#!/usr/bin/env python3
"""The node's program (docs/design.md): one voice file read by faster-whisper, answered as one JSON line.

It runs inside the card arbiter's turn: the tool starts it through the arbiter's turn client, so the
model is loaded and used only while this process holds the card. It never changes its device on its
own: a card that cannot run the model is an error, not a reason to move to the CPU.

usage: ear-transcribe.py --file <path> [--language ko] [--model large-v3-turbo]
                         [--device cuda] [--compute float16] [--remove]
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def answer(fields: dict) -> None:
    print(json.dumps(fields, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="read one voice file and answer its transcript")
    parser.add_argument("--file", required=True)
    parser.add_argument("--language", default="ko")
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute", default="float16")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        answer({"error": f"the file {args.file} does not stand on this node"})
        return 1

    try:
        from faster_whisper import WhisperModel
    except Exception as why:  # an environment without the library is named, never worked around
        answer({"error": f"faster-whisper does not stand in this environment: {why}"})
        return 1

    try:
        model = WhisperModel(args.model, device=args.device, compute_type=args.compute)
        segments, info = model.transcribe(
            args.file,
            language=args.language,
            beam_size=5,
            vad_filter=True,
        )
        text = "".join(segment.text for segment in segments).strip()
    except Exception as why:
        answer({"error": f"the model could not read the file on {args.device}: {why}"})
        return 1
    finally:
        if args.remove:
            try:
                os.remove(args.file)
            except OSError:
                pass

    answer(
        {
            "transcript": text,
            "language": getattr(info, "language", args.language),
            "duration": getattr(info, "duration", None),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
