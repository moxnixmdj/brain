#!/usr/bin/env python3
"""Answer a question about one repository-local file from words that were taught by example.

The sentence is read with the lexicon of ``canonical/runtime/taught_words_v1.py``.  The adapter
answers only when every word of the sentence is a taught word, a structure word, the file, or the
text to look for, and the meanings make exactly one operation.  It refuses otherwise and names the
word.  It never writes, never starts a process, never imports the target file, and never follows a
path outside the repository root.  Python stdlib, nothing else.
"""
from __future__ import annotations

import hashlib
import pathlib


def _taught():
    from canonical.runtime import taught_words_v1 as module
    return module


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    """Resolve inside the repository, refusing anything that escapes it."""
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    if args.get("output_path"):
        raise RuntimeError("READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH")
    goal = str(args.get("goal") or "")
    if not goal.strip():
        raise RuntimeError("SENTENCE_REQUIRED")
    root = pathlib.Path(root).resolve()
    source = _safe(root, args.get("path") or "")
    if not source.name:
        raise RuntimeError("PATH_REQUIRED")
    if not source.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    taught = _taught()
    named = taught.split_request(goal)[0]
    if len(named) != 1 or _safe(root, named[0]) != source:
        raise RuntimeError("SENTENCE_DOES_NOT_NAME_EXACTLY_THIS_FILE")
    raw = source.read_bytes()
    if len(raw) > taught.MAX_BYTES:
        raise RuntimeError("FILE_TOO_LARGE")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("NOT_UTF8_TEXT") from exc
    lexicon, lessons_sha256 = taught.load_lexicon()
    reading = taught.interpret(lexicon, goal, text)
    if not reading["ok"]:
        raise RuntimeError("TAUGHT_WORDS_DO_NOT_ACCOUNT_FOR_THE_SENTENCE:" + reading["reason"])
    return {
        "schema": "PROJECT_BRAIN_FILE_QUESTION_TAUGHT_WORDS_V1",
        "adapter": "file_question_taught_words",
        "path": source.relative_to(root).as_posix(),
        "program": reading["parts"],
        "data": reading["data"],
        "word_meanings": reading["meanings"],
        "lessons_sha256": lessons_sha256,
        "byte_count": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "answer": reading["value"],
        "output_path": None,
        "output_verified": True,
    }
