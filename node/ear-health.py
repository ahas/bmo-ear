#!/usr/bin/env python3
"""The node's environment as the adapter reads it (docs/setup.md): the library, and on `--warm` the
model's weights fetched into the environment's own cache.

It loads nothing onto the card: the warm-up runs on the CPU, so an installation can be made ready
while another occupant holds the card.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="check the node's speech environment")
    parser.add_argument("--warm", metavar="MODEL", help="fetch and load the named model on the CPU")
    args = parser.parse_args()

    try:
        import faster_whisper
    except Exception as why:
        print(json.dumps({"ok": False, "detail": f"faster-whisper does not stand: {why}"}))
        return 1

    if args.warm:
        try:
            model = faster_whisper.WhisperModel(args.warm, device="cpu", compute_type="int8")
            del model
        except Exception as why:
            print(json.dumps({"ok": False, "detail": f"{args.warm} could not be fetched: {why}"}))
            return 1

    print(json.dumps({"ok": True, "detail": faster_whisper.__version__}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
