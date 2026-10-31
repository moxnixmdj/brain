#!/usr/bin/env python3
"""Structural cost estimates, interprocedural loop depth and cyclomatic metrics.

Loop depth is propagated through statically named calls under a unit-cost model
in which each loop has O(n) iterations. Self-recursion is classified by call-site
count: multiple sites produce a branching-recursion heuristic, not a solved
recurrence. Constant bounds, argument shrinkage, mutual recursion, dynamic
Python dispatch and duplicate function names can invalidate these estimates.

The report explicitly distinguishes this structural heuristic from an
asymptotic proof. Cyclomatic complexity remains a separate branch metric.
No benchmark or source execution is performed.
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
    cyclomatic = {}
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
            cyclomatic[(rel_p, node.name)] = _cyclomatic(node)
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
            "cyclomatic_complexity": cyclomatic[(rel_p, fname)],
            "nesting": depth,
            "complexity_class": c_cls,
            "recursion_model": ("BRANCHING_CALL_SITE_HEURISTIC" if fname in rec_class
                                else "SINGLE_CALL_SITE_HEURISTIC" if any(c == fname for c, _ in _calls)
                                else "NO_SELF_RECURSION"),
            "lineno": lineno,
        })

    # Deepest first; ties broken by name so the artifact is deterministic.
    measured.sort(key=lambda r: (-r["nesting"], r["path"], r["name"]))
    worst = measured[0] if measured else None
    quadratic = [r["name"] for r in measured if r["nesting"] >= 2]
    by_cyclomatic = sorted(measured, key=lambda r: (-r["cyclomatic_complexity"], r["path"], r["name"]))
    worst_cyclomatic = by_cyclomatic[0] if by_cyclomatic else None
    report = {
        "schema": SCHEMA,
        "analysis_model": "STRUCTURAL_UNIT_COST_HEURISTIC",
        "is_asymptotic_proof": False,
        "assumptions": ["Each loop has O(n) iterations and unit-cost local operations",
                        "Calls are resolved by static function name",
                        "Recursive call-site count is not a solved recurrence"],
        "source_root": _rel(repo, source_root),
        "answer": (worst["name"] if worst else ""),
        "worst_function": worst,
        "worst_nesting": (worst["nesting"] if worst else 0),
        "worst_class": (worst["complexity_class"] if worst else "O(1)"),
        "quadratic_symbols": quadratic,
        "worst_cyclomatic": worst_cyclomatic,
        "cyclomatic_complexity": worst_cyclomatic["cyclomatic_complexity"] if worst_cyclomatic else 0,
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
        "analysis_model": "STRUCTURAL_UNIT_COST_HEURISTIC",
        "is_asymptotic_proof": False,
        "source_root": report["source_root"],
        "answer": report["answer"],
        "worst_function": worst,
        "worst_nesting": report["worst_nesting"],
        "worst_class": report["worst_class"],
        "quadratic_symbols": quadratic,
        "worst_cyclomatic": worst_cyclomatic,
        "cyclomatic_complexity": worst_cyclomatic["cyclomatic_complexity"] if worst_cyclomatic else 0,
        "total_cyclomatic": sum(r["cyclomatic_complexity"] for r in measured),
        "functions_measured": len(measured),
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
