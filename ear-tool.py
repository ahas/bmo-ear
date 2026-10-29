#!/usr/bin/env python3
"""The listening tool (docs/design.md): `ear/listen`, one saved voice file answered as text.

The executable runs on the standard library and the shared Python tool helper the build places beside
it. The file itself is carried to the node and transcribed there; this process answers what came back.
"""

from __future__ import annotations

import os
from pathlib import Path

import bmo_tool

from ear.call import CallError, transcribe


def heard(call: bmo_tool.Call) -> dict:
    path = call.arguments.get("path")
    data_root = call.session.get("dataRoot") or os.environ.get("BMO_DATA_DIR")
    if not data_root:
        data_root = str(Path.home() / ".local/share/bmo/data")
    try:
        answer = transcribe(path, data_root)
    except CallError as why:
        return bmo_tool.failure(str(why))
    return bmo_tool.structured(answer)


def main() -> None:
    bmo_tool.answer({"ear/listen": heard})


if __name__ == "__main__":
    main()
