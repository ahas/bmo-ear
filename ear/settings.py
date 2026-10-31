"""The installation's settings, read from the data root (docs/setup.md).

Every value one installation keeps — the card master's address, the way this machine reaches a node,
the folder under the node account's home, and the engine's own values — stands in one TOML file under
the data root. No such value stands in this repository, and no node is named in the file: the master
says which node each call runs on.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


# The card master on this machine's loopback, where the settings name none.
DEFAULT_ARBITER = "http://127.0.0.1:7440"


class SettingsError(Exception):
    """The settings file is missing, unreadable, or does not name what the tool needs."""


@dataclass(frozen=True)
class Arbiter:
    """The card master whose demands say which node a call runs on."""

    address: str


@dataclass(frozen=True)
class Hub:
    """The console that carries a command and a file to a node of the hub kind, by its name."""

    bun: str
    console: str


@dataclass(frozen=True)
class Place:
    """This installation's files on the node, and the card arbiter's turn client there."""

    root: str
    turn: str
    python: str
    service: str
    uv: str


@dataclass(frozen=True)
class Engine:
    """The speech model and how it is run."""

    model: str
    language: str
    device: str
    compute: str


@dataclass(frozen=True)
class Settings:
    arbiter: Arbiter
    hub: Hub
    place: Place
    engine: Engine


def settings_path(data_root: str | Path) -> Path:
    """Where one installation keeps its settings."""
    return Path(data_root) / "ear" / "settings.toml"


def _table(read: dict, name: str, path: Path) -> dict:
    table = read.get(name)
    if not isinstance(table, dict):
        raise SettingsError(f"{path}: the [%s] table stands in the settings file" % name)
    return table


def _word(table: dict, table_name: str, key: str, path: Path) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SettingsError(f"{path}: [{table_name}] {key} stands in the settings file")
    return value.strip()


def read(data_root: str | Path) -> Settings:
    """The settings of the installation whose data root this is."""
    path = settings_path(data_root)
    try:
        with path.open("rb") as file:
            read_in = tomllib.load(file)
    except FileNotFoundError as why:
        raise SettingsError(f"the settings file {path} does not stand: {why}") from why
    except OSError as why:
        raise SettingsError(f"the settings file {path} could not be read: {why}") from why
    except tomllib.TOMLDecodeError as why:
        raise SettingsError(f"the settings file {path} does not read: {why}") from why

    if "node" in read_in:
        raise SettingsError(
            f"{path}: a [node] table stands in the settings file; the card master names the node"
        )
    arbiter = read_in.get("arbiter", {})
    if not isinstance(arbiter, dict):
        raise SettingsError(f"{path}: [arbiter] is a table")
    address = arbiter.get("address", DEFAULT_ARBITER)
    if not isinstance(address, str) or not address.strip():
        raise SettingsError(f"{path}: [arbiter] address names the card master's API")
    address = address.strip().rstrip("/")
    if not address.startswith(("http://", "https://")):
        raise SettingsError(f"{path}: [arbiter] address is an http address, not {address!r}")
    hub = _table(read_in, "hub", path)
    place = _table(read_in, "place", path)
    engine = _table(read_in, "engine", path)

    settings = Settings(
        arbiter=Arbiter(address=address),
        hub=Hub(bun=_word(hub, "hub", "bun", path), console=_word(hub, "hub", "console", path)),
        place=Place(
            root=_word(place, "place", "root", path),
            turn=_word(place, "place", "turn", path),
            python=_word(place, "place", "python", path),
            service=_word(place, "place", "service", path),
            uv=_word(place, "place", "uv", path),
        ),
        engine=Engine(
            model=_word(engine, "engine", "model", path),
            language=_word(engine, "engine", "language", path),
            device=_word(engine, "engine", "device", path),
            compute=_word(engine, "engine", "compute", path),
        ),
    )
    if settings.engine.device not in ("cuda", "cpu"):
        raise SettingsError(
            f"{path}: [engine] device names cuda or cpu, not {settings.engine.device!r}"
        )
    if not settings.place.root.startswith("/"):
        raise SettingsError(f"{path}: [place] root is an absolute path on the node")
    return settings
