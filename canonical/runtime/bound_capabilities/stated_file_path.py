"""Conservative path-token matching for destructive file operations.

A basename inside another filename or inside a different directory path is not
permission to mutate a bound path. Full repository paths are compared after
resolution. Bare source names resolve only against the repository root; a bare
destination may also denote a sibling of the explicitly stated source.

This is a path-identity guard, not a complete natural-language intent parser.
Ambiguous names and spellings outside the bounded path grammar fail closed.
"""
from __future__ import annotations

import pathlib
import re

_TOKEN = re.compile(r"(?<![\w./~-])/?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*(?![\w./~-])")
_URL = re.compile(r"https?://[^\s)\]}>]+", re.I)


def names_path(goal: str, target: pathlib.Path, root: pathlib.Path, *,
               sibling_of: pathlib.Path | None = None) -> bool:
    root = root.resolve()
    target = target.resolve()
    if target == root or root not in target.parents:
        return False
    for match in _TOKEN.finditer(_URL.sub(" ", str(goal or ""))):
        token = match.group().rstrip(".,;:!?")
        if not token or token in (".", ".."):
            continue
        if "/" in token:
            if (root / token).resolve() == target:
                return True
        elif token == target.name:
            # A bare input cannot authorize an inferred file in an arbitrary
            # subdirectory. A bare output can only be the stated source's sibling.
            if (root / token).resolve() == target:
                return True
            if sibling_of is not None and (sibling_of.parent / token).resolve() == target:
                return True
    return False


def names_ordered_pair(goal: str, source: pathlib.Path, destination: pathlib.Path,
                       root: pathlib.Path) -> bool:
    """Require the source and destination in their stated roles, not just anywhere.

    Accept only an unambiguous single destination preposition. Complex requests
    fail closed rather than guessing which file is the source.
    """
    text = _URL.sub(" ", str(goal or ""))
    separators = list(re.finditer(r"\b(?:to|into|onto|named|called)\s+", text, re.I))
    if len(separators) != 1:
        return False
    separator = separators[0]
    return (names_path(text[:separator.start()], source, root) and
            names_path(text[separator.end():], destination, root, sibling_of=source))
