#!/usr/bin/env python3
"""python.repair.sql_parameterize.v1 — AST SQL-interpolation parameterizer + referee.

Rewrites interpolated SQL strings passed to ``<cursor>.execute(...)`` (%-formatting,
f-strings, ``str.format``, and string ``+`` concatenation) into DB-API parameterized
queries ``<cursor>.execute(sql, params)``, refusing unsafe identifier-slot splicing
and verifying the edited tree against fresh imports and the project's unittest suite
with full byte rollback on any failure.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_SQL_PARAMETERIZE_V1"
CAPABILITY_ID = "python.repair.sql_parameterize.v1"
PROVIDES = ["python.repair.sql_parameterized", "python.security.sql_injection.removed"]
REQUIRES: list[str] = []

_SQL_HEAD_RE = re.compile(r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|WITH|REPLACE)\b", re.IGNORECASE)
_UNSAFE_IDENT_BEFORE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE|ORDER\s+BY|GROUP\s+BY)\s+$",
    re.IGNORECASE,
)


def _safe_path(root: pathlib.Path, raw: str | None, code: str) -> pathlib.Path:
    if not raw or not str(raw).strip():
        raise RuntimeError(code)
    p = (root / str(raw).strip()).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = _safe_path(root, raw or "canonical/tmp_sql_parameterize.json", "OUTPUT_PATH_REQUIRED")
    if p.suffix.lower() == ".py" and p.exists():
        raise RuntimeError("OUTPUT_COLLIDES_WITH_PYTHON_SOURCE")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _uses_sqlite3(files: list[pathlib.Path]) -> bool:
    for p in files:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "sqlite3" for a in node.names):
                return True
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "sqlite3":
                return True
    return False


def _line_offsets(text: str) -> list[int]:
    offs = [0]
    for ln in text.splitlines(keepends=True):
        offs.append(offs[-1] + len(ln))
    return offs


def _span_slice(text: str, offs: list[int], node: ast.AST) -> tuple[int, int, str]:
    start = offs[node.lineno - 1] + node.col_offset
    end = offs[(node.end_lineno or node.lineno) - 1] + (node.end_col_offset or node.col_offset)
    return start, end, text[start:end]


def _append_segment_and_placeholder(
    sql_parts: list[str],
    next_literal: str,
    placeholder: str,
) -> tuple[str, bool]:
    """Strip SQL quote wrappers around an interpolated value and check identifier safety."""
    prev = "".join(sql_parts)
    quoted_single = prev.endswith("'") and next_literal.startswith("'")
    quoted_double = prev.endswith('"') and next_literal.startswith('"')
    if quoted_single or quoted_double:
        sql_parts[-1] = sql_parts[-1][:-1]
        next_literal = next_literal[1:]
    prefix_check = "".join(sql_parts)
    if not (quoted_single or quoted_double) and _UNSAFE_IDENT_BEFORE_RE.search(prefix_check):
        raise RuntimeError("UNSAFE_SQL_IDENTIFIER_INTERPOLATION")
    sql_parts.append(placeholder)
    return next_literal, True


def _extract_concat_parts(node: ast.AST) -> list[ast.AST] | None:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _extract_concat_parts(node.left)
        right = _extract_concat_parts(node.right)
        if left is None or right is None:
            return None
        return left + right
    return [node]


def _unwrap_str_call(expr: ast.AST) -> ast.AST:
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "str"
        and len(expr.args) == 1
        and not expr.keywords
    ):
        return expr.args[0]
    return expr


def _parameterize_expr(
    query_node: ast.AST,
    src_text: str,
    offs: list[int],
    placeholder: str,
) -> tuple[str, str] | None:
    """Return ``(sql_literal_code, params_tuple_code)`` or ``None`` if not an interpolated SQL query."""
    # 1. "SELECT ... '%s'" % val  or  "SELECT ... %s ... %s" % (a, b)
    if (
        isinstance(query_node, ast.BinOp)
        and isinstance(query_node.op, ast.Mod)
        and isinstance(query_node.left, ast.Constant)
        and isinstance(query_node.left.value, str)
    ):
        template = query_node.left.value
        if not _SQL_HEAD_RE.search(template):
            return None
        if re.search(r"%\([A-Za-z_][A-Za-z0-9_]*\)[sd]", template):
            return None
        tokens = list(re.finditer(r"%%|%[sdr]", template))
        real_specs = [m for m in tokens if m.group(0) != "%%"]
        if not real_specs:
            return None
        sql_parts: list[str] = []
        cursor = 0
        for idx, m in enumerate(real_specs):
            seg = template[cursor : m.start()].replace("%%", "%")
            sql_parts.append(seg)
            nxt_end = real_specs[idx + 1].start() if idx + 1 < len(real_specs) else len(template)
            nxt = template[m.end() : nxt_end]
            trimmed_nxt, _ = _append_segment_and_placeholder(sql_parts, nxt, placeholder)
            # Advance cursor if leading quote of nxt was consumed
            consumed = len(nxt) - len(trimmed_nxt)
            cursor = m.end() + consumed
        sql_parts.append(template[cursor:].replace("%%", "%"))
        sql_str = "".join(sql_parts)
        rhs = query_node.right
        if isinstance(rhs, ast.Tuple):
            if len(rhs.elts) != len(real_specs):
                return None
            elt_srcs = [_span_slice(src_text, offs, e)[2] for e in rhs.elts]
            params_src = "(" + ", ".join(elt_srcs) + ("," if len(elt_srcs) == 1 else "") + ")"
        else:
            if len(real_specs) != 1:
                return None
            rhs_src = _span_slice(src_text, offs, rhs)[2]
            params_src = f"({rhs_src},)"
        return repr(sql_str), params_src

    # 2. f"SELECT ... '{user_id}'"
    if isinstance(query_node, ast.JoinedStr):
        literals: list[str] = []
        exprs: list[ast.AST] = []
        cur_lit = ""
        for val in query_node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                cur_lit += val.value
            elif isinstance(val, ast.FormattedValue):
                if val.format_spec is not None:
                    return None
                literals.append(cur_lit)
                cur_lit = ""
                exprs.append(val.value)
            else:
                return None
        literals.append(cur_lit)
        if not exprs or not _SQL_HEAD_RE.search(literals[0]):
            return None
        sql_parts = [literals[0]]
        for idx, _e in enumerate(exprs):
            nxt = literals[idx + 1]
            nxt, _ = _append_segment_and_placeholder(sql_parts, nxt, placeholder)
            sql_parts.append(nxt)
        elt_srcs = [_span_slice(src_text, offs, e)[2] for e in exprs]
        params_src = "(" + ", ".join(elt_srcs) + ("," if len(elt_srcs) == 1 else "") + ")"
        return repr("".join(sql_parts)), params_src

    # 3. "SELECT ... '{}'".format(a, ...)
    if (
        isinstance(query_node, ast.Call)
        and isinstance(query_node.func, ast.Attribute)
        and query_node.func.attr == "format"
        and isinstance(query_node.func.value, ast.Constant)
        and isinstance(query_node.func.value.value, str)
        and query_node.args
        and not query_node.keywords
    ):
        template = query_node.func.value.value
        if not _SQL_HEAD_RE.search(template):
            return None
        specs = list(re.finditer(r"\{(?:\d+)?\}", template))
        if len(specs) != len(query_node.args):
            return None
        ordered_args: list[ast.AST] = []
        sql_parts = []
        cursor = 0
        for idx, m in enumerate(specs):
            tok = m.group(0)[1:-1]
            arg_idx = int(tok) if tok else idx
            if arg_idx >= len(query_node.args):
                return None
            ordered_args.append(query_node.args[arg_idx])
            sql_parts.append(template[cursor : m.start()])
            nxt_end = specs[idx + 1].start() if idx + 1 < len(specs) else len(template)
            nxt = template[m.end() : nxt_end]
            trimmed_nxt, _ = _append_segment_and_placeholder(sql_parts, nxt, placeholder)
            cursor = m.end() + (len(nxt) - len(trimmed_nxt))
        sql_parts.append(template[cursor:])
        elt_srcs = [_span_slice(src_text, offs, e)[2] for e in ordered_args]
        params_src = "(" + ", ".join(elt_srcs) + ("," if len(elt_srcs) == 1 else "") + ")"
        return repr("".join(sql_parts)), params_src

    # 4. "SELECT ... '" + user_id + "'"
    parts = _extract_concat_parts(query_node)
    if parts and len(parts) >= 2:
        first = parts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str) and _SQL_HEAD_RE.search(first.value):
            sql_parts = []
            exprs = []
            i = 0
            cur_lit = ""
            while i < len(parts):
                p = parts[i]
                if isinstance(p, ast.Constant) and isinstance(p.value, str):
                    cur_lit += p.value
                else:
                    sql_parts.append(cur_lit)
                    cur_lit = ""
                    exprs.append(_unwrap_str_call(p))
                i += 1
            if not exprs:
                return None
            # Rebuild with quote stripping around each interpolated expression
            rebuilt = [sql_parts[0]]
            trailing = sql_parts[1:] + [cur_lit]
            for idx in range(len(exprs)):
                nxt = trailing[idx]
                nxt, _ = _append_segment_and_placeholder(rebuilt, nxt, placeholder)
                rebuilt.append(nxt)
            elt_srcs = [_span_slice(src_text, offs, e)[2] for e in exprs]
            params_src = "(" + ", ".join(elt_srcs) + ("," if len(elt_srcs) == 1 else "") + ")"
            return repr("".join(rebuilt)), params_src

    return None


def _discover_project_root(src_dir: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    if (src_dir / "__init__.py").is_file() and src_dir.parent != repo and repo in src_dir.parent.parents:
        return src_dir.parent
    return src_dir


def _run_referee(project_root: pathlib.Path, edited_paths: list[pathlib.Path], timeout_s: float) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project_root))
    mods: list[str] = []
    for p in edited_paths:
        rel = p.relative_to(project_root).as_posix()
        no_ext = rel[:-3] if rel.endswith(".py") else rel
        m = ".".join(seg for seg in no_ext.split("/") if seg and seg != "__init__")
        if m:
            mods.append(m)
    if mods:
        code = "import importlib\nfor m in " + repr(mods) + ":\n    importlib.import_module(m)\n"
        proc = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"IMPORT_FAILED_AFTER_SQL_REPAIR:{(proc.stderr or proc.stdout)[-300:]}")

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
            raise RuntimeError(f"TESTS_RED_AFTER_SQL_REPAIR:{(proc.stderr or proc.stdout)[-300:]}")
    return {"imports_ok": True, "suite_ran": suite_ran, "suite_ok": True}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    src_arg = _safe_path(repo, str(args.get("source_root") or ""), "SOURCE_ROOT_REQUIRED")
    timeout_s = float(args.get("timeout_s") or 60.0)
    mod_opt = args.get("module")

    if src_arg.is_file():
        src_dir = src_arg.parent
        candidates = [src_arg]
    elif src_arg.is_dir():
        src_dir = src_arg
        if mod_opt:
            target = _safe_path(src_dir, str(mod_opt), "MODULE_INVALID")
            if not target.is_file():
                raise RuntimeError(f"MODULE_NOT_FOUND:{mod_opt}")
            candidates = [target]
        else:
            candidates = sorted(
                p for p in src_dir.rglob("*.py")
                if p.is_file() and "__pycache__" not in p.parts and "tests" not in p.relative_to(src_dir).parts
            )
    else:
        raise RuntimeError("SOURCE_ROOT_MISSING")

    project_root = _discover_project_root(src_dir, repo)
    all_py = sorted(p for p in project_root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}
    placeholder = "?" if _uses_sqlite3(all_py) else "%s"

    edits_by_file: dict[pathlib.Path, list[tuple[int, int, str]]] = {}
    parameterized_sites: list[dict[str, Any]] = []

    for path in candidates:
        src_text = originals[path].decode("utf-8")
        tree = ast.parse(src_text, filename=str(path))
        offs = _line_offsets(src_text)
        file_splices: list[tuple[int, int, str]] = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and len(node.args) == 1
                and not node.keywords
            ):
                continue
            rewritten = _parameterize_expr(node.args[0], src_text, offs, placeholder)
            if rewritten is None:
                continue
            sql_code, params_code = rewritten
            func_src = _span_slice(src_text, offs, node.func)[2]
            call_start, call_end, _ = _span_slice(src_text, offs, node)
            replacement = f"{func_src}({sql_code}, {params_code})"
            file_splices.append((call_start, call_end, replacement))
            parameterized_sites.append({
                "file": path.relative_to(repo).as_posix(),
                "line": node.lineno,
                "placeholder": placeholder,
                "sql": sql_code,
            })
        if file_splices:
            edits_by_file[path] = file_splices

    if not edits_by_file:
        raise RuntimeError("NO_SQL_INJECTION_SITES_FOUND")

    files_edited: list[str] = []
    try:
        for path, splices in sorted(edits_by_file.items()):
            updated = originals[path].decode("utf-8")
            for start, end, repl in sorted(splices, key=lambda item: (item[0], item[1]), reverse=True):
                updated = updated[:start] + repl + updated[end:]
            ast.parse(updated, filename=str(path))
            path.write_text(updated, encoding="utf-8")
            files_edited.append(path.relative_to(repo).as_posix())
        referee = _run_referee(project_root, list(edits_by_file), timeout_s)
    except Exception:
        for p, raw_bytes in originals.items():
            p.write_bytes(raw_bytes)
        raise

    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "files_edited": files_edited,
        "parameterized_count": len(parameterized_sites),
        "sites": parameterized_sites,
        "referee": referee,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    return {
        "adapter": "python_source_sql_parameterize",
        "output_path": output.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
        "verified": True,
        "files_edited": files_edited,
        "parameterized_count": len(parameterized_sites),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
