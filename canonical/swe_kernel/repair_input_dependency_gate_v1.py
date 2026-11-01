"""Refuse a repair that stops reading an input the original function read.

WHY THIS EXISTS
---------------
Measured 2026-11-01: `solve_repository_closed_loop` "repaired" a two-file coupled billing bug by
replacing the function with

    def compute_invoice(items, disc):
        if disc % 2 == 0:
            return 110.0
        return 85.0

which passes the two visible tests, reports `PASS__CLOSED_LOOP_MULTISTEP_REPO_REPAIRED_AND_VERIFIED`,
and is wrong on every input the tests do not contain (`[100.0], 0.0` returns 110.0; the correct
answer is 100.0). 0/5 runs produced an honest repair.

The existing sabotage control did not catch it, and could not: it checks that the patched code is
*load-bearing* for the tests, which a lookup table is. It does not check that the patched code is
still a function of its inputs.

THE RULE
--------
A patch may not reduce a function's input dependency set. If `compute_invoice` read `items`
before the patch and does not read it after, the patch is refused, regardless of whether the
tests are green.

This is deliberately narrow and syntactic. It does not prove an edit correct; it refuses one
specific failure -- solving the tests by discarding the data. It can reject a legitimate patch
that removes a genuinely unused parameter read, which is why the refusal is a named status with
the offending parameter listed, and why `terminal_authority` is false: a caller may override with
knowledge this module does not have.

WHAT IT IS NOT
--------------
Not a verifier, not a held-out test generator, and not a correctness proof. A patch can lose no
dependencies and still be wrong. It closes exactly one hole and says so.
"""
from __future__ import annotations

import ast
from typing import Any

SCHEMA = "PROJECT_BRAIN_REPAIR_INPUT_DEPENDENCY_GATE_V1"

PASS = "PASS"
REFUSED = "REFUSED"


class GateError(RuntimeError):
    """Raised when the gate cannot decide honestly."""


def _arg_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    names = [a.arg for a in args.posonlyargs]
    names += [a.arg for a in args.args]
    names += [a.arg for a in args.kwonlyargs]
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    return names


def _body_loads(node: ast.AST) -> set[str]:
    """Names loaded in a function's own body, not in functions nested inside it."""
    out: set[str] = set()
    stack: list[ast.AST] = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue  # a nested function has its own parameters
        if isinstance(current, ast.Name) and isinstance(current.ctx, ast.Load):
            out.add(current.id)
        stack.extend(ast.iter_child_nodes(current))
    return out


def parameter_use(source_text: str) -> dict[str, frozenset[str]]:
    """For every function in `source_text`, the parameters its body actually reads."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise GateError("SOURCE_REQUIRED")
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        raise GateError("SOURCE_NOT_PARSEABLE") from exc

    uses: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = set(_arg_names(node))
            loaded = _body_loads(node)
            uses[node.name] = frozenset(params & loaded)
    return uses


def lost_dependencies(before_source: str, after_source: str) -> list[dict[str, str]]:
    """Parameters that a function read before the patch and no longer reads after it."""
    before = parameter_use(before_source)
    after = parameter_use(after_source)
    lost: list[dict[str, str]] = []
    for name, used_before in before.items():
        if name not in after:
            continue  # a deleted function is a different question, decided elsewhere
        for parameter in sorted(used_before - after[name]):
            lost.append({"function": name, "parameter": parameter})
    return lost


def gate(before_source: str, after_source: str) -> dict[str, Any]:
    """Decide whether the patch keeps every input the original function consumed."""
    try:
        lost = lost_dependencies(before_source, after_source)
    except GateError as exc:
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": str(exc),
            "lost": [],
            "terminal_authority": False,
        }
    if lost:
        listed = ", ".join(f"{item['function']}({item['parameter']})" for item in lost)
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": "PATCH_STOPPED_READING_ITS_INPUTS: " + listed,
            "lost": lost,
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": PASS,
        "reason": "INPUT_DEPENDENCIES_PRESERVED",
        "lost": [],
        "terminal_authority": False,
    }
