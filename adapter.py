#!/usr/bin/env python3
"""The card master's adapter for the `ear` service (ear.card.toml).

The master runs one verb here, from the folder this file stands in, and reads the last line as JSON.
`install` puts this repository's node program and a virtual environment with `faster-whisper` on the
node and warms the model's weights; `health` says whether that environment reads; the service has no
resident process, so `start` and `stop` say what stands without starting anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ear.node import NodeError, exec_on_node, tail, upload
from ear.settings import SettingsError, read

HERE = Path(__file__).resolve().parent
INSTALL_LIMIT_S = 3600


def say(fields: dict, code: int = 0) -> int:
    print(json.dumps(fields, sort_keys=True), flush=True)
    return code


def nodes_named(args: argparse.Namespace) -> list[str]:
    named = [name for name in args.placed.split(",") if name.strip()] if args.placed else []
    if not named and args.node:
        named = [args.node]
    return named


def data_root() -> str:
    return os.environ.get("BMO_DATA_DIR") or str(Path.home() / ".local/share/bmo/data")


def run(settings, words: list[str]) -> tuple[int, str, str]:
    ran = exec_on_node(settings, words)
    return ran.returncode, ran.stdout, ran.stderr


def install(settings) -> tuple[bool, str]:
    root = settings.place.root.rstrip("/")
    made = exec_on_node(settings, ["mkdir", "-p", f"{root}/in"])
    if made.returncode != 0:
        return False, f"the node's folders could not be made: {tail(made.stderr) or tail(made.stdout)}"

    for name in ("ear-transcribe.py", "ear-health.py", "requirements.txt"):
        upload(settings, HERE / "node" / name, f"{root}/{name}")

    venv = f"{root}/.venv"
    python = settings.place.python
    present, _, _ = run(settings, ["test", "-x", python])
    if present != 0:
        code, _, err = run(settings, [settings.place.uv, "venv", "--python", "3", venv])
        if code != 0:
            return False, f"the virtual environment could not be made: {tail(err)}"

    code, _, err = run(
        settings,
        [settings.place.uv, "pip", "install", "--quiet", "--python", python,
         "--system-certs", "-r", f"{root}/requirements.txt"],
    )
    if code != 0:
        return False, f"faster-whisper could not be installed: {tail(err)}"

    code, out, err = run(
        settings,
        [python, f"{root}/ear-health.py", "--warm", settings.engine.model],
    )
    if code != 0:
        return False, f"the model's weights could not be fetched: {tail(err) or tail(out)}"
    return True, "the node's environment and model stand"


def health(settings) -> tuple[bool, str]:
    code, out, err = run(settings, [settings.place.python, f"{settings.place.root.rstrip('/')}/ear-health.py"])
    if code == 0:
        return True, "running"
    said = tail(err) or tail(out)
    return False, said or f"the environment check exited {code}"


def main() -> int:
    parser = argparse.ArgumentParser(description="the ear service's card adapter")
    parser.add_argument("verb", choices=["install", "uninstall", "start", "stop", "health", "placed"])
    parser.add_argument("--node")
    parser.add_argument("--placed", default="")
    args = parser.parse_args()

    nodes = nodes_named(args)
    if args.verb == "placed":
        return say({"ok": True, "state": "running", "nodes": nodes})

    if not nodes:
        return say(
            {"ok": False, "node": args.node, "state": "failing", "detail": "the adapter was given no node"},
            1,
        )

    try:
        settings = read(data_root())
    except SettingsError as why:
        return say({"ok": False, "node": nodes[-1], "state": "failing", "detail": str(why)}, 1)

    elsewhere = [name for name in nodes if name != settings.agent]
    if elsewhere:
        return say(
            {
                "ok": False,
                "node": elsewhere[-1],
                "state": "failing",
                "detail": f"this installation reaches {settings.agent}, not {', '.join(elsewhere)}",
            },
            1,
        )

    try:
        if args.verb == "install":
            ok, detail = install(settings)
            if not ok:
                return say({"ok": False, "node": nodes[-1], "state": "failing", "detail": detail}, 1)
            return say({"ok": True, "node": nodes[-1], "state": "running", "detail": "installed",
                        "nodes": nodes})

        if args.verb == "health":
            ok, detail = health(settings)
            return say(
                {"ok": ok, "node": nodes[-1], "state": "running" if ok else "failing", "detail": detail},
                0 if ok else 1,
            )

        if args.verb == "stop":
            return say({"ok": True, "node": nodes[-1], "state": "stopped", "detail": "no process stands"})

        if args.verb == "start":
            ok, detail = health(settings)
            return say(
                {"ok": ok, "node": nodes[-1], "state": "running" if ok else "failing", "detail": detail},
                0 if ok else 1,
            )

        return say({"ok": True, "node": nodes[-1], "state": "stopped",
                    "detail": "the installation stays on the node"})
    except NodeError as why:
        return say({"ok": False, "node": nodes[-1], "state": "failing", "detail": str(why)}, 1)


if __name__ == "__main__":
    sys.exit(main())
