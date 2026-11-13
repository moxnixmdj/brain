#!/usr/bin/env python3
"""One annotation shows a direction; the family follows it.

Python has two spellings for the same generic annotation: the builtin subscript (``list[int]``,
``dict[str, int]``) introduced in 3.9, and the ``typing`` name (``List[int]``,
``Dict[str, int]``) that older code uses. A migration changes one spelling to the other for the
whole family, and a single changed annotation is enough to say which way.

This operator reads the direction from the example's own before/after:

    before: list[Any]          after: List[Any]          -> up   (builtin -> typing)
    before: List[Any]          after: list[Any]          -> down (typing -> builtin)

and applies the *family* in that direction:

    list -> List    dict -> Dict    set -> Set    tuple -> Tuple
    frozenset -> FrozenSet    type -> Type

The family is knowledge, not an inference: the example shows one pair, and the operator says the
migration is the PEP 585 family. The measurement is what justifies that. If the example shows
both directions (one pair up, another down), nothing is applied.

Imports follow mechanically, and only for a top-level ``from typing import ...`` line:

* up: the mapped names the edited file now uses are added to that line (created if absent),
  kept in spelling order;
* down: the typing names no longer used anywhere in the file are removed from it, and the line
  is removed when it becomes empty.

The edit replaces the identifier bytes of each subscript base and splices the import line, so the
rest of the file keeps its formatting. The result is parsed before it is returned.
"""
from __future__ import annotations

import ast

FAMILY: tuple[tuple[str, str], ...] = (
    ("list", "List"),
    ("dict", "Dict"),
    ("set", "Set"),
    ("tuple", "Tuple"),
    ("frozenset", "FrozenSet"),
    ("type", "Type"),
)
BY_TYPING = {typing: builtin for builtin, typing in FAMILY}
ABC_NAMES = frozenset({
    "Callable", "Iterable", "Iterator", "Mapping", "MutableMapping", "Sequence",
    "MutableSequence", "Collection", "Container", "Generator", "AsyncIterable",
    "AsyncIterator", "Awaitable", "Coroutine", "Hashable", "Sized",
})
SCHEMA = "BRAIN_GENERIC_ALIAS_V1"


class Refused(Exception):
    """The example does not show one direction the family can follow."""


def _subscripts(tree: ast.AST) -> set[tuple[str, str]]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            found.add((node.value.id, ast.unparse(node.slice)))
    return found


def direction(before: str, after: str) -> dict[str, str] | None:
    """The family mapping the example shows, or None when it shows no one direction."""
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError):
        return None
    was, is_now = _subscripts(old), _subscripts(new)
    up = any((builtin, inside) in was and (typing, inside) in is_now
             for builtin, typing in FAMILY for inside in (piece[1] for piece in was if piece[0] == builtin))
    down = any((typing, inside) in was and (builtin, inside) in is_now
               for builtin, typing in FAMILY for inside in (piece[1] for piece in was if piece[0] == typing))
    if up == down:                       # neither, or both directions at once
        return None
    return dict(FAMILY) if up else {typing: builtin for builtin, typing in FAMILY}


def abc_moves(before: str, after: str) -> set[str]:
    """Names the example moved from ``typing`` to ``collections.abc`` (the PEP 585 companions)."""
    def imported(tree):
        typing, abc = set(), set()
        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom) and not statement.level:
                names = {alias.asname or alias.name for alias in statement.names}
                if statement.module == "typing":
                    typing |= names
                elif statement.module == "collections.abc":
                    abc |= names
        return typing, abc
    try:
        was, is_now = imported(ast.parse(before)), imported(ast.parse(after))
    except (SyntaxError, ValueError):
        return set()
    moved = ((was[0] & is_now[1]) - was[1]) & ABC_NAMES
    # One companion moving is the family moving: the same migration takes every abc-compatible
    # name it finds.  The intersection with the target's own typing imports keeps this bounded.
    return set(ABC_NAMES) if moved else set()


def _offset(text: str, line: int, column: int) -> int:
    lines = text.splitlines(keepends=True)
    return sum(len(piece) for piece in lines[:line - 1]) + column


def _names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _typing_lines(tree: ast.AST) -> list[ast.ImportFrom]:
    return [node for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "typing"]


def _splice(text: str, statement: ast.AST, replacement: str) -> str:
    start = _offset(text, statement.lineno, statement.col_offset)
    end = _offset(text, statement.end_lineno, statement.end_col_offset)
    return text[:start] + replacement + text[end:]


def _relocate(text: str, moves: set[str]) -> str:
    """Move the named imports from ``typing`` to ``collections.abc``, in the line's own place."""
    if not moves:
        return text
    tree = ast.parse(text)
    typing_lines = [node for node in tree.body
                    if isinstance(node, ast.ImportFrom) and not node.level and node.module == "typing"]
    moves = moves & {alias.name for line in typing_lines for alias in line.names}
    if not moves:
        return text
    abc_lines = [node for node in tree.body
                 if isinstance(node, ast.ImportFrom) and not node.level and node.module == "collections.abc"]
    edits: list[tuple[int, int, str]] = []
    if abc_lines:
        line = abc_lines[0]
        names = sorted({alias.name for alias in line.names} | moves)
        edits.append((_offset(text, line.lineno, line.col_offset),
                      _offset(text, line.end_lineno, line.end_col_offset),
                      "from collections.abc import " + ", ".join(names)))
        for line in typing_lines:
            kept = [alias for alias in line.names if alias.name not in moves]
            if len(kept) == len(line.names):
                continue
            start = _offset(text, line.lineno, line.col_offset)
            end = _offset(text, line.end_lineno, line.end_col_offset)
            if kept:
                edits.append((start, end, "from typing import " + ", ".join(alias.name for alias in kept)))
            else:
                while end < len(text) and text[end] in "\r\n":
                    end += 1
                edits.append((start, end, ""))
    else:
        # Replace the typing line the moved name stood on, so the abc import lands where the
        # person put it, not at the end of the import block.
        holder = None
        for line in typing_lines:
            if any(alias.name in moves for alias in line.names):
                holder = line
                break
        if holder is None:
            return text
        kept = [alias for alias in holder.names if alias.name not in moves]
        replacement = "from collections.abc import " + ", ".join(sorted(moves))
        if kept:
            replacement = "from typing import " + ", ".join(alias.name for alias in kept) + "\n" + replacement
        edits.append((_offset(text, holder.lineno, holder.col_offset),
                      _offset(text, holder.end_lineno, holder.end_col_offset), replacement))
        for line in typing_lines:
            if line is holder:
                continue
            kept = [alias for alias in line.names if alias.name not in moves]
            if len(kept) == len(line.names):
                continue
            start = _offset(text, line.lineno, line.col_offset)
            end = _offset(text, line.end_lineno, line.end_col_offset)
            if kept:
                edits.append((start, end, "from typing import " + ", ".join(alias.name for alias in kept)))
            else:
                while end < len(text) and text[end] in "\r\n":
                    end += 1
                edits.append((start, end, ""))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def _imports(text: str, mapping: dict[str, str]) -> str:
    """The typing import line follows the names the edited file now uses (or stops using)."""
    tree = ast.parse(text)
    used = _names(tree)
    typing_names = set(BY_TYPING)
    wanted = sorted({name for name in mapping.values() if name in typing_names and name in used})
    dropped = {name for name in mapping if name in typing_names and name not in used}
    lines = _typing_lines(tree)
    if wanted:
        if lines:
            line = lines[0]
            names = sorted({alias.name for alias in line.names} | set(wanted))
            return _splice(text, line, "from typing import " + ", ".join(names))
        newline = "\r\n" if "\r\n" in text else "\n"
        rows = text.splitlines(keepends=True)
        last = None
        for statement in tree.body:
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                last = statement
        at = last.end_lineno if last is not None else 0
        rows.insert(at, "from typing import " + ", ".join(wanted) + newline)
        return "".join(rows)
    if not dropped or not lines:
        return text
    text_now = text
    for line in sorted(lines, key=lambda node: (node.lineno, node.col_offset), reverse=True):
        kept = [alias for alias in line.names if alias.name not in dropped]
        if len(kept) == len(line.names):
            continue
        if not kept:
            start = _offset(text_now, line.lineno, line.col_offset)
            end = _offset(text_now, line.end_lineno, line.end_col_offset)
            while end < len(text_now) and text_now[end] in "\r\n":
                end += 1
            text_now = text_now[:start] + text_now[end:]
        else:
            text_now = _splice(text_now, line, "from typing import " + ", ".join(alias.name for alias in kept))
    return text_now


def apply(target: str, before: str, after: str) -> tuple[str | None, dict[str, object]]:
    """The target with the family changed in the example's direction, or (None, {})."""
    mapping = direction(before, after)
    if not mapping:
        return None, {}
    try:
        tree = ast.parse(target)
    except (SyntaxError, ValueError):
        return None, {}
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in mapping:
            spans.append((node.value, mapping[node.value.id]))
    if not spans:
        return None, {}
    text = target
    for node, new in sorted(spans, key=lambda pair: (pair[0].lineno, pair[0].col_offset), reverse=True):
        start = _offset(text, node.lineno, node.col_offset)
        end = _offset(text, node.end_lineno, node.end_col_offset)
        text = text[:start] + new + text[end:]
    try:
        text = _imports(text, mapping)
        text = _relocate(text, abc_moves(before, after))
        ast.parse(text)
    except (SyntaxError, ValueError) as problem:
        raise Refused("the changed file would not parse (%s)" % problem)
    return text, {"direction": "up" if mapping.get("list") == "List" else "down",
                  "names": len(spans)}


def main(argv=None) -> int:
    import argparse
    import pathlib
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("file")
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args(argv)
    read = lambda path: pathlib.Path(path).read_text(encoding="utf-8")
    text, did = apply(read(args.file), read(args.before), read(args.after))
    if text is None:
        print("REFUSED: the example shows no one direction")
        return 1
    print(text, end="")
    print("did:", did)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
