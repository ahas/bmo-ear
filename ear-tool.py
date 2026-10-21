#!/usr/bin/env python3
"""The listening tool (docs/design.md): `bmo/transcribe`, one saved voice file answered as text.

The executable runs on the standard library and the shared Python tool helper the build places beside
it. The file itself is carried to the node and transcribed there; this process answers what came back.
"""

from __future__ import annotations

import bmo_tool

from ear.call import CallError, transcribe


def heard(call: bmo_tool.Call) -> dict:
    path = call.arguments.get("path")
    try:
        answer = transcribe(path, call.session["dataRoot"])
    except CallError as why:
        return bmo_tool.failure(str(why))
    return bmo_tool.structured(answer)


def main() -> None:
    bmo_tool.answer({"bmo/transcribe": heard})


if __name__ == "__main__":
    main()
