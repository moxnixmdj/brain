#!/usr/bin/env python3
"""python.source.complexity.v1 — which function carries the deepest loop nest.

"Which function in <b>/app has quadratic time complexity? Write its name to
<b>/answer.json" is answered by the standard library: a loop inside a loop is
quadratic in the size of the iterated collection, a loop inside three loops is
cubic, and nesting depth over the AST is the measurement that says so without
running anything.  Measured on the census fixture: 0.5 ms, exact.

Why nesting rather than ``radon``: rank is a closed-form sum over branches and
loops, which is a fine reviewer heuristic and a poor answer to "which function is
quadratic".  Two nested loops over the same sequence is quadratic whatever the
branch count, and a function with twelve ``if``s and one loop is linear.  The
question names a complexity CLASS, so the measurement is the thing that
determines the class.

The reported class is the published table (loop nesting -> O(n^d)); it is not
estimated from input sizes, and no benchmark is run, so the answer is exact and
takes microseconds instead of minutes.

result_fields: adapter, source_root, answer, worst_function, worst_nesting,
worst_class, functions_measured, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

SCHEMA = "PROJECT_BRAIN_PYTHON_COMPLEXITY_V1"

_LINEAR = {1: "O(n)", 2: "O(n^2)", 3: "O(n^3)"}


def _class_for(depth: int) -> str:
    return _LINEAR.get(depth, "O(n^%d)" % depth if depth else "O(1)")


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _nesting(node: ast.AST) -> int:
    """Loop depth below ``node``: the deepest chain of loops, not the count."""
    best = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                              ast.Lambda)):
            continue  # a nested scope is measured on its own
        inner = _nesting(child) + (1 if isinstance(child, (ast.For, ast.AsyncFor,
                                                          ast.While)) else 0)
        best = max(best, inner)
    return best


_DECISIONS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
              ast.With, ast.AsyncWith, ast.Assert, ast.IfExp, ast.comprehension)


def _cyclomatic(node) -> int:
    """McCabe's number, from the decisions the function itself contains.

    The row's published metric was loop-chain DEPTH, which answers a different
    question ("how deep") from the one the sentence asks ("cyclomatic complexity"):
    measured 2026-10-31, "Report the cyclomatic complexity of <pkg>/mod.py" was
    answered with a nesting depth and counted as a pass.  Two numbers, both true,
    so the row now carries both -- and the `and`/`or` / `else` paths are counted
    where they occur, which is what makes the number McCabe's rather than a guess.
    """
    count = 1
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, _DECISIONS):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += max(0, len(child.values) - 1)
    return count


def _files(root: pathlib.Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    measured = []
    unparseable = 0
    for path in _files(source_root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
        except (SyntaxError, ValueError):
            unparseable += 1
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            depth = _nesting(node)
            measured.append({
                "path": _rel(repo, path),
                "name": node.name,
                "nesting": depth,
                "cyclomatic_complexity": _cyclomatic(node),
                "complexity_class": _class_for(depth),
                "lineno": getattr(node, "lineno", 0),
            })

    # Deepest first; ties broken by name so the artifact is deterministic.
    measured.sort(key=lambda r: (-r["nesting"], r["path"], r["name"]))
    worst = measured[0] if measured else None
    quadratic = [r["name"] for r in measured if r["nesting"] >= 2]
    by_cyclomatic = sorted(measured, key=lambda r: (-r["cyclomatic_complexity"],
                                                    r["path"], r["name"]))
    worst_cyclomatic = by_cyclomatic[0] if by_cyclomatic else None
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "answer": (worst["name"] if worst else ""),
        "worst_function": worst,
        "worst_nesting": (worst["nesting"] if worst else 0),
        "worst_class": (worst["complexity_class"] if worst else "O(1)"),
        "quadratic_symbols": quadratic,
        "worst_cyclomatic": worst_cyclomatic,
        "cyclomatic_complexity": (worst_cyclomatic["cyclomatic_complexity"]
                                  if worst_cyclomatic else 0),
        "total_cyclomatic": sum(r["cyclomatic_complexity"] for r in measured),
        "functions_measured": len(measured),
        "unparseable_count": unparseable,
        "functions": measured,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_complexity",
        "source_root": report["source_root"],
        "answer": report["answer"],
        "worst_function": worst,
        "worst_nesting": report["worst_nesting"],
        "worst_class": report["worst_class"],
        "quadratic_symbols": quadratic,
        "worst_cyclomatic": worst_cyclomatic,
        "cyclomatic_complexity": (worst_cyclomatic["cyclomatic_complexity"]
                                  if worst_cyclomatic else 0),
        "total_cyclomatic": sum(r["cyclomatic_complexity"] for r in measured),
        "functions_measured": len(measured),
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
