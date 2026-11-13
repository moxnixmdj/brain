#!/usr/bin/env python3
"""Which file of a project a task's text points at, and the first changes to try from there.

Why this exists
---------------
canonical/runtime/function_the_task_text_points_at_v1.py orders the functions of a file by a
task's text, and its record (FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json)
was counted with the file handed over. A repair run is not handed the file either: it has the
project's tree and the text of the task. This is the step before, with the same source.

What it does
------------
  counted      the words of a file or of a text with how often each stands; the same words
               function_the_task_text_points_at_v1.words gives (identifiers whole and in their
               parts, Python's own words left out)
  document     a file as what is scored: the words of its text and of its path
  named        how much of a file's path the text writes out: 2 when the text holds the file
               with a directory in front of it (models/query.py, .../django/db/models/query.py)
               or its module path with a dot (models.query, django.db.models.query.QuerySet),
               1 when it holds the file name alone (query.py), 0 otherwise. A package's
               __init__.py is named by its directory (django/forms/__init__.py, or
               django.forms where no further name follows the dot).
  scores       BM25 of every document against the words of the text: the formula and the
               constants (k1 1.5, b 0.75) of the scorer this tree already has
               (canonical/runtime/bound_capabilities/objective_relevance_bm25.py), over counted
               words so that a project's files are not read again for every task
  order        the files, the one the text points at most first: the files it names before the
               others (2, then 1, then 0), inside each by score, ties by path
  candidates   for the first FILES files in that order: their functions ranked together by the
               text, and for the first FUNCTIONS of them the first OF_EACH programs
               canonical/runtime/quoted_in_the_task_text_v1.py makes: (path, function, new
               text). With one file this is function_the_task_text_points_at_v1.candidates for
               that file.

Nothing here accepts a candidate: the caller's tests do. Which files are a project's own (and
not its tests) is the caller's to say.

What was found
--------------
See canonical/verification/FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json, written
by canonical/tools/file_found_from_task_text_measure_v1.py.
"""
from __future__ import annotations

import collections
import math
from typing import Callable, Iterable, Mapping

from canonical.runtime import function_the_task_text_points_at_v1 as pointer
from canonical.runtime import quoted_in_the_task_text_v1 as quoted
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25

SCHEMA = "BRAIN_FILE_THE_TASK_TEXT_POINTS_AT_V1"

FILES = 1                # files that get candidates
K1, B = 1.5, 0.75        # the constants of the tree's scorer
WRITTEN_OUT, FILE_NAME_ONLY, NOT_NAMED = 2, 1, 0

_WORD_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_NAME_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_expanded: dict[str, tuple[str, ...]] = {}


def counted(text: str) -> collections.Counter:
    """The words of a text and how often each stands: Counter(pointer.words(text)), each different identifier taken apart once."""
    out: collections.Counter = collections.Counter()
    for word, times in collections.Counter(pointer._WORD.findall(text)).items():
        words = _expanded.get(word)
        if words is None:
            words = _expanded[word] = tuple(pointer.words(word))
        for one in words:
            out[one] += times
    return out


def document(path: str, source: str) -> collections.Counter:
    """A file as what is scored: the words of its text and the words of its path."""
    out = counted(source)
    out.update(counted(path.replace("/", " ").replace(".", " ")))
    return out


def _stands(text: str, written: str, a_name_may_follow_a_dot: bool = True) -> bool:
    """Whether `written` stands in the text as a whole: no letter, digit or underscore right before or right after it."""
    at = text.find(written)
    while at != -1:
        end = at + len(written)
        before_ok = at == 0 or text[at - 1] not in _WORD_CHARS
        after_ok = end == len(text) or text[end] not in _WORD_CHARS
        if after_ok and not a_name_may_follow_a_dot and end + 1 < len(text) and text[end] == "." and text[end + 1] in _NAME_START:
            after_ok = False
        if before_ok and after_ok:
            return True
        at = text.find(written, at + 1)
    return False


def named(path: str, text: str) -> int:
    """How much of the file's path the text writes out: WRITTEN_OUT, FILE_NAME_ONLY or NOT_NAMED."""
    parts = path.split("/")
    package = parts[-1] == "__init__.py"
    if package:
        parts = parts[:-1]
    elif parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    end = "/__init__.py" if package else ".py"
    if not parts:
        return NOT_NAMED
    if len(parts) >= 2:
        last_two = parts[-2:]
        if _stands(text, "/".join(last_two) + end) or _stands(text, ".".join(last_two), a_name_may_follow_a_dot=not package):
            return WRITTEN_OUT
    if _stands(text, parts[-1] + end):
        return WRITTEN_OUT if package else FILE_NAME_ONLY
    return NOT_NAMED


def scores(documents: Mapping[str, Mapping[str, int]], words: Iterable[str]) -> dict[str, float]:
    """BM25 of each document against the words; what the tree's scorer gives for the same words in lists."""
    names = list(documents)
    if not names:
        return {}
    lengths = {name: sum(documents[name].values()) for name in names}
    average = sum(lengths.values()) / len(names)
    if average <= 0:
        return {name: 0.0 for name in names}
    asked = list(dict.fromkeys(words))
    held = {word: sum(1 for name in names if word in documents[name]) for word in asked}
    weight = {word: math.log(1.0 + (len(names) - held[word] + 0.5) / (held[word] + 0.5)) for word in asked if held[word]}
    out = {}
    for name in names:
        counts = documents[name]
        norm = K1 * (1.0 - B + B * lengths[name] / average)
        score = 0.0
        for word, idf in weight.items():
            times = counts.get(word, 0)
            if times:
                score += idf * (times * (K1 + 1.0) / (times + norm))
        out[name] = score
    return out


def order(documents: Mapping[str, Mapping[str, int]], text: str, use_names: bool = True) -> list[str]:
    """The files, the one the text points at most first. With `use_names` off: by score alone."""
    found = scores(documents, pointer.words(text))
    level = {path: named(path, text) if use_names else NOT_NAMED for path in documents}
    return sorted(documents, key=lambda path: (-level[path], -found[path], path))


def candidates(documents: Mapping[str, Mapping[str, int]], source_of: Callable[[str], str], text: str, files_tried: int = FILES,
               functions: int = pointer.FUNCTIONS, of_each: int = pointer.OF_EACH,
               in_order: list[str] | None = None) -> list[tuple[str, pointer.Function, str]]:
    """(path, function, its new text): the functions of the first `files_tried` files ranked together by the text,
    `of_each` candidates for each of the first `functions` of them, function by function."""
    tried = (order(documents, text) if in_order is None else in_order)[:files_tried]
    rows: list[tuple[str, str, pointer.Function]] = []
    texts: list[list[str]] = []
    for path in tried:
        source = source_of(path)
        lines = source.split("\n")
        for function in pointer.functions_of(source):
            rows.append((path, source, function))
            texts.append(pointer.words(" ".join(function.name.split(".")[:-1]) + "\n" + "\n".join(lines[function.first - 1:function.last])))
    if not rows:
        return []
    scored = [row[0] if isinstance(row, tuple) else row for row in bm25._bm25_scores(pointer.words(text), texts)]
    out: list[tuple[str, pointer.Function, str]] = []
    for _, at in sorted(zip([-score for score in scored], range(len(rows))))[:functions]:
        path, source, function = rows[at]
        out.extend((path, function, made) for made in quoted.candidates(pointer.text_of(source, function), text, at_most=of_each))
    return out
