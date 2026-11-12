#!/usr/bin/env python3
"""Every program that is this one with one line written as the task's own text writes it.

Why this exists
---------------
Measured 2026-11-12 (canonical/verification/FIX_CONTENT_IN_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json):
what a small fix of a real task is written with is named in the task's own issue text for half of
it (50 of 102 names and constants; another task's text names 2), and for 10 of 80 tasks the issue
quotes the changed line as a test-passing patch leaves it. Nine of those ten are tasks that no
list built here reaches within 200 candidates, because those lists are ordered by what fixes of
OTHER programs looked like. What a task writes out need not be learned from other tasks or
searched for. It can be read.

This is the smallest part of a list that takes its content from the task text: whole lines. The
larger part -- a small piece put into a line, written with the names the text points to -- is not
here.

What it does
------------
  the code lines of the text
        every line of the text, and every span between backticks in it, that reads as ONE Python
        statement on one line once a prompt (>>>, ..., $) or a diff sign (+, -) in front is set
        aside. The head of a compound statement counts (`if x is None:`), read with an empty
        body; an `elif` is read as the `if` it is. An expression counts only if it is a call:
        any word reads as a name, and "pre-commit" as a subtraction.
  in place of a line
        each code line in place of each statement line of the program it resembles: a simple
        statement for a simple one, a head for a head that begins with the same word, written
        text alike by at least MIN_ALIKE (difflib). The most alike first.
  next to a line
        then each simple code line put in before or after each statement line, at the depth of
        that line or of the next. The lines the text points at come first: a line weighs the
        names on it that the text mentions, each one over the number of lines that hold it.

Candidates are programs that compile, each once, in the text `ast.unparse` writes; the program
itself is never among them. Nothing here accepts a candidate: the caller's tests do. A line the
text quotes may be the line as it is, a line of another file, or the reporter's wrong guess.

What was found
--------------
See canonical/verification/QUOTED_LINE_PLACE_SWEBENCH_VERIFIED_20261112_V1.json, written by
canonical/tools/quoted_line_place_measure_v1.py.
"""
from __future__ import annotations

import ast
import collections
import difflib
import keyword
import re
import warnings
from typing import Iterator, Sequence

SCHEMA = "BRAIN_QUOTED_IN_THE_TASK_TEXT_V1"

MIN_ALIKE = 0.6          # how alike (difflib ratio of the written text) a line and the code line put in its place must be
SHORTEST = 8             # characters without blanks; a shorter line is not taken for code
AT_MOST = 400            # candidates made for one program

_PROMPTS = (">>> ", "... ", "$ ")
_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_KEYWORDS = frozenset(keyword.kwlist)
_CALLS = (ast.Call, ast.Await, ast.Yield, ast.YieldFrom)
_UNREADABLE = (SyntaxError, ValueError, RecursionError, MemoryError)


def _parsed(text: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.parse(text)


def _is_documentation(node: ast.AST) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _has_body(node: ast.AST) -> bool:
    body = getattr(node, "body", None)
    return isinstance(body, list) and bool(body) and isinstance(body[0], ast.stmt)


# --------------------------------------------------------------------------- #
# the code lines of a text
# --------------------------------------------------------------------------- #
def read_as_code(text: str) -> tuple[str, bool] | None:
    """(the statement as `ast.unparse` writes it, whether it is the head of a compound statement)
    when `text` reads as one statement on one line; None when it does not."""
    text = text.strip()
    if len("".join(text.split())) < SHORTEST:
        return None
    for source, head in ((text, False), (text + "\n    pass", True)):
        if head != text.endswith(":"):
            continue
        try:
            body = _parsed(source).body
        except _UNREADABLE:
            continue
        if len(body) != 1:
            continue
        statement = body[0]
        if isinstance(statement, ast.Expr) and not isinstance(statement.value, _CALLS):
            return None
        written = ast.unparse(statement)
        if head:
            if not _has_body(statement) or not written.endswith("\n    pass"):
                return None
            written = written[:-len("\n    pass")]
        if "\n" in written or len("".join(written.split())) < SHORTEST:
            return None
        return written, head
    return None


def code_lines(text: str) -> list[tuple[str, bool]]:
    """The code lines of a text, each once, in the order they stand."""
    out: list[tuple[str, bool]] = []
    for line in text.split("\n"):
        pieces = [line] + (line.split("`")[1::2] if "`" in line else [])
        for piece in pieces:
            piece = piece.strip().strip("`").strip()
            tries = [piece] + [piece[len(prompt):] for prompt in _PROMPTS if piece.startswith(prompt)]
            if piece[:1] in ("+", "-"):
                tries.append(piece[1:])
            tries.extend(one.strip()[2:] for one in list(tries) if one.strip().startswith("elif "))      # an elif is read as the if it is
            for one in tries:
                found = read_as_code(one)
                if found is not None:
                    if found not in out:
                        out.append(found)
                    break
    return out


# --------------------------------------------------------------------------- #
# the lines of a program
# --------------------------------------------------------------------------- #
def statement_lines(program: str) -> dict[int, bool]:
    """{the number of a line (from 1) on which a statement stands whole, or the head of a compound one: whether it is a head}.
    Documentation and statements written over several lines are left out."""
    out: dict[int, bool] = {}
    for node in ast.walk(_parsed(program)):
        if not isinstance(node, ast.stmt) or _is_documentation(node):
            continue
        if _has_body(node):
            out[node.lineno] = True
        elif node.end_lineno == node.lineno:
            out[node.lineno] = False
    return out


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def pointed_at(lines: Sequence[str], numbers: Sequence[int], text: str) -> list[int]:
    """The given line numbers, the lines the text points at first: a line weighs the names on it that
    the text mentions, each one over the number of lines that hold it; ties from the top."""
    mentioned = set(_WORD.findall(text))
    on = {number: set(_WORD.findall(lines[number - 1])) - _KEYWORDS for number in numbers}
    holding = collections.Counter(word for words in on.values() for word in words)
    weight = {number: sum(1.0 / holding[word] for word in words if word in mentioned) for number, words in on.items()}
    return sorted(numbers, key=lambda number: (-weight[number], number))


# --------------------------------------------------------------------------- #
# the candidates
# --------------------------------------------------------------------------- #
def _first_word(written: str) -> str:
    found = _WORD.match(written)
    word = found.group() if found else ""
    return "if" if word == "elif" else word


def _in_place(lines: Sequence[str], where: dict[int, bool], quoted: Sequence[tuple[str, bool]]) -> Iterator[list[str]]:
    found = []
    for order, (code, head) in enumerate(quoted):
        for number, is_head in where.items():
            if is_head != head:
                continue
            written = lines[number - 1].strip()
            new = "el" + code if head and written.startswith("elif ") and code.startswith("if ") else code
            if new == written or (head and _first_word(new) != _first_word(written)):
                continue
            matcher = difflib.SequenceMatcher(None, written, new, autojunk=False)
            if matcher.quick_ratio() < MIN_ALIKE:
                continue
            alike = matcher.ratio()
            if alike >= MIN_ALIKE:
                found.append((-alike, number, order, new))
    for _, number, _, new in sorted(found):
        yield list(lines[:number - 1]) + [_indent(lines[number - 1]) + new] + list(lines[number:])


def _next_to(lines: Sequence[str], where: dict[int, bool], quoted: Sequence[tuple[str, bool]], text: str) -> Iterator[list[str]]:
    simple = [code for code, head in quoted if not head]
    for number in pointed_at(lines, sorted(where), text):
        depths = [(number - 1, _indent(lines[number - 1])), (number, _indent(lines[number - 1]))]
        if number < len(lines) and _indent(lines[number]) != _indent(lines[number - 1]):
            depths.append((number, _indent(lines[number])))
        for code in simple:
            for at, depth in depths:
                yield list(lines[:at]) + [depth + code] + list(lines[at:])


def candidates(program: str, text: str, at_most: int = AT_MOST) -> list[str]:
    """The programs that are `program` with one code line of `text` in place of a line or next to one,
    in the order to try them. An empty list when the program cannot be read or the text has no code line."""
    try:
        normal = ast.unparse(_parsed(program))
        where = statement_lines(normal)
    except _UNREADABLE:
        return []
    quoted = code_lines(text)
    if not quoted:
        return []
    lines = normal.split("\n")
    out: list[str] = []
    seen = {normal}
    for made in (_in_place(lines, where, quoted), _next_to(lines, where, quoted, text)):
        for changed in made:
            if len(out) >= at_most:
                return out
            try:
                written = ast.unparse(_parsed("\n".join(changed)))
            except _UNREADABLE:
                continue
            if written not in seen:
                seen.add(written)
                out.append(written)
    return out
