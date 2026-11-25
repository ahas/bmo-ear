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
the adapter (`adapter.py`) and the testbed declaration (`testbed.toml`).

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
and its `faster-whisper` environment on the node and answers whether they read. Each call asks the
card master a demand for one `ear` card, naming no node, runs on the node the granted card names, and
gives the demand back when it ends; there the program asks the node's arbiter for the `ear` turn before
the model runs.

## Settings

The card master's address, the reach of a node and the installation's folders stand in
`$BMO_DATA_DIR/ear/settings.toml`, never in this repository; no node is named there. `docs/setup.md`
is the whole of it.

## Version

The version is the set's, read off the git tags when a build is made (bmo-chat's `docs/conventions.md`,
「Versions」); no file of this repository holds it.
