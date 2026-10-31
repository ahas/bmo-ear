"""The card master's demand for one card of the service (docs/design.md, 「The card」).

A call asks the master for a card, naming no node, waits on the demand with no bound, runs on the node
the granted card names, and gives the demand back when it ends. Every demand a call holds stands in a
ledger under the data root from before it is asked until it is given back; the call holds a lock on
its entry while it runs, so an entry nobody holds is one a call that died left, and the next call gives
it back.

Nothing here ends a wait on time: a master that holds the demand in line, one that cannot be reached,
or one that answers it at once without a card is asked again, however long that takes. Only the
master's refusal ends a wait, and it is raised as `DemandError`.
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# How long the master is asked to hold a waiting demand's answer open before the call asks again.
HOLD_MS = 60_000
# How long past the hold a read may stand before the connection is taken as lost and the read asked
# again. It ends a connection, never the wait.
READ_MARGIN_S = 30
# How long one request that the master answers at once may take.
QUICK_LIMIT_S = 30
# The pause before asking again, where the master was not reached or answered a demand with no card.
PAUSE_S = 2.0
# The work key's prefix; each call adds a fresh identifier.
WORK_PREFIX = "ear:listen:"


class DemandError(Exception):
    """The card master refused the demand, with its reason."""


class _Unreached(Exception):
    """The master was not reached, or answered as one that cannot serve now."""


def ledger_folder(data_root: str | Path) -> Path:
    """Where one installation keeps the demands its calls hold."""
    return Path(data_root) / "ear" / "demands"


def _said_to_log(line: str) -> None:
    print(f"ear: {line}", file=sys.stderr, flush=True)


def _error_text(answer: dict | None) -> str:
    """The sentence of a refusal's body, or its code where it carries no sentence."""
    if not isinstance(answer, dict):
        return ""
    for key in ("error", "code"):
        if isinstance(answer.get(key), str) and answer[key].strip():
            return answer[key].strip()
    return ""


def _granted_node(demand: dict) -> str | None:
    """The node of the one card granted, where the demand is granted and its card not taken."""
    if demand.get("state") != "granted" or demand.get("taken"):
        return None
    cards = demand.get("cards")
    if not isinstance(cards, list) or not cards:
        return None
    name = cards[0].get("nodeName") if isinstance(cards[0], dict) else None
    return name.strip() if isinstance(name, str) and name.strip() else None


def _held_open(demand: dict) -> bool:
    """Whether the master holds a read of the demand open: waiting on its service starting, no card taken.

    Any other demand short of its grant is answered at once, so the call pauses before it asks again.
    """
    reason = demand.get("reason")
    return (
        demand.get("state") == "waiting"
        and not demand.get("taken")
        and isinstance(reason, dict)
        and reason.get("code") == "starting"
    )


def _reason(demand: dict) -> str:
    taken = demand.get("taken")
    if taken:
        return f"its card was taken by {taken}"
    reason = demand.get("reason")
    if isinstance(reason, dict) and reason.get("text"):
        return str(reason["text"])
    return f"the demand is {demand.get('state') or 'waiting'}"


class Master:
    """The card master's demand routes, at one address."""

    def __init__(self, address: str):
        self.address = address.rstrip("/")

    def _request(
        self, method: str, path: str, body: dict | None = None, limit_s: float = QUICK_LIMIT_S
    ) -> tuple[int, dict | None]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.address + path,
            data=data,
            method=method,
            headers={"content-type": "application/json"} if data is not None else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=limit_s) as answer:
                status, read = answer.status, answer.read()
        except urllib.error.HTTPError as why:
            status, read = why.code, why.read()
        except (urllib.error.URLError, OSError, ValueError) as why:
            raise _Unreached(f"the card master at {self.address} was not reached: {why}") from why
        if status >= 500:
            raise _Unreached(f"the card master at {self.address} answered {status}")
        if not read.strip():
            return status, None
        try:
            parsed = json.loads(read)
        except ValueError:
            parsed = None
        return status, parsed if isinstance(parsed, dict) else None

    def ask(self, service: str, work_key: str, ref: str) -> dict:
        status, answer = self._request(
            "POST",
            "/demands",
            {"serviceName": service, "count": 1, "workKey": work_key, "ref": ref},
        )
        if status in (200, 201, 202) and isinstance(answer, dict) and answer.get("id"):
            return answer
        if status == 422:
            raise DemandError(
                f"the card master places the service {service} on no node"
                + (f": {_error_text(answer)}" if _error_text(answer) else "")
            )
        raise DemandError(
            f"the card master refused the demand for {service} ({status})"
            + (f": {_error_text(answer)}" if _error_text(answer) else "")
        )

    def read(self, demand_id: int, hold_ms: int) -> dict | None:
        """The demand as the master holds it, its answer held open while it waits; None where gone."""
        query = urllib.parse.urlencode({"waitMs": hold_ms})
        status, answer = self._request(
            "GET",
            f"/demands/{demand_id}?{query}",
            limit_s=hold_ms / 1000 + READ_MARGIN_S,
        )
        if status == 404:
            return None
        if status == 200 and isinstance(answer, dict):
            return answer
        raise DemandError(
            f"the card master answered the demand {demand_id} with {status}"
            + (f": {_error_text(answer)}" if _error_text(answer) else "")
        )

    def find(self, work_key: str) -> dict | None:
        """The demand the master holds under a work key, where one stands."""
        status, answer = self._request("GET", "/demands")
        if status != 200 or not isinstance(answer, dict):
            raise _Unreached(f"the card master at {self.address} listed no demands ({status})")
        items = answer.get("items")
        for one in items if isinstance(items, list) else []:
            if isinstance(one, dict) and one.get("workKey") == work_key and one.get("id"):
                return one
        return None

    def give_back(self, demand_id: int) -> None:
        status, answer = self._request("DELETE", f"/demands/{demand_id}")
        if status in (200, 204, 404):
            return
        raise _Unreached(
            f"the card master did not take the demand {demand_id} back ({status})"
            + (f": {_error_text(answer)}" if _error_text(answer) else "")
        )


@dataclass
class _Entry:
    """One ledger file, locked by the call that holds its demand."""

    path: Path
    fd: int
    fields: dict = field(default_factory=dict)

    def write(self) -> None:
        text = json.dumps(self.fields, sort_keys=True).encode("utf-8")
        os.ftruncate(self.fd, 0)
        os.pwrite(self.fd, text, 0)
        os.fsync(self.fd)

    def close(self, remove: bool) -> None:
        if remove:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        os.close(self.fd)


class Held:
    """A demand one call holds, from its asking until it is given back."""

    def __init__(
        self,
        master: Master,
        entry: _Entry,
        service: str,
        ref: str,
        sleep: Callable[[float], None],
        said: Callable[[str], None],
        hold_ms: int,
        pause_s: float,
    ):
        self.master = master
        self.entry = entry
        self.service = service
        self.ref = ref
        self.sleep = sleep
        self.said = said
        self.hold_ms = hold_ms
        self.pause_s = pause_s
        self.demand: dict | None = None

    @property
    def work_key(self) -> str:
        return self.entry.fields["workKey"]

    def _asked(self) -> dict:
        """A demand asked of the master, or the one a lost answer left there; waits while unreached."""
        told = None
        unanswered = False
        while True:
            try:
                standing = self.master.find(self.work_key) if unanswered else None
                demand = standing or self.master.ask(self.service, self.work_key, self.ref)
                self.entry.fields.pop("lost", None)
                self.entry.fields["id"] = demand["id"]
                self.entry.write()
                return demand
            except _Unreached as why:
                # The ask may have reached the master though its answer did not come back.
                unanswered = True
                self.entry.fields["lost"] = True
                self.entry.write()
                if str(why) != told:
                    self.said(f"waiting for the card master: {why}")
                    told = str(why)
                self.sleep(self.pause_s)

    def ask(self) -> None:
        self.demand = self._asked()

    def wait(self) -> str:
        """The node of the card granted, however long the grant takes."""
        if self.demand is None:
            self.ask()
        told = None
        while True:
            node = _granted_node(self.demand)
            if node:
                return node
            reason = _reason(self.demand)
            if reason != told:
                self.said(f"waiting for a card of {self.service}: {reason}")
                told = reason
            if not _held_open(self.demand):
                self.sleep(self.pause_s)
            try:
                read = self.master.read(self.demand["id"], self.hold_ms)
            except _Unreached as why:
                if str(why) != told:
                    self.said(f"waiting for the card master: {why}")
                    told = str(why)
                self.sleep(self.pause_s)
                continue
            if read is None:
                self.said(f"the card master no longer holds the demand {self.demand['id']}; asking again")
                self.demand = self._asked()
            else:
                self.demand = read

    def give_back(self) -> None:
        """Give the demand back; where the master is not reached, the ledger keeps it for the next call."""
        demand_id = self.entry.fields.get("id")
        given = True
        if demand_id:
            try:
                self.master.give_back(demand_id)
            except _Unreached as why:
                self.said(f"the demand {demand_id} stays in the ledger: {why}")
                given = False
        elif self.entry.fields.get("lost"):
            given = False
        self.entry.close(remove=given)


class Demands:
    """The demands one installation's calls hold, at its card master, with their ledger."""

    def __init__(
        self,
        address: str,
        folder: Path,
        sleep: Callable[[float], None] = time.sleep,
        said: Callable[[str], None] = _said_to_log,
        hold_ms: int = HOLD_MS,
        pause_s: float = PAUSE_S,
    ):
        self.address = address
        self.folder = Path(folder)
        self.sleep = sleep
        self.said = said
        self.hold_ms = hold_ms
        self.pause_s = pause_s

    def _held_entry(self, work_key: str) -> _Entry:
        """A new ledger entry, locked before it takes its name so no sweep reads it as left behind."""
        self.folder.mkdir(parents=True, exist_ok=True)
        name = work_key.removeprefix(WORK_PREFIX)
        making = self.folder / f".{name}.making"
        fd = os.open(making, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        entry = _Entry(
            path=self.folder / f"{name}.json",
            fd=fd,
            fields={"address": self.address, "workKey": work_key, "lost": True},
        )
        entry.write()
        os.replace(making, entry.path)
        return entry

    def sweep(self) -> None:
        """Give back every demand a call that died left in the ledger."""
        if not self.folder.is_dir():
            return
        for path in sorted(self.folder.glob("*.json")):
            try:
                fd = os.open(path, os.O_RDWR)
            except FileNotFoundError:
                continue
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            entry = _Entry(path=path, fd=fd)
            given = False
            try:
                with os.fdopen(os.dup(fd), "rb") as file:
                    entry.fields = json.loads(file.read() or b"{}")
                given = self._give_back_left(entry.fields)
            except ValueError:
                given = True
            finally:
                entry.close(remove=given)

    def _give_back_left(self, fields: dict) -> bool:
        master = Master(str(fields.get("address") or self.address))
        try:
            demand_id = fields.get("id")
            if fields.get("lost") or not demand_id:
                standing = master.find(str(fields.get("workKey") or ""))
                demand_id = standing["id"] if standing else None
            if demand_id:
                master.give_back(demand_id)
                self.said(f"gave back the demand {demand_id} a call left in the ledger")
            return True
        except _Unreached as why:
            self.said(f"a demand left in the ledger stays there: {why}")
            return False

    def ask(self, service: str, ref: str) -> Held:
        """A demand for one card of the service, asked of the master and entered in the ledger."""
        entry = self._held_entry(WORK_PREFIX + uuid.uuid4().hex)
        held = Held(
            Master(self.address),
            entry,
            service,
            ref,
            sleep=self.sleep,
            said=self.said,
            hold_ms=self.hold_ms,
            pause_s=self.pause_s,
        )
        try:
            held.ask()
        except DemandError:
            entry.close(remove=True)
            raise
        except BaseException:
            # A demand may stand under the work key; the entry stays for the next call's sweep.
            entry.close(remove=False)
            raise
        return held
