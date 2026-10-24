# Working in bmo-ear

This repository is the listening tool, `bmo-ear`: one entry that takes the path of a saved voice file
and answers with its transcript, transcribed on a GPU node through the node's card arbiter.

## The three standing principles

- **It runs on its own,** building, testing and running from this repository alone, reading no other
  repository's code, files, data or settings. The tool host's Python helper is vendored here because a
  placed tool's build is handed no path into another repository.
- **It is met only through its documented contract:** the `bmo/transcribe` entry, its input and output
  schemas, and the card service's adapter.
- **It knows nothing of its callers.** A room, a session or an agent is not in its code or documents;
  the caller names a file and reads the transcript.

## The documents come first

- `docs/design.md` is the canonical statement of what the tool does; the code is one realisation of
  it. Read it before changing code. A change that would make it wrong or incomplete repairs it first,
  stating what is true now, and the code is written to match.
- `docs/setup.md` states what one installation keeps in its settings file.
- A document states what is true now: no change history, no rationale told through a past design, no
  pasted source, signature or config fragment, and no file-and-line pins.

## Language and personal data

- **Code, comments, strings, tests, documents, commit messages and branch names are English.**
- **No personal data:** no person's name, machine name, internal address or home path, in code,
  documents, tests or commits. A node, an account and a path belong to an installation's settings
  file under the data root; the repository's examples use reserved names.

## The shape

- The tool's executable runs on the standard library and the vendored Python tool helper the build
  places beside it; the node's program runs in the installation's virtual environment with
  `faster-whisper`.
- The node is reached through the hub console the settings name; no shell is built from a caller's
  words. The file carried to a node is named by its content, never by the caller's path.
- The transcription takes the node's card through the arbiter's turn client under the service name
  `ear`, and never runs outside the arbiter.
- A failure is answered with its reason, never with an empty transcript. Nothing falls back to the
  CPU, to another machine or to another occupant's name.

## The stages of a change

1. **Writing:** `python3 -m unittest discover -s tests -t .` on the unit touched.
2. **Review:** read the whole diff against `docs/design.md`.
3. **Verification:** the tests once, and where the change reaches the node, a run on a real voice
   file.

A change is not done before stage 3 has passed.
