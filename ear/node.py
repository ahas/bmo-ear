"""The road to the node: the hub console's upload and exec (docs/design.md, 「Where it listens」).

The console carries a whole file and runs one command on a node of the hub kind. No shell is built
from a caller's words: the tool hands the console an argv list, and the only path it makes up is the
name of the copy it carries, taken from the file's content.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from .settings import Settings

# How long one transfer or one command on the node may take. The first run fetches the model's
# weights there, so the bound is generous and the tool's own timeout covers it.
RUN_LIMIT_S = 1800
# How much of a failed run's standard error an answer carries.
TAIL_LINES = 8


class NodeError(Exception):
    """The node could not be reached, a file could not be carried, or a command could not be run."""


def tail(said: str, lines: int = TAIL_LINES) -> str:
    """The last lines of what a program wrote, for an answer that names its failure."""
    kept = [line for line in said.strip().splitlines() if line.strip()]
    return "\n".join(kept[-lines:])


def _console(settings: Settings) -> list[str]:
    return [settings.hub.bun, settings.hub.console]


def _run(argv: list[str], limit_s: int = RUN_LIMIT_S) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=limit_s,
        )
    except FileNotFoundError as why:
        raise NodeError(f"the hub console could not be run: {why}") from why
    except subprocess.TimeoutExpired as why:
        raise NodeError(f"the hub console answered nothing within {limit_s} seconds") from why
    except OSError as why:
        raise NodeError(f"the hub console could not be run: {why}") from why


def exec_on_node(
    settings: Settings, words: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """One command on the node, its output kept off the tool's own streams."""
    if not words:
        raise NodeError("no command was named for the node")
    argv = _console(settings) + ["exec", "-a", settings.agent]
    for key, value in (env or {}).items():
        argv += ["--env", f"{key}={value}"]
    argv += ["--", *words]
    return _run(argv)


def upload(settings: Settings, local: Path, remote: str) -> None:
    """Carry one file whole to the node, and fail with its reason where it did not go."""
    argv = _console(settings) + ["upload", str(local), remote, "-a", settings.agent]
    ran = _run(argv)
    if ran.returncode != 0:
        said = tail(ran.stderr) or tail(ran.stdout)
        raise NodeError(
            f"the voice file could not be carried to the node"
            + (f": {said}" if said else f" (exit {ran.returncode})")
        )


def carried_name(local: Path) -> str:
    """The name the copy takes on the node: the file's content, and a safe extension."""
    digest = hashlib.sha256()
    try:
        with local.open("rb") as file:
            for block in iter(lambda: file.read(1 << 20), b""):
                digest.update(block)
    except OSError as why:
        raise NodeError(f"the voice file {local} could not be read: {why}") from why
    suffix = local.suffix[1:].lower()
    extension = suffix if re.fullmatch(r"[a-z0-9]{1,8}", suffix) else "ogg"
    return f"{digest.hexdigest()}.{extension}"


def remote_copy(settings: Settings, name: str) -> str:
    """Where the copy stands on the node."""
    if not re.fullmatch(r"[0-9a-f]{64}\.[a-z0-9]{1,8}", name):
        raise NodeError(f"{name!r} is not a name this tool carries")
    return f"{settings.place.root.rstrip('/')}/in/{name}"


def make_room(settings: Settings) -> None:
    """Make the node's folder for carried files, where it does not stand yet."""
    folder = f"{settings.place.root.rstrip('/')}/in"
    ran = exec_on_node(settings, ["mkdir", "-p", folder])
    if ran.returncode != 0:
        said = tail(ran.stderr) or tail(ran.stdout)
        raise NodeError(
            f"the node's folder {folder} could not be made"
            + (f": {said}" if said else f" (exit {ran.returncode})")
        )


def remove_copy(settings: Settings, remote: str) -> None:
    """Take the copy off the node; a removal that fails leaves nothing of the answer undone."""
    try:
        exec_on_node(settings, ["rm", "-f", remote])
    except NodeError:
        pass
