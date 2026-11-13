#!/usr/bin/env python3
"""Bring a name the file already imports from the same module, then let the organ edit.

Why this exists
---------------
The one-example organ refuses a change whose new code reads a name the target does not provide.
Its own import machinery declines one case on purpose: when the name came from an import the
example already had (a *standing* import, not a line the example added), and the target already
imports from that same module, the organ says the file declares its own imports and leaves the
line alone. That rule is conservative and defensible, and it is also the exact case people hit:

    example before:  from datetime import UTC, datetime   (unchanged by the change)
    example after:   ... datetime.now(UTC) ...
    target:          from datetime import datetime
                     ... datetime.now() ...

The developers extend the line that is already there: ``from datetime import UTC, datetime``.
This operator does the same, and nothing more:

* the name must be one the lesson says it needs, with an import line the example wrote down;
* the target must already import from that module (so the module resolves there), or the file
  must have a module-level import added only when the import line resolves from the project;
* the name must not already be bound anywhere in the target, and no star import may be present;
* after the edit the text must parse, the name must be bound, and exactly the import line must
  have changed.

It never decides whether the lesson's other parts apply: the organ runs afterwards, with its own
gate, on the brought text. If the organ refuses, nothing is returned.
"""
from __future__ import annotations

import ast
import pathlib

from . import edit_by_example_v1 as organ

SCHEMA = "BRAIN_BRING_NAMES_V1"


class Refused(Exception):
    """The name cannot be brought without guessing."""


def _binds(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)) and node.id == name:
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return True
        if isinstance(node, ast.arg) and node.arg == name:
            return True
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or (alias.name.split(".")[0]
                                         if isinstance(node, ast.Import) else alias.name)
                if bound == name:
                    return True
    return False


def needed(rules) -> dict[str, str]:
    """The names the lesson says it needs, and the import line the example wrote for each."""
    found: dict[str, str] = {}
    for rule in rules:
        for name, line in (getattr(rule, "bring", {}) or {}).items():
            found.setdefault(name, line)
    return found


def _offset(text: str, line: int, column: int) -> int:
    lines = text.splitlines(keepends=True)
    return sum(len(piece) for piece in lines[:line - 1]) + column


def _extend(text: str, statement: ast.ImportFrom, name: str) -> str:
    """Add ``name`` to an existing ``from module import ...`` line, in place.

    The name goes where its spelling sorts, not at the end: the developers' lines are kept in
    order by a formatter, and appending would make every brought line differ from theirs even
    when the edit is right.  ``UTC`` sorts before ``date`` and after ``tzinfo``; the comparison is
    the ASCII one formatters use.
    """
    for alias in statement.names:
        written = alias.name if alias.asname is None else "%s as %s" % (alias.name, alias.asname)
        if written > name:
            at = _offset(text, alias.lineno, alias.col_offset)
            return text[:at] + name + ", " + text[at:]
    last = statement.names[-1]
    at = _offset(text, last.end_lineno, last.end_col_offset)
    return text[:at] + ", " + name + text[at:]


def _insert(text: str, line: str) -> str:
    """Add a new import line after the last top-level import, else after the docstring."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as problem:
        raise Refused("the file is not Python this interpreter can read (%s)" % problem)
    last = None
    for statement in tree.body:
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            last = statement
    if last is None and tree.body and isinstance(tree.body[0], ast.Expr) \
            and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
        last = tree.body[0]
    at = last.end_lineno if last is not None else 0
    lines.insert(at, line + newline)
    return "".join(lines)


def bring(target: str, rules, must_resolve: bool = True) -> tuple[str | None, dict[str, str]]:
    """The target with the needed names imported, or (None, {}) when nothing can be brought.

    ``must_resolve`` is on for a file being edited in its own project: a new import line whose
    module cannot be found there is refused rather than written.
    """
    wanted = needed(rules)
    if not wanted:
        return None, {}
    text = target
    brought: dict[str, str] = {}
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as problem:
        raise Refused("the file is not Python this interpreter can read (%s)" % problem)
    for name, line in sorted(wanted.items()):
        if _binds(ast.parse(text), name):
            continue
        try:
            statement = ast.parse(line).body[0]
        except (SyntaxError, ValueError):
            continue
        if not isinstance(statement, ast.ImportFrom) or not statement.module:
            # `import x` is not the standing-import case this operator was measured on.
            continue
        if statement.level:
            # A relative import resolves against the file's package, not this one.
            continue
        current = ast.parse(text)
        existing = [node for node in current.body
                    if isinstance(node, ast.ImportFrom) and node.level == statement.level
                    and node.module == statement.module]
        if any(any(alias.name == "*" for alias in node.names) for node in existing):
            raise Refused("the file has a star import from `%s`; a name cannot be added to it" % statement.module)
        if existing:
            changed = _extend(text, existing[-1], name)
        else:
            if must_resolve:
                top = organ.import_resolves(line)
                if top is not None:
                    raise Refused("`%s` cannot be found in this project; nothing was changed" % top)
            changed = _insert(text, line)
        try:
            new_tree = ast.parse(changed)
        except (SyntaxError, ValueError) as problem:
            raise Refused("adding `%s` would not parse (%s)" % (line, problem))
        if not _binds(new_tree, name):
            raise Refused("adding `%s` did not make `%s` available" % (line, name))
        # The text is spliced, not regenerated, so only the import line changes.
        text = changed
        brought[name] = line
    if not brought:
        return None, {}
    return text, brought


def rewrite_with_brought_names(rules, target: str, what: str = "the file",
                               leave_unshown: bool = False):
    """Bring the names the lesson needs, then run the organ's own gate on the result."""
    text, brought = bring(target, rules)
    if text is None:
        return organ.rewrite(rules, target, what, leave_unshown=leave_unshown)
    try:
        edited, count = organ.rewrite(rules, text, what, leave_unshown=leave_unshown)
    except organ.Refused:
        return organ.rewrite(rules, target, what, leave_unshown=leave_unshown)
    if not count:
        # The import was brought but no lesson applied: the import alone is not the edit.
        return organ.rewrite(rules, target, what, leave_unshown=leave_unshown)
    return edited, count


def main(argv=None) -> int:
    """A small command line: FILE and the two example files, print the edit or the refusal."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("file")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--leave-unshown", action="store_true")
    args = parser.parse_args(argv)
    read = lambda path: pathlib.Path(path).read_text(encoding="utf-8")
    rules = organ.learn(read(args.before), read(args.after))
    try:
        text, count = rewrite_with_brought_names(rules, read(args.file), leave_unshown=args.leave_unshown)
    except organ.Refused as problem:
        print("REFUSED:", problem)
        return 1
    print(text, end="")
    print("changes:", count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
