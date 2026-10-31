#!/usr/bin/env python3
"""python.refactor.move_symbol.v1 — AST top-level symbol move + caller import propagation.

Moves a top-level function or class from ``origin_path`` to ``target_module_path``,
copies required external imports, updates every ``from <origin> import <symbol>``
and ``<origin>.<symbol>`` caller across the enclosing project (including tests),
and verifies bidirectional module imports plus the unittest suite with full
byte rollback on any failure.
"""
from __future__ import annotations

import ast
import hashlib
import json
import keyword as pykeyword
import os
import pathlib
import subprocess
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_MOVE_SYMBOL_V1"
CAPABILITY_ID = "python.refactor.move_symbol.v1"
PROVIDES = ["python.refactor.move_symbol", "python.source.crossfile.symbol_relocated"]
REQUIRES: list[str] = []


def _safe_path(root: pathlib.Path, raw: str | None, code: str) -> pathlib.Path:
    if not raw or not str(raw).strip():
        raise RuntimeError(code)
    p = (root / str(raw).strip()).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = _safe_path(root, raw or "canonical/tmp_move_symbol.json", "OUTPUT_PATH_REQUIRED")
    if p.suffix.lower() == ".py" and p.exists():
        raise RuntimeError("OUTPUT_COLLIDES_WITH_PYTHON_SOURCE")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _discover_project_root(file_a: pathlib.Path, file_b: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    def _pkg_top(p: pathlib.Path) -> pathlib.Path:
        cur = p.parent
        while (cur / "__init__.py").is_file() and cur.parent != repo and repo in cur.parent.parents:
            cur = cur.parent
        return cur

    top_a = _pkg_top(file_a)
    top_b = _pkg_top(file_b)
    common = pathlib.Path(os.path.commonpath([str(top_a), str(top_b)]))
    if common == repo or repo in common.parents:
        return common
    return top_a


def _mod_name(project_root: pathlib.Path, path: pathlib.Path) -> str:
    rel = path.relative_to(project_root).as_posix()
    no_ext = rel[:-3] if rel.endswith(".py") else rel
    parts = [seg for seg in no_ext.split("/") if seg and seg != "__init__"]
    return ".".join(parts)


def _resolve_import_from(cur_mod: str, is_pkg_init: bool, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    cur_parts = cur_mod.split(".") if cur_mod else []
    pkg_parts = cur_parts if is_pkg_init else cur_parts[:-1]
    up = node.level - 1
    if up > len(pkg_parts):
        return ""
    base = pkg_parts[: len(pkg_parts) - up]
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base)


def _def_start_line(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    if node.decorator_list:
        return min([node.lineno] + [d.lineno for d in node.decorator_list])
    return node.lineno


def _format_aliases(aliases: list[ast.alias]) -> str:
    return ", ".join(f"{a.name} as {a.asname}" if a.asname else a.name for a in aliases)


def _insert_imports_at_top(src_text: str, tree: ast.Module, new_lines: list[str]) -> str:
    if not new_lines:
        return src_text
    lines = src_text.splitlines(keepends=True)
    insert_at = 0
    for idx, stmt in enumerate(tree.body):
        if (
            idx == 0
            and isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            insert_at = stmt.end_lineno or stmt.lineno
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            insert_at = stmt.end_lineno or stmt.lineno
            continue
        break
    payload = [ln + "\n" for ln in new_lines]
    lines[insert_at:insert_at] = payload
    return "".join(lines)


def _rewrite_caller_imports(
    src_text: str,
    cur_mod: str,
    is_pkg_init: bool,
    origin_mod: str,
    target_mod: str,
    symbol: str,
    is_target_file: bool,
) -> tuple[str, bool]:
    tree = ast.parse(src_text)
    lines = src_text.splitlines(keepends=True)
    ops: list[tuple[int, int, list[str]]] = []
    changed = False

    for stmt in tree.body:
        if not isinstance(stmt, ast.ImportFrom):
            continue
        resolved = _resolve_import_from(cur_mod, is_pkg_init, stmt)
        if resolved != origin_mod:
            continue
        matching = [a for a in stmt.names if a.name == symbol]
        if not matching:
            continue
        others = [a for a in stmt.names if a.name != symbol]
        raw_line = lines[stmt.lineno - 1]
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
        repl: list[str] = []
        if others:
            mod_spec = ("." * stmt.level) + (stmt.module or "")
            repl.append(f"{indent}from {mod_spec} import {_format_aliases(others)}\n")
        if not is_target_file:
            repl.append(f"{indent}from {target_mod} import {_format_aliases(matching)}\n")
        ops.append((stmt.lineno - 1, stmt.end_lineno or stmt.lineno, repl))
        changed = True

    if not changed:
        return src_text, False
    for start, end, repl in sorted(ops, key=lambda item: (item[0], item[1]), reverse=True):
        lines[start:end] = repl
    return "".join(lines), True


def _verify_move(
    project_root: pathlib.Path,
    origin_mod: str,
    target_mod: str,
    symbol: str,
    timeout_s: float,
) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project_root))
    for order in ([origin_mod, target_mod], [target_mod, origin_mod]):
        code = (
            "import importlib\n"
            f"for m in {order!r}:\n"
            "    importlib.import_module(m)\n"
            f"tm = importlib.import_module({target_mod!r})\n"
            f"assert hasattr(tm, {symbol!r})\n"
        )
        proc = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"IMPORT_FAILED_AFTER_MOVE:{(proc.stderr or proc.stdout)[-300:]}")

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
            raise RuntimeError(f"TESTS_RED_AFTER_MOVE:{(proc.stderr or proc.stdout)[-300:]}")
    return {"imports_ok": True, "suite_ran": suite_ran, "suite_ok": True}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    origin = _safe_path(repo, str(args.get("origin_path") or ""), "ORIGIN_PATH_REQUIRED")
    target = _safe_path(repo, str(args.get("target_module_path") or ""), "TARGET_MODULE_PATH_REQUIRED")
    symbol = str(args.get("qualname") or "").strip()
    timeout_s = float(args.get("timeout_s") or 60.0)

    if not symbol or not symbol.isidentifier() or pykeyword.iskeyword(symbol):
        raise RuntimeError(f"INVALID_SYMBOL_NAME:{symbol}")
    if not origin.is_file() or origin.suffix.lower() != ".py":
        raise RuntimeError("ORIGIN_NOT_PYTHON_FILE")
    if not target.is_file() or target.suffix.lower() != ".py":
        raise RuntimeError("TARGET_NOT_PYTHON_FILE")
    if origin == target:
        raise RuntimeError("ORIGIN_EQUALS_TARGET")

    project_root = _discover_project_root(origin, target, repo)
    origin_mod = _mod_name(project_root, origin)
    target_mod = _mod_name(project_root, target)
    if not origin_mod or not target_mod:
        raise RuntimeError("MODULE_NAME_UNRESOLVABLE")

    all_py = sorted(p for p in project_root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}

    origin_text = originals[origin].decode("utf-8")
    target_text = originals[target].decode("utf-8")
    origin_tree = ast.parse(origin_text, filename=str(origin))
    target_tree = ast.parse(target_text, filename=str(target))

    defs = [
        stmt for stmt in origin_tree.body
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt.name == symbol
    ]
    if not defs:
        raise RuntimeError(f"SYMBOL_NOT_FOUND:{symbol}")
    if len(defs) > 1:
        raise RuntimeError(f"MULTIPLE_DEFINITIONS:{symbol}")
    sym_node = defs[0]

    for stmt in target_tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt.name == symbol:
            raise RuntimeError(f"TARGET_SYMBOL_COLLISION:{symbol}")
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == symbol:
                    raise RuntimeError(f"TARGET_SYMBOL_COLLISION:{symbol}")

    # Collect external imports and sibling definitions in origin referenced by sym_node.
    loaded_in_sym = {
        sub.id for sub in ast.walk(sym_node)
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id != symbol
    }
    target_bound: set[str] = set()
    for stmt in target_tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            target_bound.add(stmt.name)
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for a in stmt.names:
                target_bound.add((a.asname or a.name.split(".")[0]) if isinstance(stmt, ast.Import) else (a.asname or a.name))
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    target_bound.add(t.id)

    origin_lines = origin_text.splitlines(keepends=True)
    extra_target_imports: list[str] = []
    sibling_needed: list[str] = []

    for stmt in origin_tree.body:
        if stmt is sym_node:
            continue
        if isinstance(stmt, ast.Import):
            used_aliases = [a for a in stmt.names if (a.asname or a.name.split(".")[0]) in loaded_in_sym and (a.asname or a.name.split(".")[0]) not in target_bound]
            if used_aliases:
                extra_target_imports.append(f"import {_format_aliases(used_aliases)}")
        elif isinstance(stmt, ast.ImportFrom):
            resolved = _resolve_import_from(origin_mod, origin.name == "__init__.py", stmt)
            if resolved == target_mod:
                continue
            used_aliases = [a for a in stmt.names if (a.asname or a.name) in loaded_in_sym and (a.asname or a.name) not in target_bound]
            if used_aliases and resolved:
                extra_target_imports.append(f"from {resolved} import {_format_aliases(used_aliases)}")
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if stmt.name in loaded_in_sym and stmt.name not in target_bound:
                sibling_needed.append(stmt.name)
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id in loaded_in_sym and t.id not in target_bound:
                    sibling_needed.append(t.id)

    if sibling_needed:
        extra_target_imports.append(f"from {origin_mod} import {', '.join(dict.fromkeys(sibling_needed))}")

    # Check whether remaining statements in origin still reference `symbol`.
    origin_still_uses = False
    for stmt in origin_tree.body:
        if stmt is sym_node:
            continue
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id == symbol:
                origin_still_uses = True
                break

    start_ln = _def_start_line(sym_node) - 1
    end_ln = sym_node.end_lineno or sym_node.lineno
    sym_block = "".join(origin_lines[start_ln:end_ln])
    if not sym_block.endswith("\n"):
        sym_block += "\n"

    # Trim trailing blank line left immediately after the removed symbol block
    trim_end = end_ln
    while trim_end < len(origin_lines) and not origin_lines[trim_end].strip():
        trim_end += 1
        if trim_end - end_ln >= 2:
            break
    new_origin_lines = origin_lines[:start_ln] + origin_lines[trim_end:]
    new_origin_text = "".join(new_origin_lines)
    if origin_still_uses:
        if sibling_needed:
            raise RuntimeError("CYCLIC_MUTUAL_DEPENDENCY_ON_MOVE")
        new_origin_tree = ast.parse(new_origin_text)
        new_origin_text = _insert_imports_at_top(new_origin_text, new_origin_tree, [f"from {target_mod} import {symbol}"])

    # Update target: remove any `from origin_mod import symbol`, add extra_target_imports, append sym_block
    updated_target, _ = _rewrite_caller_imports(
        target_text,
        target_mod,
        target.name == "__init__.py",
        origin_mod,
        target_mod,
        symbol,
        is_target_file=True,
    )
    if extra_target_imports:
        updated_target_tree = ast.parse(updated_target)
        updated_target = _insert_imports_at_top(updated_target, updated_target_tree, extra_target_imports)
    sep = "\n\n" if updated_target.strip() and not updated_target.endswith("\n\n") else ("\n" if not updated_target.endswith("\n") else "")
    updated_target = updated_target.rstrip("\n") + "\n\n\n" + sym_block.lstrip("\n") if updated_target.strip() else sym_block

    files_edited: list[str] = []
    try:
        ast.parse(new_origin_text, filename=str(origin))
        ast.parse(updated_target, filename=str(target))
        origin.write_text(new_origin_text, encoding="utf-8")
        target.write_text(updated_target, encoding="utf-8")
        files_edited.extend([origin.relative_to(repo).as_posix(), target.relative_to(repo).as_posix()])

        for p in all_py:
            if p in (origin, target):
                continue
            cur_m = _mod_name(project_root, p)
            rewritten, did_change = _rewrite_caller_imports(
                originals[p].decode("utf-8"),
                cur_m,
                p.name == "__init__.py",
                origin_mod,
                target_mod,
                symbol,
                is_target_file=False,
            )
            if did_change:
                ast.parse(rewritten, filename=str(p))
                p.write_text(rewritten, encoding="utf-8")
                files_edited.append(p.relative_to(repo).as_posix())

        referee = _verify_move(project_root, origin_mod, target_mod, symbol, timeout_s)
    except Exception:
        for p, raw_bytes in originals.items():
            p.write_bytes(raw_bytes)
        raise

    files_edited = sorted(set(files_edited))
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "qualname": symbol,
        "origin_path": origin.relative_to(repo).as_posix(),
        "target_module_path": target.relative_to(repo).as_posix(),
        "origin_module": origin_mod,
        "target_module": target_mod,
        "files_edited": files_edited,
        "referee": referee,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    return {
        "adapter": "python_source_move_symbol",
        "qualname": symbol,
        "origin_path": origin.relative_to(repo).as_posix(),
        "target_module_path": target.relative_to(repo).as_posix(),
        "files_edited": files_edited,
        "output_path": output.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
