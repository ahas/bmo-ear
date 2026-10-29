# bmo-ear

The listening tool: one entry, `ear/listen`, that takes the path of a saved voice file and answers
with what is said in it, in Korean.

The speech model runs on a GPU node of the card pool through that node's card arbiter, half precision,
with `faster-whisper` and the `large-v3-turbo` model. The file is carried to the node, transcribed
there and removed; the transcript comes back as text.

## Layout

| Folder | Holds |
|---|---|
| `ear/` | The tool's own code: the settings reader, the node's road, and the call that carries a file and answers a transcript |
| `node/` | The program the node runs: `faster-whisper` behind one JSON line |
| `tests/` | Every test, the manifest's shape and the personal-data check among them |
| `docs/` | What the tool does (`design.md`) and how one installation is set up (`setup.md`) |

At the root stand the tool's manifest (`tool.toml`), the card master's declaration (`ear.card.toml`),
the entry's schemas, the executable (`ear-tool.py`), the tool host's Python helper (`bmo_tool.py`),
the adapter (`adapter.py`), the testbed declaration (`testbed.toml`) and the version.

## Building and testing

```sh
python3 -m unittest discover -s tests -t . -v
```

The manifest's build copies the executable, its package and the helper into the placed folder; its
check is the test suite above. The testbed declaration runs the same suite as its one check step.

## Placing it

The tool host places this repository under its registry, with the capability its entry asks for:

```sh
bmo pocket put . --allow room.tools
```

A session holding `room.tools` reaches the entry as `ear/listen`, or through the toolbook.

## The card service

`ear.card.toml` declares the `ear` service to the card master. The adapter installs the node's program
and its `faster-whisper` environment on the node and answers whether they read. The card master places
the service on the node the installation names; the tool asks the node's arbiter for the `ear` turn
before the model runs.

## Settings

The node, its reach and the installation's folders stand in `$BMO_DATA_DIR/ear/settings.toml`, never
in this repository. `docs/setup.md` is the whole of it.

## Version

`VERSION` holds the repository's one version, `0.1.0` with a revision until the first release.
