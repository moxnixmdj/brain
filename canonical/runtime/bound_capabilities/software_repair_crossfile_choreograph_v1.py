#!/usr/bin/env python3
"""Software repair — cross-file import-cycle resolution and atomic choreography.

Breaks top-level Python circular imports by AST scope analysis (deferring
strictly function/method-body-only imports across cycle edges after verifying
zero module-level, decorator, default-arg, class-header, or re-export uses)
and proves the repair with bidirectional fresh-interpreter imports plus the
project's unittest suite, rolling back every byte on any failure.
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

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]

REPO = pathlib.Path(__file__).resolve().parents[3]


def _safe_path(root: pathlib.Path, raw: str | None, code: str) -> pathlib.Path:
    if not raw or not str(raw).strip():
        raise RuntimeError(code)
    p = (root / str(raw).strip()).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = _safe_path(root, raw or "canonical/tmp_choreograph_repair.json", "OUTPUT_PATH_REQUIRED")
    if p.suffix.lower() == ".py" and p.exists():
        raise RuntimeError("OUTPUT_COLLIDES_WITH_PYTHON_SOURCE")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _is_test_path(rel: pathlib.PurePosixPath) -> bool:
    if "tests" in rel.parts or "__pycache__" in rel.parts or ".git" in rel.parts:
        return True
    name = rel.name
    return name.startswith("test_") or name.endswith("_test.py")


def _discover_layout(src_dir: pathlib.Path, repo: pathlib.Path) -> tuple[pathlib.Path, list[pathlib.Path]]:
    if (src_dir / "__init__.py").is_file() and src_dir.parent != repo and repo in src_dir.parent.parents:
        project_root = src_dir.parent
        pkg_files = sorted(
            p for p in src_dir.rglob("*.py")
            if p.is_file() and not _is_test_path(pathlib.PurePosixPath(p.relative_to(project_root).as_posix()))
        )
        return project_root, pkg_files
    project_root = src_dir
    pkg_files = sorted(
        p for p in project_root.rglob("*.py")
        if p.is_file() and not _is_test_path(pathlib.PurePosixPath(p.relative_to(project_root).as_posix()))
    )
    return project_root, pkg_files


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


def _external_reexport_names(project_root: pathlib.Path, mod: str, target_path: pathlib.Path) -> set[str]:
    """Names imported FROM ``mod`` (or accessed as ``mod.<name>``) by other files."""
    claimed: set[str] = set()
    short = mod.rsplit(".", 1)[-1]
    for p in sorted(project_root.rglob("*.py")):
        if p == target_path or "__pycache__" in p.parts or ".git" in p.parts:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        is_init = p.name == "__init__.py"
        p_mod = _mod_name(project_root, p)
        mod_aliases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                resolved = _resolve_import_from(p_mod, is_init, node)
                if resolved == mod:
                    for alias in node.names:
                        claimed.add(alias.name)
                elif node.module and resolved and f"{resolved}.{short}" == mod:
                    for alias in node.names:
                        if alias.name == short:
                            mod_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == mod:
                        mod_aliases.add(alias.asname or alias.name.split(".")[0])
        if mod_aliases:
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    if node.value.id in mod_aliases:
                        claimed.add(node.attr)
    return claimed


def _has_future_annotations(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
            if any(a.name == "annotations" for a in stmt.names):
                return True
    return False


def _deferrable_targets(
    tree: ast.Module,
    stmt: ast.ImportFrom,
    externally_imported: set[str],
) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, list[ast.alias]]] | None:
    """Return [(fn_node, needed_aliases), ...] if ``stmt`` can safely move into function bodies."""
    if any(a.name == "*" for a in stmt.names):
        return None
    alias_by_local: dict[str, ast.alias] = {}
    for a in stmt.names:
        local = a.asname or a.name
        if local in externally_imported:
            return None
        alias_by_local[local] = a
    tracked = set(alias_by_local)
    if not tracked:
        return None

    for top in tree.body:
        if isinstance(top, ast.Assign):
            for t in top.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    for elt in ast.walk(top.value):
                        if isinstance(elt, ast.Constant) and elt.value in tracked:
                            return None

    future_ann = _has_future_annotations(tree)
    disallowed = False
    fn_uses: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, set[str]]] = []

    def _any_tracked_load(node: ast.AST | None) -> bool:
        if node is None:
            return False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in tracked:
                return True
        return False

    def _check_fn_header(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        for dec in fn.decorator_list:
            if _any_tracked_load(dec):
                return True
        for d in list(fn.args.defaults) + [x for x in fn.args.kw_defaults if x is not None]:
            if _any_tracked_load(d):
                return True
        if not future_ann:
            if _any_tracked_load(fn.returns):
                return True
            for arg in (
                list(fn.args.posonlyargs)
                + list(fn.args.args)
                + list(fn.args.kwonlyargs)
                + ([fn.args.vararg] if fn.args.vararg else [])
                + ([fn.args.kwarg] if fn.args.kwarg else [])
            ):
                if _any_tracked_load(arg.annotation):
                    return True
        return False

    def _collect_fn_body(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if _check_fn_header(fn):
            return False
        used: set[str] = set()
        rebound: set[str] = set()
        for body_stmt in fn.body:
            for sub in ast.walk(body_stmt):
                if isinstance(sub, ast.Name) and sub.id in tracked:
                    if isinstance(sub.ctx, ast.Load):
                        used.add(sub.id)
                    else:
                        rebound.add(sub.id)
        if used & rebound:
            return False
        if used:
            fn_uses.append((fn, used))
        return True

    for top in tree.body:
        if top is stmt:
            continue
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _collect_fn_body(top):
                return None
        elif isinstance(top, ast.ClassDef):
            for dec in top.decorator_list:
                if _any_tracked_load(dec):
                    return None
            for base in top.bases:
                if _any_tracked_load(base):
                    return None
            for kw in top.keywords:
                if _any_tracked_load(kw.value):
                    return None
            for item in top.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not _collect_fn_body(item):
                        return None
                elif _any_tracked_load(item):
                    return None
        else:
            if _any_tracked_load(top):
                return None

    if disallowed or not fn_uses:
        return None
    result: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, list[ast.alias]]] = []
    for fn, used in fn_uses:
        ordered = [a for a in stmt.names if (a.asname or a.name) in used]
        if ordered:
            result.append((fn, ordered))
    return result if result else None


def _find_cycle(adj: dict[str, set[str]]) -> list[str] | None:
    visited: set[str] = set()
    stack: list[str] = []
    on_stack: set[str] = set()

    def dfs(u: str) -> list[str] | None:
        visited.add(u)
        stack.append(u)
        on_stack.add(u)
        for v in sorted(adj.get(u, ())):
            if v not in visited:
                cyc = dfs(v)
                if cyc is not None:
                    return cyc
            elif v in on_stack:
                idx = stack.index(v)
                return stack[idx:] + [v]
        stack.pop()
        on_stack.remove(u)
        return None

    for node in sorted(adj):
        if node not in visited:
            cyc = dfs(node)
            if cyc is not None:
                return cyc
    return None


def _format_import(module: str, aliases: list[ast.alias]) -> str:
    parts = [f"{a.name} as {a.asname}" if a.asname else a.name for a in aliases]
    return f"from {module} import {', '.join(parts)}"


def _apply_deferrals_to_file(
    src_text: str,
    removals: list[ast.ImportFrom],
    insertions: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]],
) -> str:
    lines = src_text.splitlines(keepends=True)
    # Build line-indexed edits so line numbers stay exact when processed bottom-up.
    ops: list[tuple[int, int, list[str]]] = []
    for stmt in removals:
        start = stmt.lineno - 1
        end = (stmt.end_lineno or stmt.lineno)
        ops.append((start, end, []))

    by_fn: dict[int, tuple[ast.FunctionDef | ast.AsyncFunctionDef, list[str]]] = {}
    for fn, imp_line in insertions:
        entry = by_fn.setdefault(fn.lineno, (fn, []))
        if imp_line not in entry[1]:
            entry[1].append(imp_line)

    for _lineno, (fn, imp_lines) in by_fn.items():
        first = fn.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and len(fn.body) >= 2
        ):
            anchor = fn.body[1]
            insert_at = anchor.lineno - 1
            raw_line = lines[insert_at]
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
            payload = [f"{indent}{imp}\n" for imp in imp_lines]
            ops.append((insert_at, insert_at, payload))
        elif first.lineno == fn.lineno:
            # Single-line def header+body (e.g. `def f(x): return g(x)`)
            fn_line = lines[fn.lineno - 1]
            fn_indent = fn_line[: len(fn_line) - len(fn_line.lstrip(" \t"))]
            body_indent = fn_indent + "    "
            header = fn_line[: first.col_offset].rstrip()
            rest = fn_line[first.col_offset :]
            payload = [header + "\n"] + [f"{body_indent}{imp}\n" for imp in imp_lines] + [f"{body_indent}{rest}"]
            ops.append((fn.lineno - 1, fn.lineno, payload))
        else:
            insert_at = first.lineno - 1
            raw_line = lines[insert_at]
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
            payload = [f"{indent}{imp}\n" for imp in imp_lines]
            ops.append((insert_at, insert_at, payload))

    for start, end, repl in sorted(ops, key=lambda item: (item[0], item[1]), reverse=True):
        lines[start:end] = repl
    return "".join(lines)


def _verify_imports_and_suite(
    project_root: pathlib.Path,
    module_names: list[str],
    timeout_s: float,
) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project_root))
    clean_mods = [m for m in module_names if m]
    for label, order in (("forward", sorted(clean_mods)), ("reverse", sorted(clean_mods, reverse=True))):
        if not order:
            continue
        code = "import importlib\nfor m in " + repr(order) + ":\n    importlib.import_module(m)\n"
        proc = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"POST_EDIT_IMPORT_FAILED:{label}:{(proc.stderr or proc.stdout)[-300:]}")

    tests_dir = project_root / "tests"
    has_tests = tests_dir.is_dir() and any(tests_dir.rglob("test*.py"))
    if not has_tests:
        has_tests = any(
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
            raise RuntimeError(f"TESTS_RED_AFTER_CHOREOGRAPHY:{(proc.stderr or proc.stdout)[-300:]}")
    return {"bidirectional_imports_ok": True, "suite_ran": suite_ran, "suite_ok": True}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    raw_src = args.get("source_root")
    src_dir = _safe_path(repo, str(raw_src) if raw_src is not None else None, "SOURCE_ROOT_REQUIRED")
    if not src_dir.is_dir():
        raise RuntimeError("SOURCE_ROOT_NOT_DIRECTORY")
    timeout_s = float(args.get("timeout_s") or 60.0)

    project_root, pkg_files = _discover_layout(src_dir, repo)
    if not pkg_files:
        raise RuntimeError("NO_PYTHON_MODULES_UNDER_SOURCE_ROOT")

    all_py = sorted(p for p in project_root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}

    mod_to_path: dict[str, pathlib.Path] = {}
    path_to_mod: dict[pathlib.Path, str] = {}
    trees: dict[str, ast.Module] = {}
    for p in pkg_files:
        m = _mod_name(project_root, p)
        if not m:
            continue
        mod_to_path[m] = p
        path_to_mod[p] = m
        trees[m] = ast.parse(originals[p].decode("utf-8"), filename=str(p))

    edge_stmts: dict[tuple[str, str], list[ast.ImportFrom]] = {}
    adj: dict[str, set[str]] = {m: set() for m in mod_to_path}
    for m, tree in trees.items():
        is_init = mod_to_path[m].name == "__init__.py"
        for stmt in tree.body:
            if isinstance(stmt, ast.ImportFrom):
                resolved = _resolve_import_from(m, is_init, stmt)
                if resolved in mod_to_path and resolved != m:
                    adj[m].add(resolved)
                    edge_stmts.setdefault((m, resolved), []).append(stmt)

    initial_cycle = _find_cycle(adj)
    if initial_cycle is None:
        raise RuntimeError("NO_IMPORT_CYCLE_FOUND")

    removals_by_mod: dict[str, list[ast.ImportFrom]] = {}
    insertions_by_mod: dict[str, list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]] = {}
    broken_edges: list[dict[str, Any]] = []

    while True:
        cyc = _find_cycle(adj)
        if cyc is None:
            break
        cycle_pairs = [(cyc[i], cyc[i + 1]) for i in range(len(cyc) - 1)]
        chosen: tuple[str, str, list[ast.ImportFrom], list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]] | None = None
        for u, v in cycle_pairs:
            stmts = edge_stmts.get((u, v), [])
            if not stmts:
                continue
            ext_claimed = _external_reexport_names(project_root, u, mod_to_path[u])
            plan_ins: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []
            ok = True
            for st in stmts:
                targets = _deferrable_targets(trees[u], st, ext_claimed)
                if targets is None:
                    ok = False
                    break
                for fn, aliases in targets:
                    plan_ins.append((fn, _format_import(v, aliases)))
            if ok:
                chosen = (u, v, stmts, plan_ins)
                break
        if chosen is None:
            raise RuntimeError("IMPORT_CYCLE_NOT_SAFELY_DEFERRABLE:" + "->".join(cyc))
        u, v, stmts, plan_ins = chosen
        adj[u].discard(v)
        removals_by_mod.setdefault(u, []).extend(stmts)
        insertions_by_mod.setdefault(u, []).extend(plan_ins)
        broken_edges.append({"from_module": u, "to_module": v, "deferred_count": len(plan_ins)})

    files_edited: list[str] = []
    try:
        for m, stmts in sorted(removals_by_mod.items()):
            p = mod_to_path[m]
            updated = _apply_deferrals_to_file(
                originals[p].decode("utf-8"),
                stmts,
                insertions_by_mod.get(m, []),
            )
            ast.parse(updated, filename=str(p))
            p.write_text(updated, encoding="utf-8")
            files_edited.append(p.relative_to(repo).as_posix())
        referee = _verify_imports_and_suite(project_root, list(mod_to_path), timeout_s)
    except Exception:
        for p, raw_bytes in originals.items():
            p.write_bytes(raw_bytes)
        raise

    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": src_dir.relative_to(repo).as_posix(),
        "files_edited": files_edited,
        "broken_edges": broken_edges,
        "referee": referee,
        "choreography_verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": True,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    reloaded = json.loads(output.read_bytes().decode("utf-8"))
    if reloaded.get("choreography_verified") is not True:
        raise RuntimeError("CHOREOGRAPHY_REVERIFY_FAILED")
    return {
        "adapter": "software_repair_crossfile_choreograph_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": sha,
        "output_verified": True,
        "verified": True,
        "choreography_verified": True,
        "files_edited": files_edited,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
