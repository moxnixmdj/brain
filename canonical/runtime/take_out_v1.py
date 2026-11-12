#!/usr/bin/env python3
"""Every program that is this one with one piece taken out. No lesson is needed for it.

Why this exists
---------------
Measured 2026-11-12: the edit-kind learner, shown 2,864 real fixes once each, makes some 30,000
candidate programs for a bug and has the published fix among the first 200 for a third of the
bugs it never saw (EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json). An order counted from further
experience did not bring more fixes to the front (EDIT_KIND_CHOICE_20261112_V1.json).

A bug that consists of something too much (a statement that should not be there, a condition
added to a test, an operand added to a sum) has its fix among the programs that are the buggy one
with one piece less, and those can simply be listed: a few dozen for a short function. Nobody has
to have shown a fix of that shape before. What can be listed need not be learned.

What counts as one piece
------------------------
  a statement             deleted, where its block keeps a statement
  its block               a compound statement (if, for, while, with, try) replaced by the
                          statements under it, or by those under its else
  no else                 the else (or finally) of a compound statement dropped
  one inside              an expression replaced by one of the expressions inside it:
                          `a + b + 1` by `a + b`, `sorted(xs)` by `xs`, `not x` by `x`, `xs[1:]` by `xs`
  one of several          one operand of a longer and/or, one link of a chained comparison, one
                          argument of a call, one element of a list, tuple, set or dict written
                          out, one `if` of a comprehension
  plain assignment        `x *= y` made `x = y`
  no bound                one bound of a slice left out

Definitions and documentation strings are never taken out. The candidates come the smallest
piece first, so that of two that pass the tests the one that keeps more of the program is tried
first. Nothing here accepts a candidate: the caller's tests do.

What was found
--------------
Measured 2026-11-12 (canonical/verification/TAKE_OUT_20261112_V1.json) on the 100 scored
HumanEvalFix bugs, some 40 candidates a bug: 19 repaired, 15 of them right as far as checked, 4
passing the tests without being right. Of the 19 bugs that are something too much, 11 repaired
(10 right) where the learner with 2,864 lessons repairs 8. In front of the learner within the
same 200 candidates: 58 repaired against 55, and 49 right against 48, because twice a piece that
passes weak tests stood before a right repair of the learner's. With the learner first it is 58
and 51, which was worked out afterwards. Five of the seven things expected beforehand did not
hold; the family was shaped on 64 development bugs and did better there (11 of 12).

So: try the pieces AFTER whatever has lessons behind it, and never call a piece that passes right
before it has been checked on inputs the tests do not have.

This is not new. It is what Kali did (Qi, Long, Achour, Rinard, ISSTA 2015), with expressions
added to statements; and Kali is remembered for showing that deleting code makes weak tests pass
without repairing anything. So a caller must check a passing candidate on inputs the tests do not
have before calling it right, and the measurement that goes with this module does
(canonical/tools/take_out_measure_v1.py).
"""
from __future__ import annotations

import ast
import copy
import warnings
from typing import Any, Callable, Iterator

from canonical.runtime import edit_kind_learning_v1 as kinds

SCHEMA = "BRAIN_TAKE_OUT_V1"

STATEMENT, ITS_BLOCK, ITS_ELSE_BLOCK, NO_ELSE = "a statement", "its block", "its else block", "no else"
ONE_INSIDE, ONE_OF_SEVERAL, PLAIN_ASSIGNMENT, NO_BOUND = "one inside", "one of several", "plain assignment", "no bound"
KINDS = (STATEMENT, ITS_BLOCK, ITS_ELSE_BLOCK, NO_ELSE, ONE_INSIDE, ONE_OF_SEVERAL, PLAIN_ASSIGNMENT, NO_BOUND)

_DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_NOT_ON_THEIR_OWN = (ast.Slice, ast.Starred, ast.FormattedValue)      # expressions that only stand inside another


def _is_documentation(node: ast.AST) -> bool:
    """A string standing alone as a statement: taking it out changes nothing that runs."""
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _is_read(node: ast.AST) -> bool:
    """An expression whose value is used, not a name or place that is assigned to or deleted."""
    return isinstance(node, ast.expr) and not isinstance(getattr(node, "ctx", None), (ast.Store, ast.Del))


def _spots(tree: ast.AST) -> list[tuple[ast.AST, ast.AST | None, str | None, int | None]]:
    """Every node with where it hangs: (node, parent, field, index in the field or None). The
    order is the same for a tree and for a copy of it, so a number names the same node in both."""
    out: list[tuple[ast.AST, ast.AST | None, str | None, int | None]] = []

    def go(node: ast.AST, parent: ast.AST | None, field: str | None, index: int | None) -> None:
        out.append((node, parent, field, index))
        for name, value in ast.iter_fields(node):
            if isinstance(value, list):
                for at, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        go(item, node, name, at)
            elif isinstance(value, ast.AST):
                go(value, node, name, None)

    go(tree, None, None, None)
    return out


def size(tree: ast.AST) -> int:
    """How many nodes a program has, not counting the marks that say whether a name is read or written."""
    return sum(1 for node in ast.walk(tree) if not isinstance(node, ast.expr_context))


def _put(spot: tuple[ast.AST, ast.AST | None, str | None, int | None], new: Any) -> None:
    """`new` where the node of this spot hangs; a list of statements takes the place of the one statement."""
    _, parent, field, index = spot
    if index is None:
        setattr(parent, field, new)
    elif isinstance(new, list):
        getattr(parent, field)[index:index + 1] = new
    else:
        getattr(parent, field)[index] = new


def _changes(tree: ast.AST) -> Iterator[tuple[str, Callable[[list], None]]]:
    """(kind, what to do to the spots of a copy of the tree) for every piece that can be taken out."""
    spots = _spots(tree)
    documentation = {id(node) for node, _, _, _ in spots if _is_documentation(node)}
    for number, (node, parent, field, index) in enumerate(spots):
        if parent is None or id(node) in documentation or id(parent) in documentation:
            continue
        if isinstance(node, ast.stmt) and index is not None and not isinstance(node, _DEFINITIONS):
            if len(getattr(parent, field)) > 1:
                yield STATEMENT, lambda copied, number=number: getattr(copied[number][1], copied[number][2]).pop(copied[number][3])
            for inner, kind in (("body", ITS_BLOCK), ("orelse", ITS_ELSE_BLOCK)):
                block = getattr(node, inner, None)
                if isinstance(block, list) and block and all(isinstance(item, ast.stmt) for item in block):
                    yield kind, lambda copied, number=number, inner=inner: _put(copied[number], list(getattr(copied[number][0], inner)))
            for inner in ("orelse", "finalbody"):
                if getattr(node, inner, None):
                    yield NO_ELSE, lambda copied, number=number, inner=inner: setattr(copied[number][0], inner, [])
            if isinstance(node, ast.AugAssign):
                def plain(copied: list, number: int = number) -> None:
                    old = copied[number][0]
                    target = old.target
                    target.ctx = ast.Store()
                    _put(copied[number], ast.Assign(targets=[target], value=old.value, lineno=0, col_offset=0))
                yield PLAIN_ASSIGNMENT, plain
        if _is_read(node):
            for inside, (inner, _, _, _) in enumerate(_spots(node)):
                if inside and _is_read(inner) and not isinstance(inner, _NOT_ON_THEIR_OWN):
                    yield ONE_INSIDE, lambda copied, number=number, inside=inside: _put(copied[number], _spots(copied[number][0])[inside][0])
            several: list[tuple[str, int]] = []
            if isinstance(node, ast.BoolOp) and len(node.values) > 2:
                several = [("values", at) for at in range(len(node.values))]
            elif isinstance(node, ast.Call):
                several = [("args", at) for at in range(len(node.args))] + [("keywords", at) for at in range(len(node.keywords))]
            elif isinstance(node, (ast.List, ast.Tuple, ast.Set)) and len(node.elts) > 1:
                several = [("elts", at) for at in range(len(node.elts))]
            for name, at in several:
                yield ONE_OF_SEVERAL, lambda copied, number=number, name=name, at=at: getattr(copied[number][0], name).pop(at)
            if isinstance(node, ast.Dict) and len(node.keys) > 1:
                for at in range(len(node.keys)):
                    def pair(copied: list, number: int = number, at: int = at) -> None:
                        copied[number][0].keys.pop(at)
                        copied[number][0].values.pop(at)
                    yield ONE_OF_SEVERAL, pair
            if isinstance(node, ast.Compare) and len(node.ops) > 1:
                for at in range(len(node.ops) + 1):
                    def link(copied: list, number: int = number, at: int = at) -> None:
                        compare = copied[number][0]
                        if at == 0:                                   # the first operand goes, with the comparison after it
                            compare.left = compare.comparators.pop(0)
                            compare.ops.pop(0)
                        else:                                         # a later operand goes, with the comparison before it
                            compare.comparators.pop(at - 1)
                            compare.ops.pop(at - 1)
                    yield ONE_OF_SEVERAL, link
        if isinstance(node, ast.comprehension):
            for at in range(len(node.ifs)):
                yield ONE_OF_SEVERAL, lambda copied, number=number, at=at: copied[number][0].ifs.pop(at)
        if isinstance(node, ast.Slice):
            for bound in ("lower", "upper", "step"):
                if getattr(node, bound) is not None:
                    yield NO_BOUND, lambda copied, number=number, bound=bound: setattr(copied[number][0], bound, None)


def candidates(source: str) -> list[tuple[str, int, str]]:
    """Every program that is `source` with one piece taken out: (text, how many nodes fewer, what
    kind of piece), the smallest piece first and otherwise in the order of the program. Only
    programs that compile, each once, and never the program itself. Nothing when the program cannot be read."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return []
    original = ast.unparse(tree)
    whole = size(tree)
    seen = {original}
    out: list[tuple[str, int, str]] = []
    for kind, change in _changes(tree):
        copied = copy.deepcopy(tree)
        try:
            change(_spots(copied))
            text = ast.unparse(ast.fix_missing_locations(copied))
        except Exception:                                           # a tree that cannot be written out is no candidate
            continue
        if text in seen or not kinds.is_a_program(text):
            continue
        seen.add(text)
        out.append((text, whole - size(ast.parse(text)), kind))
    out.sort(key=lambda item: item[1])                              # stable: equal pieces stay in the order of the program
    return out


def in_order(source: str) -> list[tuple[str, float, dict[str, Any]]]:
    """The candidates as (text, score, {"kind": ..., "nodes_fewer": ...}), the shape the benches here take."""
    return [(text, -float(fewer), {"kind": kind, "nodes_fewer": fewer}) for text, fewer, kind in candidates(source)]
