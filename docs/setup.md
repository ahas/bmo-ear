# Setting up an installation

The repository carries the tool, the node's program and the card master's adapter. What belongs to one
installation — the card master's address, the way this machine reaches a node, and the folder under the
node account's home — stands in a settings file under the data root, outside the repository. No node is
named in it: the master says which node each call runs on.

## The settings file

The tool reads `ear/settings.toml` under the data root the host's `BMO_DATA_DIR` names, or under bmo's
default data root, `~/.local/share/bmo/data`, where the host sets none. `$BMO_DATA_DIR/ear/settings.toml`:

```toml
[arbiter]
# The card master's API, where each call asks its demand for a card of the service.
address = "http://127.0.0.1:7440"

[hub]
# The program that carries a command and a file to a node of the hub kind, under the node's name as
# the master grants it, and the interpreter that runs it.
bun = "/home/example/.bun/bin/bun"
console = "/opt/example/console/main.ts"

[place]
# Where this installation keeps its files under the node account's home, the same on every node the
# service is placed on.
root = "/home/example/bmo-ear"
# The card arbiter's turn client, installed on the node by the arbiter, and the installation's
# interpreter.
turn = "/home/example/bmo-card/turn.py"
python = "/home/example/bmo-ear/.venv/bin/python"
# The package manager the adapter builds the environment with, on the node.
uv = "/home/example/.local/bin/uv"
# The service name the card master and the node's card arbiter know this installation by.
service = "ear"

[engine]
model = "large-v3-turbo"
language = "ko"
device = "cuda"
compute = "float16"
```

- Every key stands in the file, and a missing key is refused with its name, but for `[arbiter]
  address`: where the table or the key stands nowhere, the master is the one on this machine's
  loopback, `http://127.0.0.1:7440`.
- A `[node]` table is refused: the node a call runs on is the master's grant, never a setting.
- No value of an installation stands in the repository's files or in a test.
- The card arbiter's own settings name the nodes and their reach; this file names only what the tool
  and the adapter need.

## The ledger of demands

- `ear/demands/` under the data root holds one file for each demand a call holds, named by the fresh
  identifier of the call's work key. It is written before the demand is asked, with the master's
  address and the work key, takes the demand's id once the master answers, and is removed once the
  demand is given back.
- A call holds a lock on its own file from before the file takes its name for as long as the call runs.
  A file whose lock nobody holds is a demand a call that died left behind: the next call gives it back
  to the master named in it and removes the file, finding the demand by its work key where the master's
  answer never came back. A demand the master no longer holds is removed as given back; a file whose
  master cannot be reached stays for the call after.
- A person may read the folder, and the master's cluster shows the same demands, each with its
  reference.

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
- The master places it with `bmo-arbiter place ear --to <node>`, which runs the adapter's `install`
  and asks its `health`. Each verb acts on the node the master names in it; the adapter reaches that
  node through the hub console under that name.
- A node reserved for an alone service at a higher priority takes it only while it stands below that
  service and does not stand alone itself. A placement that the node's reservation refuses is said by
  the master and is not worked around here.

## The tool host

The tool host places this repository and serves its entry to the sessions whose record holds the
capability the entry asks for:

```sh
bmo pocket put . --allow room.tools
```

The host reads the manifest at the next call; no restart is needed. An upgrade is the same command
after the change.

## Checking an installation

- `python3 -m unittest discover -s tests -t .` runs the repository's tests; the testbed declaration
  runs the same suite as its one check step.
- A call by hand, with the tool placed:

  ```sh
  bmo pocket tool call bmo/transcribe '{"path":"/tmp/voice.ogg"}'
  ```

- A call by hand, from a checkout, without the tool host:

  ```sh
  printf '%s' '{"protocol":1,"kind":"call","entry":"ear/listen","arguments":{"path":"/tmp/voice.ogg"},"session":{"dataRoot":"/home/example/.local/share/bmo/data"}}' \
    | python3 ear-tool.py
  ```

- The entry is unbounded: a call waits for its card and for the node's turn with no bound, and ends
  when it answers or its caller goes away. The tool host keeps no timeout for an unbounded entry, the
  tool's own included.
