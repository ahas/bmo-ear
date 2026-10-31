"""One call of the listening tool (docs/design.md): a card asked of the card master, the saved voice file
carried to the node the card is granted on, transcribed there on that card, the transcript answered
back, and the card given back however the call ends.

Every failure is raised as `CallError` carrying the reason. Nothing here answers an empty transcript
for a run that failed, and nothing falls back to the CPU, to another machine or to another occupant's
name.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import demand, node
from .settings import Settings, SettingsError, read


class CallError(Exception):
    """The file could not be heard, with the reason the answer carries."""


def _checked_file(path_text: str) -> Path:
    if not isinstance(path_text, str) or not path_text.strip():
        raise CallError("the call names no voice file path")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise CallError(f"the voice file's path {path_text!r} is not absolute")
    if not path.exists():
        raise CallError(f"the voice file {path} does not stand")
    if not path.is_file():
        raise CallError(f"the path {path} is not a file")
    if not os.access(path, os.R_OK):
        raise CallError(f"the voice file {path} cannot be read")
    return path


def _program_words(settings: Settings, remote: str) -> list[str]:
    program = f"{settings.place.root.rstrip('/')}/ear-transcribe.py"
    return [
        settings.place.python,
        program,
        "--file",
        remote,
        "--language",
        settings.engine.language,
        "--model",
        settings.engine.model,
        "--device",
        settings.engine.device,
        "--compute",
        settings.engine.compute,
        "--remove",
    ]


def _run_words(settings: Settings, remote: str) -> list[str]:
    """The program, inside the card arbiter's turn for a card installation.

    A CPU installation names a node whose card this tool does not use, so there is no card to take;
    a card installation never runs outside the arbiter.
    """
    program = _program_words(settings, remote)
    if settings.engine.device != "cuda":
        return program
    return [
        settings.place.python,
        settings.place.turn,
        "--service",
        settings.place.service,
        "--",
        *program,
    ]


def _answer(ran, language: str, device: str) -> dict:
    said = ran.stdout.strip().splitlines()
    heard = None
    if said:
        try:
            heard = json.loads(said[-1])
        except ValueError:
            heard = None

    if isinstance(heard, dict) and isinstance(heard.get("transcript"), str):
        return {
            "transcript": heard["transcript"],
            "language": heard.get("language") or language,
            "duration": heard.get("duration"),
            "device": device,
        }
    if isinstance(heard, dict) and isinstance(heard.get("error"), str):
        raise CallError(f"the node could not transcribe the file: {heard['error']}")

    detail = node.tail(ran.stderr) or node.tail(ran.stdout)
    if ran.returncode == 3:
        raise CallError(
            "the card arbiter gave the service no place on the node, so nothing ran"
            + (f": {detail}" if detail else "")
        )
    if ran.returncode != 0:
        raise CallError(
            f"the node's transcription ended with {ran.returncode}"
            + (f": {detail}" if detail else "")
        )
    raise CallError(
        "the node answered nothing that reads as a transcript"
        + (f": {detail}" if detail else "")
    )


def _on_node(settings: Settings, node_name: str, path: Path, remote: str):
    """The file carried to the granted node and the program run there, the copy removed after."""
    try:
        node.make_room(settings, node_name)
        node.upload(settings, node_name, path, remote)
    except node.NodeError as why:
        raise CallError(f"{node_name}: {why}") from why

    on_card = settings.engine.device == "cuda"
    try:
        return node.exec_on_node(
            settings,
            node_name,
            _run_words(settings, remote),
            env={"BMO_CARD_SERVICE": settings.place.service} if on_card else None,
            unbounded=True,
        )
    except node.NodeError as why:
        raise CallError(f"{node_name}: {why}") from why
    finally:
        node.remove_copy(settings, node_name, remote)


def transcribe(path_text: str, data_root: str | Path, demands: demand.Demands | None = None) -> dict:
    """What is said in one voice file, transcribed on the node the card master grants a card on."""
    path = _checked_file(path_text)
    try:
        settings = read(data_root)
    except SettingsError as why:
        raise CallError(f"this installation's settings do not read: {why}") from why

    try:
        name = node.carried_name(path)
        remote = node.remote_copy(settings, name)
    except node.NodeError as why:
        raise CallError(str(why)) from why

    if demands is None:
        demands = demand.Demands(settings.arbiter.address, demand.ledger_folder(data_root))
    try:
        demands.sweep()
        held = demands.ask(settings.place.service, f"ear listens to {name}")
    except demand.DemandError as why:
        raise CallError(str(why)) from why
    except OSError as why:
        raise CallError(f"the ledger of demands could not be kept: {why}") from why

    try:
        try:
            node_name = held.wait()
        except demand.DemandError as why:
            raise CallError(str(why)) from why
        ran = _on_node(settings, node_name, path, remote)
    finally:
        held.give_back()

    return _answer(ran, settings.engine.language, settings.engine.device)
