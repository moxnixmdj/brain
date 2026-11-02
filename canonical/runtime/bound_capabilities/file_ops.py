#!/usr/bin/env python3
"""Copy and rename one repository-local file, in process.

Seven of the 11 ordinary requests still failing after the read-only work are
MUTATIONS, and the sentences state them exactly:

    "Copy a.txt to c.txt"        -> cp a.txt c.txt
    "Rename b.txt to d.txt"      -> mv b.txt d.txt

They were refused with the computer-execution boundary. They are ordinary
pathlib operations, so the boundary was answering for an absent row rather than
refusing an unsafe one.

What this module will not do
----------------------------
Writes are the class where a wrong answer destroys something, so every rule here
is a refusal rather than a default:

* both paths are required. A copy with no stated destination does not become
  "copy next to the source";
* the destination must NOT already exist unless the sentence itself asks to
  overwrite or replace. Silent overwrite is how an ordinary request eats a file;
* the destination may not be the source (also enforced upstream by
  `write_authority_v1`, and re-checked here on the resolved paths, since the
  upstream check compares names while a hard link shares bytes);
* every result is READ BACK. `output_verified` is the digest of what is on disk
  after the write, compared with the digest of the source (copy) or with the
  bytes that were moved (rename) -- not a restatement of what the adapter meant
  to do.

No process is spawned, no shell is involved, and no path outside the repository
root can be written.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

#: Words a sentence uses when it MEANS to replace an existing destination.
_OVERWRITE = re.compile(r"\b(?:overwrit\w*|over-writ\w*|replac\w*|clobber\w*|force)\b", re.I)


def _safe(root: pathlib.Path, raw: str, *, role: str) -> pathlib.Path:
    if not str(raw or "").strip():
        raise RuntimeError("PATH_REQUIRED:" + role)
    p = (root / str(raw)).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + role)
    return p


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare(args, root: pathlib.Path):
    source = _safe(root, args.get("path") or args.get("input_path"), role="path")
    destination = _safe(root, args.get("output_path") or args.get("destination_path"),
                        role="output_path")
    if not source.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    if source == destination:
        # Resolved, so `a.txt` and `./a.txt` are the same file here even though
        # they are different strings.
        raise RuntimeError("SOURCE_AND_DESTINATION_ARE_THE_SAME_FILE")
    # BOTH FILES MUST BE NAMED BY THE SENTENCE.
    #
    # Upstream binding can be wrong -- and was: a symbol-rename sentence had its
    # `path` filled with a repository file the sentence never mentioned, and the
    # move succeeded. A writer that acts on a path the sentence did not state is
    # a writer that destroys something the user did not point at, so the last
    # line of defence is the sentence itself: the source's name and the
    # destination's name must both appear in it.
    stated = str(args.get("goal") or "")
    for role, target in (("path", source), ("output_path", destination)):
        name = target.name
        if not name or (name not in stated and target.as_posix() not in stated):
            raise RuntimeError("PATH_NOT_STATED_IN_THE_SENTENCE:" + role + ":" + name)
    if destination.exists():
        if not _OVERWRITE.search(str(args.get("goal") or "")):
            raise RuntimeError("DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE")
        if destination.is_dir():
            raise RuntimeError("DESTINATION_IS_A_DIRECTORY")
    return source, destination


def _copy(args, root: pathlib.Path) -> dict:
    source, destination = _prepare(args, root)
    before = _digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    after, written = _digest(destination), _digest(source)
    if after != before or written != before:
        raise RuntimeError("COPY_DID_NOT_ROUNDTRIP")
    return {"path": source.relative_to(root).as_posix(),
            "destination_path": destination.relative_to(root).as_posix(),
            "source_sha256": before, "destination_sha256": after,
            "byte_count": destination.stat().st_size,
            "answer": destination.relative_to(root).as_posix()}


def _rename(args, root: pathlib.Path) -> dict:
    source, destination = _prepare(args, root)
    before = _digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    if source.exists():
        raise RuntimeError("RENAME_LEFT_THE_SOURCE_IN_PLACE")
    after = _digest(destination)
    if after != before:
        raise RuntimeError("RENAME_CHANGED_THE_BYTES")
    return {"path": source.relative_to(root).as_posix(),
            "destination_path": destination.relative_to(root).as_posix(),
            "source_sha256": before, "destination_sha256": after,
            "byte_count": destination.stat().st_size,
            "answer": destination.relative_to(root).as_posix()}


_HANDLERS = {"copy": _copy, "rename": _rename}


def run(args, root):
    root = pathlib.Path(root).resolve()
    command = str(args.get("command") or "").strip()
    if command not in _HANDLERS:
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + (command or "<none>"))
    payload = {"schema": "PROJECT_BRAIN_FILE_OPS_V1",
               "adapter": "file_ops", "command": command}
    payload.update(_HANDLERS[command](args, root))
    payload["output_verified"] = True
    return payload
