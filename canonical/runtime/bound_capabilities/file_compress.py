#!/usr/bin/env python3
"""`gzip <file>` -- in process, verified before anything is removed.

The sentence "Compress <p>/a.txt" settles exactly one command line, `gzip
<p>/a.txt`, and `gzip` is in the acceptance tables as a MUTATING command: it
writes `<file>.gz` and then removes the original. This module performs that
operation and nothing else. It does not quietly become `gzip -k`; a row that
declared `gzip <f>` while keeping the original would be a false declaration, and
the whole point of `computes_command` is that the declaration is checkable.

What makes it safe enough to run at all
---------------------------------------
The destructive step is last, and only after the compressed bytes have been
proved twice -- once against the temporary file and once by reading the moved
`.gz` back off disk and decompressing it to the original bytes. If any check
fails the original is still where it was. There is no shell, no process, no
flag, and no second command in the table.

Refusals, all of them before any write:

* no path stated, a path outside the repository, or not a regular file;
* the sentence does not name the file;
* `<file>.gz` already exists -- this row never overwrites an archive, and the
  sentence would have to say so explicitly for a future one to;
* the file is larger than the size cap.

`output_verified` is true only when the bytes on disk decompress to exactly the
bytes that were read, and `source_removed` says plainly that the original is
gone -- the answer states the consequence rather than leaving it to be found.
"""
from __future__ import annotations

from canonical.runtime.bound_capabilities.stated_file_path import names_path

import gzip
import hashlib
import os
import pathlib
import re

_MAX_BYTES = 256 * 1024 * 1024


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args, root):
    root = pathlib.Path(root).resolve()
    if str(args.get("command") or "").strip().lower() != "compress":
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + str(args.get("command") or "<none>"))
    raw = args.get("path") or args.get("input_path")
    if not str(raw or "").strip():
        raise RuntimeError("PATH_REQUIRED")
    source = (root / str(raw)).resolve()
    if source != root and root not in source.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not source.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    stated = str(args.get("goal") or "")
    if not names_path(stated, source, root):
        raise RuntimeError("PATH_NOT_STATED_IN_THE_SENTENCE:" + source.name)
    if source.stat().st_size > _MAX_BYTES:
        raise RuntimeError("FILE_TOO_LARGE")

    # THE SENTENCE MUST NOT NAME A DESTINATION THIS ROW DOES NOT WRITE.
    #
    # Measured 2026-11-02, on the very first run of this row: the request was
    # "Compress <p>/a.txt into <p>/a.tar.gz".  `extract_argv` reads that as
    # `gzip <p>/a.txt` -- the "into" clause is not part of the command line -- so
    # the row was admitted and did gzip's own thing: it wrote `a.txt.gz` and
    # REMOVED `a.txt`.  The caller asked for an archive at a named path and got a
    # different file at a different path, plus the original gone.  An invented
    # destination on a destructive write is the worst answer this machine can
    # give, so a sentence that names any other path is refused outright.
    _named = set(re.findall(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", stated))
    _named |= set(re.findall(r"\b[\w-]+\.(?:gz|tgz|zip|tar|bz2|xz)\b", stated))
    _named.discard(source.relative_to(root).as_posix())
    _named.discard(source.name)
    if _named:
        raise RuntimeError(
            "THE_SENTENCE_NAMES_A_DESTINATION_THIS_ROW_DOES_NOT_WRITE:" + ",".join(sorted(_named))[:80])

    destination = source.with_name(source.name + ".gz")
    if destination.exists():
        raise RuntimeError("THE_ARCHIVE_ALREADY_EXISTS:" + destination.name)

    original = source.read_bytes()
    before = _digest(original)
    # mtime=0 keeps the header deterministic: the same bytes always produce the
    # same archive, so a re-run is comparable and a receipt can be replayed.
    packed = gzip.compress(original, mtime=0)
    if gzip.decompress(packed) != original:
        raise RuntimeError("COMPRESSION_DID_NOT_ROUNDTRIP")

    temporary = source.with_name(source.name + ".gz.brain-compress-tmp")
    # Claim the scratch path exclusively before writing.  In particular, an
    # existing file or symlink at the predictable name is somebody else's data:
    # do not truncate it and do not remove it in our cleanup.
    try:
        scratch = temporary.open("xb")
    except FileExistsError as exc:
        raise RuntimeError("TEMPORARY_PATH_ALREADY_EXISTS:" + temporary.name) from exc
    try:
        with scratch:
            scratch.write(packed)
        if _digest(temporary.read_bytes()) != _digest(packed):
            raise RuntimeError("THE_ARCHIVE_DID_NOT_LAND")
        # Publishing must also be exclusive: a destination can appear after
        # the earlier existence check. A hard link in the same directory fails
        # instead of overwriting that file (including a dangling symlink).
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise RuntimeError("THE_ARCHIVE_ALREADY_EXISTS:" + destination.name) from exc
    finally:
        if temporary.exists():
            temporary.unlink()

    landed = destination.read_bytes()
    if gzip.decompress(landed) != original:
        # Put the world back exactly as it was: the source was never touched and
        # a wrong archive has no business staying behind.
        destination.unlink(missing_ok=True)
        raise RuntimeError("THE_ARCHIVE_ON_DISK_DOES_NOT_MATCH_THE_SOURCE")

    source.unlink()
    if source.exists():
        raise RuntimeError("COMPRESS_LEFT_THE_SOURCE_IN_PLACE")

    return {"schema": "PROJECT_BRAIN_FILE_COMPRESS_V1", "adapter": "file_compress",
            "command": "compress",
            "path": source.relative_to(root).as_posix(),
            "destination_path": destination.relative_to(root).as_posix(),
            "source_sha256": before, "destination_sha256": _digest(landed),
            "original_byte_count": len(original), "byte_count": len(landed),
            "source_removed": True,
            "answer": destination.relative_to(root).as_posix(),
            "output_verified": True}
