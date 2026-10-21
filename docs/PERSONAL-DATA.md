# Personal data

This repository holds none. Its code, comments, documents, tests and commit messages name no person
and carry no detail that belongs to one; a value that differs by machine, by account or by
installation is read from settings instead.

## What is kept out

- a person's name, handle or account id;
- an email address, other than the development address `dev@ahas.io` and the reserved example space;
- a host name, a home folder that names someone, a domain, a device or a network detail;
- a room member's display name and id;
- a token, a key or a password;
- a line of a real conversation.

## What stands in its place

- **A value that differs by machine, account or installation belongs in the settings file under the
  data root** (`docs/setup.md`), read when it is needed, never written into the code, a document or a
  test.
- **An example uses a neutral name** — `example`, `tester`, `qa-admin` — and a home folder among the
  reserved ones, never a person's.

## The check

`tests/test_personal_data.py` reads every file git tracks or would track and refuses one that holds
the shape of an email address, a home folder that names someone, a telephone number, a token or a
private network address. A finding names the path, the line and the shape, never the value.

The check keeps the shapes alone, never a list of names or values: such a list would itself be what
this rule keeps out. A loopback address such as `127.0.0.1` names this machine and is not a private
address.
