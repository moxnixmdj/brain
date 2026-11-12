#!/usr/bin/env python3
"""Which function of a file a task's text points at, and the first few changes to try in each.

Why this exists
---------------
Every list of candidate repairs counted here so far was handed the function to change
(canonical/verification/SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json,
QUOTED_LINE_PLACE_SWEBENCH_VERIFIED_20261112_V1.json). A repair run is not handed it: it has a
tree of files and the text of a task. The text of the task was measured to point at the line
inside the function (FIX_CONTENT_IN_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json). This is the
step before that one, with the same source: the text orders the functions of a file.

What it does
------------
  functions      every function of the file, methods and nested ones too, each from its first
                 decorator to its last line
  the order      each function's text is scored against the words of the task text with BM25,
                 the scorer this tree already has
                 (canonical/runtime/bound_capabilities/objective_relevance_bm25.py, k1 1.5,
                 b 0.75, each function of the file one document). A function's text is its
                 lines and the names of what it stands in (its class). A word is an identifier,
                 whole as written and in its parts in small letters (RenameContentType: also
                 rename, content, type; update_fields: also update, fields); Python's own words
                 are left out. Ties go from the top of the file.
  candidates     for the first FUNCTIONS functions in that order, the first OF_EACH programs
                 canonical/runtime/quoted_in_the_task_text_v1.py makes for each, function by
                 function: (the function, its new text).
  written_into   the file with a function's new text in its place. The new text is as
                 `ast.unparse` writes it, so comments inside that one function are lost and a
                 documentation string is indented anew.

Nothing here accepts a candidate: the caller's tests do. Nothing here finds the file.

What was found
--------------
See canonical/verification/FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json,
written by canonical/tools/function_found_from_task_text_measure_v1.py.
"""
from __future__ import annotations

import ast
import keyword
import re
import textwrap
import warnings
from typing import NamedTuple, Sequence

from canonical.runtime import quoted_in_the_task_text_v1 as quoted
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25

SCHEMA = "BRAIN_FUNCTION_THE_TASK_TEXT_POINTS_AT_V1"

FUNCTIONS = 4            # functions of the file that get candidates
OF_EACH = 5              # candidates for each of them
SHORTEST_PART = 3        # letters; a shorter part of an identifier is not a word of its own

_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_PART = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
_KEYWORDS = frozenset(keyword.kwlist)
_UNREADABLE = (SyntaxError, ValueError, RecursionError, MemoryError)


class Function(NamedTuple):
    first: int           # the line of its first decorator, or of its `def`, counted from 1
    last: int            # its last line
    name: str            # as it is called in full: Class.method, outer.inner


def _parsed(text: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.parse(text)


def functions_of(source: str) -> list[Function]:
    """Every function of a file, from the top. An empty list when the file cannot be read."""
    try:
        tree = _parsed(source)
    except _UNREADABLE:
        return []
    out: list[Function] = []

    def go(node: ast.AST, above: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = above + [child.name]
                if not isinstance(child, ast.ClassDef):
                    first = min([child.lineno] + [decorator.lineno for decorator in child.decorator_list])
                    out.append(Function(first, child.end_lineno or child.lineno, ".".join(name)))
                go(child, name)
            elif isinstance(child, ast.stmt):
                go(child, above)

    go(tree, [])
    return sorted(out)


def words(text: str) -> list[str]:
    """The words of a text or of a piece of program: every identifier as written, and after it its
    parts in small letters where it has parts or capitals."""
    out: list[str] = []
    for word in _WORD.findall(text):
        if word in _KEYWORDS:
            continue
        out.append(word)
        for part in _PART.findall(word):
            part = part.lower()
            if part != word and len(part) >= SHORTEST_PART and part not in _KEYWORDS:
                out.append(part)
    return out


def text_of(source: str, function: Function) -> str:
    """The function as it stands in the file, moved to the left margin."""
    return textwrap.dedent("\n".join(source.split("\n")[function.first - 1:function.last]))


def order(source: str, text: str, functions: Sequence[Function] | None = None) -> list[Function]:
    """The functions of the file, the one the text points at most first; ties from the top."""
    found = functions_of(source) if functions is None else list(functions)
    if not found:
        return []
    lines = source.split("\n")
    documents = [words(" ".join(function.name.split(".")[:-1]) + "\n" + "\n".join(lines[function.first - 1:function.last])) for function in found]
    scores = [row[0] if isinstance(row, tuple) else row for row in bm25._bm25_scores(words(text), documents)]
    return [function for _, function in sorted(zip([-score for score in scores], found))]


def candidates(source: str, text: str, functions: int = FUNCTIONS, of_each: int = OF_EACH) -> list[tuple[Function, str]]:
    """(the function, its new text) for the first `functions` functions the text points at, `of_each` for each, function by function."""
    out: list[tuple[Function, str]] = []
    for function in order(source, text)[:functions]:
        out.extend((function, made) for made in quoted.candidates(text_of(source, function), text, at_most=of_each))
    return out


def written_into(source: str, function: Function, new_text: str) -> str:
    """The file with the function's new text where the function stood, at the function's depth."""
    lines = source.split("\n")
    head = lines[function.first - 1]
    depth = head[:len(head) - len(head.lstrip())]
    new = [depth + line if line.strip() else line for line in new_text.split("\n")]
    return "\n".join(lines[:function.first - 1] + new + lines[function.last:])
