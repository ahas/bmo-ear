# bmo-ear: listening to a saved voice file

## What it is

- One tool entry, `bmo/transcribe`, answering with what is said in a voice file.
- Its argument is the path of a saved voice file on the machine the caller runs on: the message-file
  store's copy of a voice message, or any other file the caller may read.
- The answer is the transcript as text, in the language the installation names, Korean where it names
  none, with the device it was read on.
- The tool host places the tool and hands each call to the executable; the entry is shown to a session
  holding the `room.tools` capability. Nothing of the tool is linked into the host.

## Where it listens

- The speech model runs on a GPU node of the card pool, never on this machine.
- The file is carried to the node, transcribed there, and the transcript is answered back. The copy on
  the node is removed once the run ends.
- The node and how it is reached are the installation's, kept in a settings file under the data root;
  no address, account or path of a machine stands in this repository.

## The card

- The transcription is a GPU run: it takes the node's card through that node's card arbiter.
- It asks the arbiter's hold for a ticket under the service name `ear`, waits in the queue in its
  place, holds the card lock while the model loads and transcribes, and gives the ticket back when the
  process ends.
- A service with no place among the node's occupants is refused by the arbiter, and that refusal is
  the answer: the tool never runs on the card outside the arbiter, never takes another occupant's
  name, and never moves to the CPU or to another machine instead.
- The card master places the service through the declaration at the repository's root, whose adapter
  installs the node's program and its environment and says whether they read. The adapter starts no
  resident process: the tool's process on the node is the only one that holds the card.
- A CPU installation names a node whose card this tool does not use; it runs without asking the
  arbiter, and its answer names the CPU as the device. It is a choice the installation states, never
  something the tool does when a card run fails.

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
  - a card arbiter that gives the service no place on the node;
  - a run that ends on the node with an error, whose last lines are named;
  - an answer from the node that does not read.
- A run that heard no words is a success with an empty transcript: the file held no speech, and that
  is what it heard. It is not an error, and it is not silent about itself.

## The tool's side and the node's side

- This machine runs a small tool with the standard library and the tool host's Python helper, which
  the build places beside the executable: it reads the settings, checks the file, carries it, runs the
  node's command, and answers what came back.
- The node runs one Python program in the installation's virtual environment, where `faster-whisper`
  and its weights stand. The program loads the model only after the card is its turn's, so nothing of
  it rests on another occupant's card.
- The model's weights are fetched on the node at the first run, never from this machine.

## What it does not do

- It does not send into a room, wake a session, read a message's record, or decide what to do with a
  transcript. The caller asks for a file and reads the answer.
- It does not reach another repository's code, store or settings. The node's reach and the settings
  file are this installation's own.
