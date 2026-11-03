#!/usr/bin/env python3
"""`tar czf <archive> <file>` -- in process, and additive by construction.

The sentence "Compress <p>/a.txt into <p>/a.tar.gz" names a source and a
destination.  It is not gzip's sentence: `gzip <file>` writes `<file>.gz` and
removes the source, so a row that computes that argv has nowhere to put the
archive the sentence named.  This module computes the argv the sentence *does*
settle -- `tar czf <destination> <source>` -- and nothing else.

Why this is the safe shape rather than the risky one
----------------------------------------------------
`tar czf` COPIES the named member into an archive.  It does not remove, move or
rewrite its input, so the destructive step that makes `gzip` a decision at all
is simply absent here: after this row runs, the source is still where it was,
byte for byte.  That is stated in the answer (`source_removed: false`,
`source_kept: true`) rather than left to be discovered.

The write is still verified rather than assumed.  The archive is built in
memory, written to a temporary file beside its destination and published in place
with an exclusive hard link, then RE-OPENED FROM DISK and its member decompressed and
compared with the bytes that were read.  If that comparison fails the archive is
removed and the call raises, so a corrupt archive is never left behind as if it
were the requested one.

Refusals, all of them before any write:

* no source path, or a source outside the repository, or not a regular file;
* no destination path, or a destination outside the repository, or one whose
  parent directory does not exist (this row does not create directories);
* a destination that is not a tar archive path (`.tar.gz` / `.tgz`);
* a destination equal to the source;
* a destination that already exists -- this row never overwrites an archive;
* either path not stated in the sentence the row was given;
* a source larger than the size cap.

There is no shell, no subprocess and no second command in the table: the bytes
are produced with the standard library's `tarfile` and `gzip`.
"""
from __future__ import annotations

from canonical.runtime.bound_capabilities.stated_file_path import names_ordered_pair, names_path

import gzip
import hashlib
import io
import os
import pathlib
import tarfile

_MAX_BYTES = 256 * 1024 * 1024
_ARCHIVE_SUFFIXES = (".tar.gz", ".tgz")
_MEMBER_MTIME = 0


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pack(name: str, data: bytes, mode: int) -> bytes:
    """A tar.gz holding exactly one member, with no clock or ownership in it.

    Deterministic on purpose: the same bytes always produce the same archive, so
    a re-run is comparable and a receipt can be replayed.  A tar header carries
    a modification time and an owner; both are pinned so they cannot vary.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=_MEMBER_MTIME) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = _MEMBER_MTIME
            info.mode = mode
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _unpack(packed: bytes, name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(packed), mode="r:gz") as archive:
        member = archive.getmember(name)
        handle = archive.extractfile(member)
        if handle is None:  # pragma: no cover - a non-file member cannot be read
            raise RuntimeError("ARCHIVE_MEMBER_IS_NOT_A_FILE:" + name)
        return handle.read()


def run(args, root):
    root = pathlib.Path(root).resolve()
    if str(args.get("command") or "").strip().lower() != "compress":
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + str(args.get("command") or "<none>"))

    raw_source = args.get("path") or args.get("input_path")
    if not str(raw_source or "").strip():
        raise RuntimeError("PATH_REQUIRED")
    source = (root / str(raw_source)).resolve()
    if source != root and root not in source.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + str(raw_source))

    raw_destination = args.get("output_path") or args.get("destination_path")
    if not str(raw_destination or "").strip():
        raise RuntimeError("DESTINATION_REQUIRED")
    destination = (root / str(raw_destination)).resolve()
    if destination != root and root not in destination.parents:
        raise RuntimeError("DESTINATION_OUTSIDE_REPOSITORY:" + str(raw_destination))

    stated = str(args.get("goal") or "")
    source_rel = source.relative_to(root).as_posix()
    destination_rel = destination.relative_to(root).as_posix()
    if not names_path(stated, source, root):
        raise RuntimeError("PATH_NOT_STATED_IN_THE_SENTENCE:" + source.name)
    if not names_path(stated, destination, root, sibling_of=source):
        raise RuntimeError("DESTINATION_NOT_STATED_IN_THE_SENTENCE:" + destination.name)

    if not names_ordered_pair(stated, source, destination, root):
        raise RuntimeError("STATED_PATH_ROLES_MISMATCH")
    if not source.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE:" + source_rel)
    if source.stat().st_size > _MAX_BYTES:
        raise RuntimeError("FILE_TOO_LARGE")
    if source == destination:
        raise RuntimeError("THE_DESTINATION_IS_THE_SOURCE")
    if not destination.name.lower().endswith(_ARCHIVE_SUFFIXES):
        raise RuntimeError("DESTINATION_IS_NOT_A_TAR_ARCHIVE:" + destination.name)
    if not destination.parent.is_dir():
        raise RuntimeError("DESTINATION_DIRECTORY_MISSING:" + destination.parent.as_posix())
    if destination.exists():
        raise RuntimeError("THE_ARCHIVE_ALREADY_EXISTS:" + destination_rel)

    original = source.read_bytes()
    before = _digest(original)
    packed = _pack(source.name, original, source.stat().st_mode & 0o777)
    if _unpack(packed, source.name) != original:
        raise RuntimeError("THE_ARCHIVE_DID_NOT_ROUNDTRIP")

    temporary = destination.with_name(destination.name + ".brain-tar-tmp")
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
    try:
        recovered = _unpack(landed, source.name)
    except Exception as exc:  # noqa: BLE001 - a bad archive is data, not a crash
        destination.unlink(missing_ok=True)
        raise RuntimeError("THE_ARCHIVE_ON_DISK_IS_NOT_READABLE:" + str(exc)[:120]) from None
    if recovered != original:
        destination.unlink(missing_ok=True)
        raise RuntimeError("THE_ARCHIVE_ON_DISK_DOES_NOT_MATCH_THE_SOURCE")
    if not source.is_file() or source.read_bytes() != original:
        raise RuntimeError("THE_SOURCE_CHANGED_WHILE_ARCHIVING")

    return {"schema": "PROJECT_BRAIN_FILE_ARCHIVE_TAR_V1", "adapter": "file_archive_tar",
            "command": "compress",
            "path": source_rel,
            "destination_path": destination_rel,
            "member_name": source.name,
            "source_sha256": before,
            "destination_sha256": _digest(landed),
            "original_byte_count": len(original),
            "byte_count": len(landed),
            # This row copies; it never removes.  Said plainly in the answer.
            "source_removed": False,
            "source_kept": True,
            "answer": destination_rel,
            "output_verified": True}
