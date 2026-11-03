#!/usr/bin/env python3
"""Count the lines of one repository-local file. Python stdlib, nothing else.

Why this exists
---------------
The front door served 1 of 25 ordinary requests measured on `ec94c97`
("count the lines in a.txt", "what is the size of a.txt", "copy a to c"...).
Twelve of the refusals were not real safety refusals: routing proposed no
capability at all, and the last tier reported the computer-execution boundary
because there was nothing to dispatch. The registry simply had no row for a
file fact -- it had writers (`text.file.write`, `json.file.write`) and
extractors, but nothing that answers a question about a file it only reads.

This adapter is that row for one fact: how many lines. It is deliberately the
smallest useful thing, because the point of the change is not this counter --
it is proving the whole path end to end (route -> bind -> dispatch -> verified
answer) on an ordinary sentence instead of only on curated ones.

What it does not do: it never writes, never imports the target file, never
spawns a process, and never follows a path outside the repository root. The
count is the number of ``str.splitlines()`` elements of the decoded text, which
is the same number `wc -l` gives when the file ends with a newline and one
higher when it does not; that difference is reported (`ends_with_newline`)
rather than hidden.
"""
from __future__ import annotations

import hashlib
import pathlib


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    """Resolve inside the repository, refusing anything that escapes it."""
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    # This capability is registered read-only. A report path would make it a
    # writer and may be synthesized by the binder, so refuse it before reads.
    if args.get("output_path"):
        raise RuntimeError("READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH")
    root = pathlib.Path(root).resolve()
    source = _safe(root, args.get("path") or args.get("input_path") or "")
    if not source.name:
        raise RuntimeError("PATH_REQUIRED")
    if not source.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    raw = source.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("NOT_UTF8_TEXT") from exc
    lines = text.splitlines()
    count = len(lines)
    ends_with_newline = text.endswith("\n")
    payload = {
        "schema": "PROJECT_BRAIN_FILE_LINE_COUNT_V1",
        "adapter": "file_line_count",
        "path": source.relative_to(root).as_posix(),
        "line_count": count,
        # Exactly what `wc -l` prints: the number of newline BYTES.  Kept as its
        # own field because it agrees with `line_count` only when the last line
        # is terminated, and a caller comparing against `wc -l` deserves the
        # number `wc -l` would give rather than a reconciliation done for them.
        "newline_count": raw.count(b"\n"),
        "ends_with_newline": ends_with_newline,
        "byte_count": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "answer": count,
    }
    payload.update({"output_path": None, "output_verified": True})
    return payload
