# Setting up an installation

The repository carries the tool and the node's program. What belongs to one installation — the node,
the way this machine reaches it, and the folder under the node account's home — stands in a settings
file under the data root, outside the repository.

## The settings file

`$BMO_DATA_DIR/ear/settings.toml`:

```toml
[node]
# The node the installation transcribes on, as the hub knows it.
agent = "n2"

[hub]
# The program that carries a command and a file to a node of the hub kind, and the interpreter that
# runs it.
bun = "/home/example/.bun/bin/bun"
console = "/opt/example/console/main.ts"

[place]
# Where this installation keeps its files under the node account's home.
root = "/home/example/bmo-ear"
# The card arbiter's turn client, installed on the node by the arbiter, and the installation's
# interpreter.
turn = "/home/example/bmo-card/turn.py"
python = "/home/example/bmo-ear/.venv/bin/python"
# The package manager the adapter builds the environment with, on the node.
uv = "/home/example/.local/bin/uv"
# The service name the card arbiter knows this installation by.
service = "ear"

[engine]
model = "large-v3-turbo"
language = "ko"
device = "cuda"
compute = "float16"
```

- Every key stands in the file; a missing key is refused with its name.
- No value of an installation stands in the repository's files or in a test.
- The card arbiter's own settings name the node and its reach; this file names only what the tool and
  the adapter need.

## The node's environment

The adapter's `install` verb builds it on the node:

- the folder `place.root`, and `in/` under it for the carried files;
- the programs `ear-transcribe.py` and `ear-health.py` from this repository's `node/`, and its
  `requirements.txt`, at the installation's root;
- the virtual environment `place.root/.venv`, made with `uv`, holding `faster-whisper` and the
  pinned `av` its reading of an audio container needs;
- the model named by `engine.model`, fetched into the environment's own cache on the CPU during
  `install`, so the first call does not wait for the weights.

## The card service

- `ear.card.toml` declares the service to the card master: one node, priority 60, not alone, its
  adapter in this repository.
- The master places it with `card-master place ear --to <node>`, which runs the adapter's `install`
  and asks its `health`.
- A node reserved for an alone service at a higher priority takes it only while it stands below that
  service and does not stand alone itself. A placement that the node's reservation refuses is said by
  the master and is not worked around here.

## Checking an installation

- `python3 -m unittest discover -s tests -t .` runs the repository's tests.
- A call by hand, from a checkout:

  ```sh
  printf '%s' '{"protocol":1,"kind":"call","entry":"bmo/transcribe","arguments":{"path":"/tmp/voice.ogg"},"session":{"dataRoot":"/home/example/.local/share/bmo/data"}}' \
    | PYTHONPATH=<checkout>/tools/_sdk/python python3 ear-tool.py
  ```

- The tool's own timeout is generous: the first run on a node fetches the model's weights.
