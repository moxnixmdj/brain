#!/usr/bin/env python3
"""Recompute a taught-words answer from the file, without the code that produced it.

``taught_words_v1.run`` produces the answer.  This module is the door's side of the check: it reads
the stated file itself, confirms the digest the adapter reported, and recomputes the value of the
reported operation with its own splitting, filtering and reducing.  It imports nothing from the
producer.  What it checks is that the OPERATION was carried out correctly on THAT file.  It does not
check that the operation is what the sentence asked for; that is the lexicon's job, and the lessons'.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

_UNITS = {"lines", "words", "characters", "bytes", "numbers"}
_REDUCERS = {"count", "sum", "max", "min"}
_KNOWN = _UNITS | _REDUCERS | {"rest", "containing", "blank", "unique", "lengths"}


def recompute(program, data, raw):
    """The value of ``program`` on the bytes ``raw``; None when the program is not a valid one."""
    wanted = set(program)
    if not wanted <= _KNOWN:
        return None
    kinds, ways = sorted(wanted & _UNITS), sorted(wanted & _REDUCERS)
    if len(kinds) != 1 or len(ways) != 1:
        return None
    kind, way = kinds[0], ways[0]
    textual = kind in ("lines", "words", "characters")
    if kind == "bytes":
        things = [raw[i] for i in range(len(raw))]
    else:
        text = raw.decode("utf-8")
        if kind == "lines":
            things = [m.group(1) for m in re.finditer(r"([^\n]*)\n", text)]
            tail = text[text.rfind("\n") + 1:]
            if tail:
                things.append(tail)
        elif kind == "words":
            things = re.findall(r"\S+", text)
        elif kind == "characters":
            things = [ch for ch in text]
        else:
            things = [int(m) for m in re.findall(r"(?<!\S)-?\d+(?!\S)", text)]
    if "rest" in wanted:
        del things[:1]
    if "containing" in wanted:
        if not textual or not isinstance(data, str) or data == "":
            return None
        things = [t for t in things if t.find(data) != -1]
    elif data not in (None, ""):
        return None
    if "blank" in wanted:
        if kind != "lines":
            return None
        things = [t for t in things if len(t) == 0]
    if "unique" in wanted:
        seen, kept = set(), []
        for t in things:
            if t not in seen:
                seen.add(t)
                kept.append(t)
        things = kept
    measured = kind == "numbers"
    if "lengths" in wanted:
        if not textual or way == "count":
            return None
        things = [sum(1 for _ in t) for t in things]
        measured = True
    if way == "count":
        n = 0
        for _ in things:
            n += 1
        return n
    if not measured or not things:
        return None
    if way == "sum":
        total = 0
        for t in things:
            total += t
        return total
    ordered = sorted(things)
    return ordered[-1] if way == "max" else ordered[0]


def verify(expect, result, args, root):
    """(ok, detail) -- the interface ``_check_expectation`` gives its independent verifiers."""
    root = pathlib.Path(root).resolve()
    stated = str((args or {}).get("path") or "")
    target = (root / stated).resolve()
    if not stated or root not in target.parents or not target.is_file():
        return False, "TAUGHT_ANSWER_SOURCE_NOT_A_FILE_INSIDE_THE_ROOT"
    if (root / str(result.get("path") or "")).resolve() != target:
        return False, "TAUGHT_ANSWER_READ_A_DIFFERENT_FILE"
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != str(result.get("source_sha256") or ""):
        return False, "TAUGHT_ANSWER_SOURCE_DIGEST_DIFFERS"
    claimed = result.get(str(expect.get("field") or "answer"))
    if isinstance(claimed, bool) or not isinstance(claimed, int):
        return False, "TAUGHT_ANSWER_NOT_A_WHOLE_NUMBER"
    try:
        mine = recompute(result.get("program") or [], result.get("data"), raw)
    except Exception as exc:  # noqa: BLE001 - a checker that cannot recompute has not confirmed
        return False, "TAUGHT_ANSWER_NOT_RECOMPUTABLE:" + type(exc).__name__
    if mine is None or mine != claimed:
        return False, "TAUGHT_ANSWER_RECOMPUTED_DIFFERENTLY:claimed=%r:recomputed=%r" % (claimed, mine)
    return True, ""
