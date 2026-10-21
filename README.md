# bmo-ear

The listening tool: one entry, `bmo/transcribe`, that takes the path of a saved voice file and answers
with what is said in it, in Korean.

The speech model runs on a GPU node of the card pool through that node's card arbiter, half precision,
with `faster-whisper` and the `large-v3-turbo` model. The file is carried to the node, transcribed
there and removed; the transcript comes back as text.

## Layout

| Folder | Holds |
|---|---|
| `ear/` | The tool's own code: the settings reader, the node's road, and the call that carries a file and answers a transcript |
| `node/` | The program the node runs: `faster-whisper` behind one JSON line |
| `tests/` | Every test, the manifest's shape among them |
| `docs/` | What the tool does (`design.md`) and how one installation is set up (`setup.md`) |

At the root stand the tool's manifest (`tool.toml`), the card master's declaration (`ear.card.toml`),
the entry's schemas, the executable (`ear-tool.py`), the adapter (`adapter.py`) and the version.

## Building and testing

```sh
python3 -m unittest discover -s tests -t . -v
```

The manifest's build copies the executable, its package and the shared Python tool helper into the
placed folder; the manifest's check is the test suite above, and it is the unit the parent
repository's static check and suite run for this folder.

## Settings

The node, its reach and the installation's folders stand in `$BMO_DATA_DIR/ear/settings.toml`, never
in this repository. `docs/setup.md` is the whole of it.

## Version

`VERSION` holds the repository's one version, `0.1.0` with a revision until the first release.
