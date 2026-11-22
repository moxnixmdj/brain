"""Opt-in structure-derived edit families for the existing Python repair loop.

This module is deliberately SEPARATE from `python_test_guided_patch_search_v1`.
The older module's source is parsed by `reach_of_the_grammar_v1` to price what
the legacy grammar can express. Adding these families there would silently
rewrite that historical receipt. Here they are a declared extension, priced in
`CONTRACT_VETO_REPAIR_20261121_V1` and off by default in the caller.

Nothing in this file names a program, a bug or an expected patch. It reads only
source structure:

* a name assigned from an expression containing a quotient is an interval
  index, so +/-1 on that name is a candidate (midpoint boundary class);
* adjacent transposition of arguments in a recursive call is a candidate
  (recurrence-order class).
"""
from __future__ import annotations

import ast
from typing import Any, Iterator


def _descriptor(node: ast.AST, kind: str, detail: str, family: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "family": family,
        "ratio": None,
        "detail": detail,
        "lineno": getattr(node, "lineno", None),
        "col_offset": getattr(node, "col_offset", None),
        "end_lineno": getattr(node, "end_lineno", None),
        "end_col_offset": getattr(node, "end_col_offset", None),
    }


def _quotient_names(tree: ast.AST) -> set[str]:
    """Locals assigned from any expression containing a Div or FloorDiv node."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        if not any(isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Div, ast.FloorDiv))
                   for sub in ast.walk(node.value)):
            continue
        targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                out.add(target.id)
    return out


def _locations(tree: ast.AST) -> list[ast.AST]:
    nodes = [node for node in ast.walk(tree) if hasattr(node, "lineno")]
    nodes.sort(key=lambda node: (getattr(node, "lineno", 10**9),
                                 getattr(node, "col_offset", 10**9), type(node).__name__))
    return nodes


def candidate_specs(tree: ast.AST) -> Iterator[tuple[tuple, dict[str, Any], Any]]:
    """Yield the same (key, descriptor, replacer) triples as the legacy grammar."""
    quotient_names = _quotient_names(tree)
    recursive = {getattr(node, "name", None) for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in _locations(tree):
        key = (type(node).__name__, getattr(node, "lineno", None),
               getattr(node, "col_offset", None), getattr(node, "end_lineno", None),
               getattr(node, "end_col_offset", None))
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) \
                and node.id in quotient_names:
            for delta, op in ((1, ast.Add()), (-1, ast.Sub())):
                yield key, _descriptor(node, "INDEX_ADJUST",
                                       f"{node.id}->{node.id}{delta:+d}", "structural_index"), (
                    lambda n, delta=delta, op=op: ast.BinOp(
                        left=n, op=op, right=ast.Constant(value=abs(delta))))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in recursive and len(node.args) >= 2:
            for index in range(len(node.args) - 1):
                yield key, _descriptor(
                    node, "CALL_ARG_SWAP", f"{node.func.id}:args {index}<->{index+1}",
                    "structural_call"), (
                    lambda n, index=index: ast.Call(
                        func=n.func,
                        args=[*n.args[:index], n.args[index + 1], n.args[index],
                              *n.args[index + 2:]],
                        keywords=n.keywords))
