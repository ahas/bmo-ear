# bmo-ear: listening to a saved voice file

## What it is

- One tool entry, `ear/listen`, answering with what is said in a voice file.
- Its argument is the path of a saved voice file on the machine the caller runs on: the message-file
  store's copy of a voice message, or any other file the caller may read.
- The answer is the transcript as text, in the language the installation names, Korean where it names
  none, with the device it was read on.
- The tool host places the tool and hands each call to the executable; the entry is shown to a session
  holding the `room.tools` capability. Nothing of the tool is linked into the host.
- The entry is unbounded: a call waits for its card as long as that takes and ends when it answers or its
  caller goes away, never on a measure of time.

## Where it listens

- The speech model runs on a GPU node of the card pool, never on this machine.
- **Which node listens is the card master's to say.** Nothing in the tool or its settings names a node:
  each call asks the master for a card of the service `ear`, and the node the granted card names is the
  one the call runs on (「The card」).
- The file is carried to that node, transcribed there, and the transcript is answered back. The copy on
  the node is removed once the run ends.
- A granted node is reached through the hub console under the node's name, as the hub knows it; the
  console, the master's address and the folders under the node account's home are the installation's,
  kept in a settings file under the data root. No address, account or path of a machine stands in this
  repository.

## The card

- The transcription is a GPU run, and a card is asked for it twice over, at the master and on the node.
- **The demand.** Every call asks the card master a demand for one card of the service `ear`, naming no
  node, with a work key of its own, `ear:listen:` and a fresh identifier, and a reference naming the
  carried file. It waits on that demand with no bound: while the master holds it in line, and while the
  master cannot be reached, the call waits and asks again. A master that no longer holds the demand,
  one restarted, is asked a new one. Once the card is granted, the call runs on the node the card
  names.
- **The demand is given back when the call ends,** however it ends: transcribed, failed on the node, or
  failed on the way to it.
- **Every demand a call holds stands in a ledger** under the data root, from its asking until it is given
  back. A call that held one stands over its entry for as long as it runs; an entry nothing stands over
  is a demand a call that died left behind, and the next call gives it back before it asks its own.
- **The node's turn.** A grant takes no card itself: on the granted node the program takes the card
  through that node's card arbiter, as every occupant does. It asks the arbiter's hold for a ticket
  under the service name `ear`, waits in the queue in its place, holds the card lock while the model
  loads and transcribes, and gives the ticket back when the process ends. That wait has no bound either:
  the run on the node is never ended on time.
- A service placed on no node is refused by the master (`no-place`), and a service with no place among
  the node's occupants is refused by the node's arbiter; either refusal is the answer: the tool never
  runs on the card outside the arbiter, never takes another occupant's name, and never moves to the CPU
  or to another machine instead.
- The card master places the service through the declaration at the repository's root, whose adapter
  installs the node's program and its environment and says whether they read, on the node the master
  names in each verb. The adapter starts no resident process: the tool's process on the node is the only
  one that holds the card.
- A CPU installation runs the program on the processor of the node its demand is granted, without the
  node's turn, and its answer names the CPU as the device. It still asks the demand, since the master
  alone says which node a call runs on. It is a choice the installation states, never something the
  tool does when a card run fails.

## What it hears with

- `faster-whisper` with the `large-v3-turbo` model, half precision on the card.
- The language is the installation's setting, `ko` where it names none.
- Voice activity is filtered and the decoder runs with a beam of five, which holds up on a room's
  recording as well as on a line spoken into a studio microphone.

## Failure, never a grey area

- Every way the tool can fail is answered as an error whose text is the reason, and the answer never
  carries an empty transcript in place of one:
  - a missing or unreadable file;
  - a missing or unreadable settings file;
  - a node that cannot be reached, or a file that could not be carried to it;
  - a card master that places the service on no node, or refuses the demand;
  - a card arbiter that gives the service no place on the node;
  - a run that ends on the node with an error, whose last lines are named;
  - an answer from the node that does not read.
- A master that cannot be reached, or holds the demand in line, is not a failure: the call waits.
- A run that heard no words is a success with an empty transcript: the file held no speech, and that
  is what it heard. It is not an error, and it is not silent about itself.

## The tool's side and the node's side

- This machine runs a small tool with the standard library and the tool host's Python helper, which
  the build places beside the executable: it reads the settings, checks the file, asks the master for
  the card, carries the file to the granted node, runs the node's command, gives the card back, and
  answers what came back.
- The node runs one Python program in the installation's virtual environment, where `faster-whisper`
  and its weights stand. The program loads the model only after the card is its turn's, so nothing of
  it rests on another occupant's card.
- The model's weights are fetched on the node at the first run, never from this machine.

## What it does not do

- It does not send into a room, wake a session, read a message's record, or decide what to do with a
  transcript. The caller asks for a file and reads the answer.
- It does not reach another repository's code, store or settings. The node's reach and the settings
  file are this installation's own.
