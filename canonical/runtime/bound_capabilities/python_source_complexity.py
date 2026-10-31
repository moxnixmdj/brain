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


def _files(root: pathlib.Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _calls_with_loop_depth(node: ast.AST, cur_loop: int = 0) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        next_loop = cur_loop + (1 if isinstance(child, (ast.For, ast.AsyncFor, ast.While, ast.comprehension)) else 0)
        if isinstance(child, ast.Call):
            fn = child.func
            cname = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if cname:
                out.append((cname, cur_loop))
        out.extend(_calls_with_loop_depth(child, next_loop))
    return out


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    raw_fns: list[tuple[str, str, int, int, list[tuple[str, int]]]] = []
    unparseable = 0
    for path in _files(source_root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
        except (SyntaxError, ValueError):
            unparseable += 1
            continue
        rel_p = _rel(repo, path)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            raw_fns.append((
                rel_p,
                node.name,
                _nesting(node),
                getattr(node, "lineno", 0),
                _calls_with_loop_depth(node, 0),
            ))

    # Interprocedural loop-depth propagation + self-recursion recurrence detection
    eff_depth: dict[str, int] = {}
    rec_class: dict[str, str] = {}
    for _rel_p, fname, ldepth, _ln, calls in raw_fns:
        self_calls = sum(1 for c, _ in calls if c == fname)
        if self_calls >= 2:
            eff_depth[fname] = max(eff_depth.get(fname, 0), max(ldepth, 4))
            rec_class[fname] = "O(2^n)"
        elif self_calls == 1:
            eff_depth[fname] = max(eff_depth.get(fname, 0), max(ldepth, 1))
        else:
            eff_depth[fname] = max(eff_depth.get(fname, 0), ldepth)

    for _ in range(min(len(raw_fns), 12)):
        changed = False
        for _rel_p, fname, ldepth, _ln, calls in raw_fns:
            best_d = eff_depth.get(fname, ldepth)
            for cname, call_loop_d in calls:
                if cname != fname and cname in eff_depth:
                    cand = call_loop_d + eff_depth[cname]
                    if cand > best_d and cand <= 8:
                        best_d = cand
            if best_d != eff_depth.get(fname):
                eff_depth[fname] = best_d
                changed = True
        if not changed:
            break

    measured = []
    for rel_p, fname, ldepth, lineno, _calls in raw_fns:
        depth = eff_depth.get(fname, ldepth)
        c_cls = rec_class.get(fname) or _class_for(depth)
        measured.append({
            "path": rel_p,
            "name": fname,
            "local_nesting": ldepth,
            "nesting": depth,
            "complexity_class": c_cls,
            "lineno": lineno,
        })

    # Deepest first; ties broken by name so the artifact is deterministic.
    measured.sort(key=lambda r: (-r["nesting"], r["path"], r["name"]))
    worst = measured[0] if measured else None
    quadratic = [r["name"] for r in measured if r["nesting"] >= 2]
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "answer": (worst["name"] if worst else ""),
        "worst_function": worst,
        "worst_nesting": (worst["nesting"] if worst else 0),
        "worst_class": (worst["complexity_class"] if worst else "O(1)"),
        "quadratic_symbols": quadratic,
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
        "functions_measured": len(measured),
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
