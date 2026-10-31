#!/usr/bin/env python3
"""python.refactor.remove_dead_code.v1 — whole-project AST dead-function & unused-import remover.

Iteratively removes top-level functions in ``source_root`` that have zero external
references across the enclosing project (including ``tests/``) while respecting
``__all__``, ``__init__.py`` re-exports, dunder protocols, and decorators, then
prunes unused module-level imports in the updated modules and proves the result
via fresh imports plus the project's unittest suite with full byte rollback.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_REMOVE_DEAD_CODE_V1"
CAPABILITY_ID = "python.refactor.remove_dead_code.v1"
PROVIDES = ["python.refactor.dead_code.removed", "python.refactor.unused_imports.removed"]
REQUIRES: list[str] = []


def _safe_path(root: pathlib.Path, raw: str | None, code: str) -> pathlib.Path:
    if not raw or not str(raw).strip():
        raise RuntimeError(code)
    p = (root / str(raw).strip()).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = _safe_path(root, raw or "canonical/tmp_remove_dead_code.json", "OUTPUT_PATH_REQUIRED")
    if p.suffix.lower() == ".py" and p.exists():
        raise RuntimeError("OUTPUT_COLLIDES_WITH_PYTHON_SOURCE")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _discover_project_root(src_dir: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    if src_dir.parent != repo and repo in src_dir.parent.parents:
        if (src_dir / "__init__.py").is_file() or (src_dir.parent / "tests").is_dir():
            return src_dir.parent
    return src_dir


def _is_test_file(path: pathlib.Path, src_dir: pathlib.Path) -> bool:
    rel = path.relative_to(src_dir)
    if "tests" in rel.parts or "__pycache__" in rel.parts or ".git" in rel.parts:
        return True
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _dunder_all_names(tree: ast.Module) -> set[str]:
    exported: set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets):
                for elt in ast.walk(stmt.value):
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        exported.add(elt.value)
    return exported


def _collect_external_refs(
    trees: dict[pathlib.Path, ast.Module],
    cand_path: pathlib.Path,
    cand_fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    name = cand_fn.name
    for path, tree in trees.items():
        if name in _dunder_all_names(tree):
            return True
        if path != cand_path:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == name:
                    return True
                if isinstance(node, ast.Attribute) and node.attr == name:
                    return True
                if isinstance(node, ast.ImportFrom):
                    for a in node.names:
                        if a.name == name:
                            return True
        else:
            for top in tree.body:
                if top is cand_fn:
                    continue
                for node in ast.walk(top):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == name:
                        return True
                    if isinstance(node, ast.Attribute) and node.attr == name:
                        return True
    return False


def _def_start_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    if node.decorator_list:
        return min([node.lineno] + [d.lineno for d in node.decorator_list])
    return node.lineno


def _remove_defs_from_text(src_text: str, dead_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> str:
    lines = src_text.splitlines(keepends=True)
    for fn in sorted(dead_nodes, key=lambda n: n.lineno, reverse=True):
        start = _def_start_line(fn) - 1
        end = fn.end_lineno or fn.lineno
        while end < len(lines) and not lines[end].strip():
            end += 1
            if end - (fn.end_lineno or fn.lineno) >= 2:
                break
        lines[start:end] = []
    return "".join(lines)


def _prune_unused_imports(src_text: str) -> tuple[str, list[str]]:
    tree = ast.parse(src_text)
    exported = _dunder_all_names(tree)

    # Collect every identifier loaded/deleted anywhere outside top-level import statements.
    used_names: set[str] = set(exported)
    top_imports = {stmt for stmt in tree.body if isinstance(stmt, (ast.Import, ast.ImportFrom))}
    for stmt in tree.body:
        if stmt in top_imports:
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Load, ast.Del)):
                used_names.add(node.id)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Preserve imports referenced inside stringified type annotations if identifier-shaped
                if node.value in used_names:
                    continue

    # Also check string annotations on function signatures/AnnAssign so PEP 563 annotations keep their types.
    for node in ast.walk(tree):
        ann_nodes: list[ast.AST] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                ann_nodes.append(node.returns)
            for a in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                if a.annotation is not None:
                    ann_nodes.append(a.annotation)
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            ann_nodes.append(node.annotation)
        for ann in ann_nodes:
            if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
                try:
                    ann_tree = ast.parse(ann.value, mode="eval")
                    for sub in ast.walk(ann_tree):
                        if isinstance(sub, ast.Name):
                            used_names.add(sub.id)
                except SyntaxError:
                    pass

    lines = src_text.splitlines(keepends=True)
    ops: list[tuple[int, int, list[str]]] = []
    removed_imports: list[str] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            kept: list[ast.alias] = []
            for a in stmt.names:
                local = a.asname or a.name.split(".")[0]
                if local in used_names:
                    kept.append(a)
                else:
                    removed_imports.append(a.name)
            if len(kept) == len(stmt.names):
                continue
            raw_line = lines[stmt.lineno - 1]
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
            if not kept:
                ops.append((stmt.lineno - 1, stmt.end_lineno or stmt.lineno, []))
            else:
                spec = ", ".join(f"{a.name} as {a.asname}" if a.asname else a.name for a in kept)
                ops.append((stmt.lineno - 1, stmt.end_lineno or stmt.lineno, [f"{indent}import {spec}\n"]))
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.module == "__future__" or any(a.name == "*" for a in stmt.names):
                continue
            kept = []
            for a in stmt.names:
                local = a.asname or a.name
                if local in used_names:
                    kept.append(a)
                else:
                    removed_imports.append(f"{stmt.module or ''}.{a.name}".strip("."))
            if len(kept) == len(stmt.names):
                continue
            raw_line = lines[stmt.lineno - 1]
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
            if not kept:
                ops.append((stmt.lineno - 1, stmt.end_lineno or stmt.lineno, []))
            else:
                mod_spec = ("." * stmt.level) + (stmt.module or "")
                spec = ", ".join(f"{a.name} as {a.asname}" if a.asname else a.name for a in kept)
                ops.append((stmt.lineno - 1, stmt.end_lineno or stmt.lineno, [f"{indent}from {mod_spec} import {spec}\n"]))

    if not ops:
        return src_text, []
    for start, end, repl in sorted(ops, key=lambda item: (item[0], item[1]), reverse=True):
        lines[start:end] = repl
    return "".join(lines), removed_imports


def _verify_project(project_root: pathlib.Path, target_files: list[pathlib.Path], timeout_s: float) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project_root))
    mods: list[str] = []
    for p in target_files:
        rel = p.relative_to(project_root).as_posix()
        no_ext = rel[:-3] if rel.endswith(".py") else rel
        m = ".".join(seg for seg in no_ext.split("/") if seg and seg != "__init__")
        if m:
            mods.append(m)
    if mods:
        code = "import importlib\nfor m in " + repr(sorted(set(mods))) + ":\n    importlib.import_module(m)\n"
        proc = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"IMPORT_FAILED_AFTER_DEAD_CODE_REMOVAL:{(proc.stderr or proc.stdout)[-300:]}")

    tests_dir = project_root / "tests"
    has_tests = (tests_dir.is_dir() and any(tests_dir.rglob("test*.py"))) or any(
        p.is_file() and (p.name.startswith("test_") or p.name.endswith("_test.py"))
        for p in project_root.rglob("*.py")
    )
    suite_ran = False
    if has_tests:
        suite_ran = True
        start_dir = "tests" if tests_dir.is_dir() else "."
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", start_dir, "-t", "."],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"TESTS_RED_AFTER_DEAD_CODE_REMOVAL:{(proc.stderr or proc.stdout)[-300:]}")
    return {"imports_ok": True, "suite_ran": suite_ran, "suite_ok": True}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    src_arg = _safe_path(repo, str(args.get("source_root") or ""), "SOURCE_ROOT_REQUIRED")
    timeout_s = float(args.get("timeout_s") or 60.0)
    mod_opt = args.get("module")

    if src_arg.is_file():
        src_dir = src_arg.parent
        target_files = [src_arg]
    elif src_arg.is_dir():
        src_dir = src_arg
        if mod_opt:
            target = _safe_path(src_dir, str(mod_opt), "MODULE_INVALID")
            if not target.is_file():
                raise RuntimeError(f"MODULE_NOT_FOUND:{mod_opt}")
            target_files = [target]
        else:
            target_files = sorted(
                p for p in src_dir.rglob("*.py")
                if p.is_file() and p.name != "__init__.py" and not _is_test_file(p, src_dir)
            )
    else:
        raise RuntimeError("SOURCE_ROOT_MISSING")

    project_root = _discover_project_root(src_dir, repo)
    all_py = sorted(p for p in project_root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}
    working_texts = {p: originals[p].decode("utf-8") for p in all_py}

    removed_functions: list[dict[str, Any]] = []
    # Phase 1: iteratively prune unreferenced top-level functions across target_files.
    while True:
        trees = {p: ast.parse(txt, filename=str(p)) for p, txt in working_texts.items()}
        round_dead: dict[pathlib.Path, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        for path in target_files:
            tree = trees[path]
            exported = _dunder_all_names(tree)
            for stmt in tree.body:
                if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if stmt.decorator_list or (stmt.name.startswith("__") and stmt.name.endswith("__")):
                    continue
                if stmt.name in exported or stmt.name == "main":
                    continue
                if not _collect_external_refs(trees, path, stmt):
                    round_dead.setdefault(path, []).append(stmt)
                    removed_functions.append({"file": path.relative_to(repo).as_posix(), "name": stmt.name})
        if not round_dead:
            break
        for path, dead_nodes in round_dead.items():
            working_texts[path] = _remove_defs_from_text(working_texts[path], dead_nodes)

    # Phase 2: prune unused module-level imports in target_files (including imports newly orphaned by Phase 1).
    removed_imports: list[dict[str, Any]] = []
    for path in target_files:
        pruned, imp_names = _prune_unused_imports(working_texts[path])
        if imp_names:
            working_texts[path] = pruned
            for nm in imp_names:
                removed_imports.append({"file": path.relative_to(repo).as_posix(), "import": nm})

    changed_paths = [p for p in target_files if working_texts[p].encode("utf-8") != originals[p]]
    if not changed_paths:
        raise RuntimeError("NO_DEAD_CODE_OR_UNUSED_IMPORTS_FOUND")

    files_edited: list[str] = []
    try:
        for path in changed_paths:
            ast.parse(working_texts[path], filename=str(path))
            path.write_text(working_texts[path], encoding="utf-8")
            files_edited.append(path.relative_to(repo).as_posix())
        referee = _verify_project(project_root, target_files, timeout_s)
    except Exception:
        for p, raw_bytes in originals.items():
            p.write_bytes(raw_bytes)
        raise

    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "files_edited": files_edited,
        "removed_functions": removed_functions,
        "removed_imports": removed_imports,
        "referee": referee,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    return {
        "adapter": "python_source_remove_dead_code",
        "files_edited": files_edited,
        "removed_functions": removed_functions,
        "removed_imports": removed_imports,
        "output_path": output.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
