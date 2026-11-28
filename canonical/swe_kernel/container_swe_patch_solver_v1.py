#!/usr/bin/env python3
"""Container-native zero-LLM Python SWE patch solver backed by ContainerExecBridge.

Closes the Stage-2 host-vs-container execution gap: when a Harbor task container holds
repo-specific dependencies (e.g. ansible, openlibrary, qutebrowser virtualenvs) that are
not installed on the host runner, this solver runs traceback localization AND candidate
patch verification directly inside the live container via transactional overlays while
reusing read-only AST repair operators + 1-scope-hole minimal-subtree cross-repo transfer.
"""
from __future__ import annotations

import ast
import copy
import json
import pathlib
import re
import shlex
import time
from typing import Any, Mapping, Sequence

from canonical.swe_kernel import container_exec_bridge_v1 as _ce_bridge
from canonical.swe_kernel import minimal_subtree_transfer_v1 as _mst

_CACHED_TRANSFER_STORE: _mst.MinimalSubtreeTransferStore | None = None

_STDLIB_TEST_RUNNER = (
    "import importlib.util, inspect, pathlib, sys, traceback\n"
    "failed = 0\n"
    "for p in sys.argv[1:]:\n"
    "  spec = importlib.util.spec_from_file_location('_t', p)\n"
    "  mod = importlib.util.module_from_spec(spec)\n"
    "  spec.loader.exec_module(mod)\n"
    "  for n, f in inspect.getmembers(mod, inspect.isfunction):\n"
    "    if n.startswith('test_'):\n"
    "      try: f()\n"
    "      except Exception: failed += 1; traceback.print_exc()\n"
    "sys.exit(1 if failed else 0)\n"
)


def _get_transfer_store() -> _mst.MinimalSubtreeTransferStore:
    """Lazily train a 1-scope-hole minimal-subtree transfer store from the repo's real-fix corpora."""
    global _CACHED_TRANSFER_STORE
    if _CACHED_TRANSFER_STORE is not None:
        return _CACHED_TRANSFER_STORE
    store = _mst.MinimalSubtreeTransferStore(allow_one_scope_hole=True)
    corpus_dir = pathlib.Path(__file__).resolve().parents[1] / "corpus"
    sources_spec = (
        ("real_fix_pairs_20261119_V1.json", ("tasks", "pairs"), ("before", "before_source", "buggy_source"), ("after", "after_source", "fixed_source")),
        ("real_fix_commits_20261116_V1.json", ("grammar", "tasks"), ("defective", "before", "before_source"), ("repaired", "after", "after_source")),
    )
    for fname, list_keys, b_keys, a_keys in sources_spec:
        cpath = corpus_dir / fname
        if not cpath.is_file():
            continue
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
            items = []
            if isinstance(data, dict):
                for lk in list_keys:
                    if isinstance(data.get(lk), list):
                        items.extend(data[lk])
            elif isinstance(data, list):
                items = data
            for item in items:
                if not isinstance(item, dict):
                    continue
                b_src = next((item[k] for k in b_keys if isinstance(item.get(k), str) and item[k]), "")
                a_src = next((item[k] for k in a_keys if isinstance(item.get(k), str) and item[k]), "")
                if b_src and a_src:
                    store.learn_from_file_pair(b_src, a_src)
        except Exception:
            pass
    _CACHED_TRANSFER_STORE = store
    return store


def _parse_traceback_sites(
    tb_text: str,
    repo_root: pathlib.Path,
    workdir: str,
    repro_rels: Sequence[str],
) -> tuple[list[tuple[str, int]], str]:
    """Extract ordered in-repo `(rel_path, lineno)` fault sites and exception type from pytest/Python output."""
    repro_set = {r.lstrip("./") for r in repro_rels}
    sites: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    wd_prefix = workdir.rstrip("/") + "/"

    def _add(raw_path: str, ln: int) -> None:
        p = raw_path.strip()
        if p.startswith(wd_prefix):
            p = p[len(wd_prefix) :]
        p = p.lstrip("./")
        if p in repro_set or not p.endswith(".py") or p.startswith("/"):
            return
        pp = pathlib.PurePosixPath(p)
        # Never patch test files or pytest conftest hooks!
        if pp.name == "conftest.py" or pp.name.startswith("test_") or pp.name.endswith("_test.py"):
            return
        if any(part in ("tests", "test", "testing") for part in pp.parts[:-1]):
            return
        if (repo_root / p).is_file() and (p, ln) not in seen:
            seen.add((p, ln))
            sites.append((p, ln))

    # Pytest short traceback: `foo/bar.py:123: in func_name`
    for m in re.finditer(r"(?m)^([A-Za-z0-9_./-]+\.py):(\d+):", tb_text):
        _add(m.group(1), int(m.group(2)))
    # Standard Python traceback: `File "/app/foo/bar.py", line 123`
    for m in re.finditer(r'File "([^"]+\.py)", line (\d+)', tb_text):
        _add(m.group(1), int(m.group(2)))

    # Prefer deepest frames (closest to the crash/wrong return) first
    sites.reverse()

    exc_type = ""
    exc_m = re.findall(r"\b([A-Z][A-Za-z]+(?:Error|Exception))\b", tb_text)
    if exc_m:
        exc_type = exc_m[-1]
    elif re.search(r"(?m)^E\s+assert\b", tb_text):
        # pytest --tb=short prints `E       assert a == b` WITHOUT the literal word `AssertionError`!
        exc_type = "AssertionError"
    return sites, exc_type


def _extract_test_imported_symbols(repo_root: pathlib.Path, test_targets: Sequence[str]) -> list[str]:
    """Extract symbols imported or called inside the failing reproducer/test files (handles AssertionError returns!)."""
    syms: list[str] = []
    for tf in test_targets:
        p = repo_root / tf.split("::", 1)[0]
        if not p.is_file():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for al in node.names:
                    if al.name and al.name != "*" and al.name not in syms:
                        syms.append(al.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id not in syms:
                    syms.append(node.func.id)
                elif isinstance(node.func, ast.Attribute) and node.func.attr not in syms:
                    syms.append(node.func.attr)
    return syms


def _find_symbol_sites(repo_root: pathlib.Path, symbols: Sequence[str]) -> list[tuple[str, int]]:
    """Static localization: find executable body lines (return/if/assign) of `def <sym>` in repo Python files."""
    out: list[tuple[str, int]] = []
    sym_set = {s.split(".")[-1] for s in symbols if s}
    if not sym_set:
        return out
    for p in sorted(repo_root.rglob("*.py")):
        rel = p.relative_to(repo_root).as_posix()
        if any(part in (".git", ".venv", "venv", "node_modules", "__pycache__", "tests", "test", "examples", "example", "docs", "doc", "benchmarks", "samples", "demos") for part in p.parts):
            continue
        if p.name.startswith(("test_", "_epistemic_")) or p.name.endswith("_test.py"):
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            if not any(s in src for s in sym_set):
                continue
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in sym_set:
                body_lines: list[int] = []
                for stmt in ast.walk(node):
                    if isinstance(stmt, (ast.Return, ast.If, ast.Assign, ast.AugAssign, ast.Raise)) and hasattr(stmt, "lineno"):
                        ln = int(stmt.lineno)
                        if ln not in body_lines:
                            body_lines.append(ln)
                for ln in (body_lines[:6] or [int(node.lineno)]):
                    out.append((rel, ln))
                    if len(out) >= 12:
                        return out
    return out


def _enclosing_function(tree: ast.Module, lineno: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    best_span = 10**9
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = getattr(n, "end_lineno", n.lineno) or n.lineno
            if n.lineno <= lineno <= end_ln and (end_ln - n.lineno) < best_span:
                best = n
                best_span = end_ln - n.lineno
    return best


def _transfer_candidates_at_line(src: str, lineno: int) -> list[tuple[str, str]]:
    """Apply learned 1-scope-hole minimal-subtree rules to expressions on/around `lineno`."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    fn = _enclosing_function(tree, lineno)
    scope = _mst.collect_function_scope(fn) if fn is not None else []
    store = _get_transfer_store()
    if not store.rules():
        return []

    out: list[tuple[str, str]] = []
    seen_src: set[str] = {src}

    # Find expressions whose lineno matches [lineno-1, lineno+1]
    targets: list[tuple[int, int, int, int, ast.expr]] = []
    for node in ast.walk(fn or tree):
        if isinstance(node, ast.expr) and hasattr(node, "lineno") and abs(node.lineno - lineno) <= 1:
            if hasattr(node, "col_offset") and hasattr(node, "end_lineno") and hasattr(node, "end_col_offset"):
                targets.append((node.lineno, node.col_offset, node.end_lineno or node.lineno, node.end_col_offset or 0, node))

    lines = src.splitlines(keepends=True)
    for ln0, c0, ln1, c1, expr_node in targets[:12]:
        if ln0 != ln1 or ln0 < 1 or ln0 > len(lines):
            continue
        raw_line = lines[ln0 - 1]
        for rule, repl_expr in store.apply_to_expr(expr_node, scope_names=scope)[:6]:
            new_line = raw_line[:c0] + repl_expr + raw_line[c1:]
            cand_src = "".join(lines[: ln0 - 1] + [new_line] + lines[ln0:])
            if cand_src in seen_src:
                continue
            try:
                ast.parse(cand_src)
            except SyntaxError:
                continue
            seen_src.add(cand_src)
            out.append((f"minimal_subtree_transfer({rule.example[:36]})", cand_src))
            if len(out) >= 12:
                return out
    return out


def _intrafile_callee_ranges(tree: ast.Module, fn: ast.FunctionDef | ast.AsyncFunctionDef | None, total_lines: int, fallback_ln: int) -> list[tuple[int, int]]:
    """Return 0-based `[start, end)` line ranges for `fn` plus up to 2-hop intra-file callees."""
    if fn is None:
        return [(max(0, fallback_ln - 12), min(total_lines, fallback_ln + 2))]
    defs_by_name: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    ranges: list[tuple[int, int]] = []
    visited: set[str] = {fn.name}
    frontier: list[ast.FunctionDef | ast.AsyncFunctionDef] = [fn]
    for _depth in range(3):
        next_frontier: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for cur in frontier:
            ranges.append((max(0, cur.lineno - 1), min(total_lines, cur.end_lineno or cur.lineno)))
            for node in ast.walk(cur):
                nm = node.id if isinstance(node, ast.Name) else (node.attr if isinstance(node, ast.Attribute) else "")
                if nm and nm in defs_by_name and nm not in visited:
                    visited.add(nm)
                    next_frontier.append(defs_by_name[nm])
                    if len(visited) >= 12:
                        break
            if len(visited) >= 12:
                break
        frontier = next_frontier
        if not frontier:
            break
    return ranges


def _generate_python_candidates_at_site(
    src: str,
    lineno: int,
    exc_type: str,
    tb_text: str,
) -> list[tuple[str, str]]:
    """Combine exception-specific causal operators + Causal Angelic AST mutators + 1-hole transfer."""
    from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE

    cands: list[tuple[str, str]] = []
    seen: set[str] = {src}

    def _add(desc: str, patched: str) -> None:
        if not patched or patched in seen:
            return
        try:
            ast.parse(patched)
        except SyntaxError:
            return
        seen.add(patched)
        cands.append((desc, patched))

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    lines = src.splitlines(keepends=True)

    # 0. PRIORITY 0: Exception-specific & assertion-diff causal operators (ALWAYS before generic flips!)
    if 1 <= lineno <= len(lines):
        raw = lines[lineno - 1]
        # Bytes/str file-mode mismatch on TypeError (`bytes-like object is required`, `must be str, not bytes`)
        # Expands across 1-hop intra-file callees (e.g. `get_pager_file` -> `_tempfilepager`)!
        if exc_type == "TypeError" and ("bytes" in tb_text.lower() or "str" in tb_text.lower()):
            fn_b = _enclosing_function(tree, lineno)
            for scan_start, scan_end in _intrafile_callee_ranges(tree, fn_b, len(lines), lineno):
                for idx_b in range(scan_start, scan_end):
                    ln_b = lines[idx_b]
                    for old_m, new_m in (
                        ('mode="wb"', 'mode="w"'),
                        ("mode='wb'", "mode='w'"),
                        ('mode="w"', 'mode="wb"'),
                        ('mode="rb"', 'mode="r"'),
                        ('mode="r"', 'mode="rb"'),
                        (', "wb"', ', "w"'),
                        (', "w"', ', "wb"'),
                    ):
                        if old_m in ln_b:
                            _add(
                                f"file_mode({old_m}->{new_m})",
                                "".join(lines[:idx_b] + [ln_b.replace(old_m, new_m, 1)] + lines[idx_b + 1 :]),
                            )
        # KeyError / subscript safe .get() rewrite
        if exc_type == "KeyError":
            m_sub = re.search(r"\b([A-Za-z_]\w*)\[([^\[\]\n]+)\]", raw)
            if m_sub and "=" not in raw[m_sub.end() : m_sub.end() + 3]:
                repl = f"{m_sub.group(1)}.get({m_sub.group(2)})"
                new_line = raw[: m_sub.start()] + repl + raw[m_sub.end() :]
                _add("keyerror_dict_get", "".join(lines[: lineno - 1] + [new_line] + lines[lineno:]))
        # Safe getattr rewrite on AttributeError
        if exc_type == "AttributeError":
            m_attr = re.search(r"has no attribute '([A-Za-z_]\w*)'", tb_text)
            if m_attr:
                aname = m_attr.group(1)
                m_use = re.search(rf"\b([A-Za-z_]\w*)\.{re.escape(aname)}\b", raw)
                if m_use and "=" not in raw[m_use.end() : m_use.end() + 3]:
                    repl = f"getattr({m_use.group(1)}, {aname!r}, None)"
                    new_line = raw[: m_use.start()] + repl + raw[m_use.end() :]
                    _add(f"safe_getattr({aname})", "".join(lines[: lineno - 1] + [new_line] + lines[lineno:]))
        # NoneType / empty-collection entry guard on enclosing function
        fn_enc = _enclosing_function(tree, lineno)
        if fn_enc is not None and fn_enc.body and exc_type in ("AttributeError", "TypeError", "IndexError", "ValueError"):
            p_names = [a.arg for a in fn_enc.args.args if a.arg not in ("self", "cls")]
            first_body_ln = fn_enc.body[0].lineno
            if 1 <= first_body_ln <= len(lines) and p_names:
                indent = re.match(r"^(\s*)", lines[first_body_ln - 1]).group(1)  # type: ignore[union-attr]
                p0 = p_names[0]
                if "NoneType" in tb_text or exc_type in ("AttributeError", "TypeError"):
                    for ret_v in ("None", '""', "[]", "False"):
                        guard = f"{indent}if {p0} is None:\n{indent}    return {ret_v}\n"
                        _add(f"none_entry_guard({p0}->{ret_v})", "".join(lines[: first_body_ln - 1] + [guard] + lines[first_body_ln - 1 :]))
                if exc_type == "IndexError":
                    for ret_v in ("None", '""', "[]"):
                        guard = f"{indent}if not {p0}:\n{indent}    return {ret_v}\n"
                        _add(f"empty_entry_guard({p0}->{ret_v})", "".join(lines[: first_body_ln - 1] + [guard] + lines[first_body_ln - 1 :]))
        # Assertion-diff string normalization, constant/default substitution & wrapper unwrap!
        if exc_type == "AssertionError":
            m_eq = re.search(r"assert\s+(['\"])(.*?)\1\s*==\s*(['\"])(.*?)\3", tb_text)
            if not m_eq:
                m_call_eq = re.search(r"assert\s+[A-Za-z_][\w.]*\(\s*(['\"])(.*?)\1\s*\)\s*==\s*(['\"])(.*?)\3", tb_text)
                if m_call_eq:
                    m_eq = m_call_eq
            m_ret = re.match(r"^(\s*return\s+)(.+?)(\s*)$", raw)
            if m_eq and m_ret:
                got_s, want_s = m_eq.group(2), m_eq.group(4)
                ret_expr = m_ret.group(2)
                if got_s.strip() == want_s:
                    _add("return_strip", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}({ret_expr}).strip()\n"] + lines[lineno:]))
                if got_s.lower() == want_s:
                    _add("return_lower", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}({ret_expr}).lower()\n"] + lines[lineno:]))
                if got_s.rstrip("/") == want_s:
                    _add("return_rstrip_slash", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}({ret_expr}).rstrip('/')\n"] + lines[lineno:]))
                if repr(got_s) in ret_expr:
                    _add("return_literal_sub", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}{ret_expr.replace(repr(got_s), repr(want_s), 1)}\n"] + lines[lineno:]))
            if m_ret and re.search(r"assert\s+None\s*==\s*\[\]", tb_text):
                _add("return_or_list", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}({m_ret.group(2)}) or []\n"] + lines[lineno:]))
            if m_ret and re.search(r"assert\s+None\s*==\s*['\"]['\"]", tb_text):
                _add("return_or_str", "".join(lines[: lineno - 1] + [f"{m_ret.group(1)}({m_ret.group(2)}) or ''\n"] + lines[lineno:]))

            # Exact scalar/default substitution from pytest `assert <GOT> == <WANT>` (e.g. `302 == 303`, `False == True`)
            m_scalar = re.search(r"assert\s+(-?\d+|True|False)\s*==\s*(-?\d+|True|False)\b", tb_text)
            if m_scalar and m_scalar.group(1) != m_scalar.group(2):
                got_k, want_k = m_scalar.group(1), m_scalar.group(2)
                fn_s = _enclosing_function(tree, lineno)
                for sc_start, sc_end in _intrafile_callee_ranges(tree, fn_s, len(lines), lineno):
                    pat_k = re.compile(rf"\b{re.escape(got_k)}\b")
                    for idx_k in range(sc_start, sc_end):
                        ln_k = lines[idx_k]
                        if pat_k.search(ln_k):
                            _add(
                                f"assert_scalar_sub({got_k}->{want_k}@L{idx_k+1})",
                                "".join(lines[:idx_k] + [pat_k.sub(want_k, ln_k, count=1)] + lines[idx_k + 1 :]),
                            )

            # 1-arg wrapper call unwrap (`fn(x) -> x`, e.g. `_(text) -> text`, `str(x) -> x`) across enclosing function
            # AND sibling methods in the same enclosing class (handles 2-hunk consistent class fixes!).
            fn_u = _enclosing_function(tree, lineno)
            u_start = (fn_u.lineno - 1) if fn_u is not None else max(0, lineno - 1)
            u_end = min(len(lines), (fn_u.end_lineno or lineno) if fn_u is not None else lineno)
            # Find enclosing class if any
            cls_range: tuple[int, int] | None = None
            for _node in ast.walk(tree):
                if isinstance(_node, ast.ClassDef) and _node.lineno <= lineno <= (_node.end_lineno or _node.lineno):
                    cls_range = (max(0, _node.lineno - 1), min(len(lines), _node.end_lineno or _node.lineno))
                    break
            seen_wraps: set[tuple[str, str]] = set()
            for idx_u in range(u_start, u_end):
                ln_u = lines[idx_u]
                for m_wrap in re.finditer(r"(?<![.\w])([A-Za-z_]\w*)\(([A-Za-z_]\w*)\)", ln_u):
                    wfn, warg = m_wrap.group(1), m_wrap.group(2)
                    if wfn not in ("def", "class", "return", "if", "for", "while", "not", "len", "isinstance", "super", "type", "print", "raise"):
                        new_l = ln_u[: m_wrap.start()] + warg + ln_u[m_wrap.end() :]
                        _add(
                            f"unwrap_call({wfn}({warg})->{warg}@L{idx_u+1})",
                            "".join(lines[:idx_u] + [new_l] + lines[idx_u + 1 :]),
                        )
                        if cls_range is not None and (wfn, warg) not in seen_wraps:
                            seen_wraps.add((wfn, warg))
                            c_pat = re.compile(rf"(?<![.\w]){re.escape(wfn)}\({re.escape(warg)}\)")
                            cs, ce = cls_range
                            cls_lines = [c_pat.sub(warg, l) for l in lines[cs:ce]]
                            _add(
                                f"unwrap_call_class({wfn}({warg})->{warg})",
                                "".join(lines[:cs] + cls_lines + lines[ce:]),
                            )

    # 1. Causal Angelic AST condition / exception / hoist mutators (pure Python, read-only reuse)
    for ln in (lineno, max(1, lineno - 1), lineno + 1):
        try:
            for d, s in PY_SWE._mutate_condition_exprs(tree, ln):
                _add(d, s)
        except Exception:
            pass
    if exc_type:
        try:
            for d, s in PY_SWE._widen_enclosing_except(tree, lineno, exc_type):
                _add(d, s)
        except Exception:
            pass
        try:
            for d, s in PY_SWE._synthesize_exception_repairs(tree, lineno, exc_type, tb_text):
                _add(d, s)
        except Exception:
            pass
    try:
        for d, s in PY_SWE._hoist_inner_stmt(tree, lineno):
            _add(d, s)
    except Exception:
        pass

    # 2. Scope-grounded 1-hole Minimal-Subtree Cross-Repo Transfer (learned from real OSS fix pairs!)
    # Cap duplicate rule descriptions to 2 per rule so one rule never crowds out other candidates!
    _rule_counts: dict[str, int] = {}
    for d, s in _transfer_candidates_at_line(src, lineno):
        if _rule_counts.get(d, 0) >= 2:
            continue
        _rule_counts[d] = _rule_counts.get(d, 0) + 1
        _add(d, s)

    # 3. Direct safe line-level comparison & boolean operator flips
    if 1 <= lineno <= len(lines):
        raw = lines[lineno - 1]
        for old_op, new_op in ((" < ", " <= "), (" <= ", " < "), (" > ", " >= "), (" >= ", " > "), (" == ", " != "), (" != ", " == "), (" is None", " is not None"), (" is not None", " is None"), (" and ", " or "), (" or ", " and ")):
            if old_op in raw:
                _add(
                    f"op_flip({old_op.strip()}->{new_op.strip()})",
                    "".join(lines[: lineno - 1] + [raw.replace(old_op, new_op, 1)] + lines[lineno:]),
                )

    return cands[:48]


def _count_pytest_failures(out_text: str) -> int | None:
    """Parse failure/error count from pytest short summary (`2 failed, 14 passed` -> 2)."""
    m = re.search(r"(\d+)\s+failed\b", out_text)
    if m:
        return int(m.group(1))
    m_e = re.search(r"(\d+)\s+error", out_text)
    if m_e:
        return int(m_e.group(1))
    return None


def solve_python_with_container_bridge(
    ws: pathlib.Path,
    test_targets: Sequence[str],
    *,
    python_src_root: str = "",
    referenced_symbols: Sequence[str] = (),
    issue_text: str = "",
    timeout_s: float = 45.0,
    max_candidates: int = 36,
) -> dict[str, Any]:
    """Solve a Python repo bug executing every probe & patch check inside the live Docker container."""
    t0 = time.monotonic()
    bridge = _ce_bridge.get_active_bridge()
    if bridge is None or not bridge.toolchain.python_exe:
        return {"status": "NO_CONTAINER_BRIDGE", "verified": False}

    py_c = bridge.toolchain.python_exe
    if not python_src_root and (ws / "src").is_dir():
        python_src_root = "src"
    pp_expr = f"{bridge.workdir}/{python_src_root}:{bridge.workdir}" if python_src_root else bridge.workdir
    tf_args = " ".join(shlex.quote(t) for t in test_targets)
    if bridge.toolchain.has_pytest:
        test_cmd = f"PYTHONPATH={shlex.quote(pp_expr)}:${{PYTHONPATH:-}} PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 {shlex.quote(py_c)} -m pytest -q --tb=short {tf_args}"
    else:
        test_cmd = f"PYTHONPATH={shlex.quote(pp_expr)}:${{PYTHONPATH:-}} {shlex.quote(py_c)} -c {shlex.quote(_STDLIB_TEST_RUNNER)} {tf_args}"

    # Base overlays include the temporary reproducer file(s) written into `ws`
    base_overlays = bridge.collect_modified_overlays(ws)

    # Step 1: Run inside the real container to get the real traceback & fault sites!
    rc0, out0, err0 = bridge.run_cmd(test_cmd, overlays=base_overlays, timeout_s=min(20.0, timeout_s / 3.0))
    tb_text = (out0 or "") + "\n" + (err0 or "")
    # Bypass broken repo-root conftest.py hooks when the target test file doesn't need them!
    if bridge.toolchain.has_pytest and rc0 == 4 and "ImportError while loading conftest" in tb_text:
        test_cmd = f"PYTHONPATH={shlex.quote(pp_expr)}:${{PYTHONPATH:-}} PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 {shlex.quote(py_c)} -m pytest --noconftest -q --tb=short {tf_args}"
        rc0, out0, err0 = bridge.run_cmd(test_cmd, overlays=base_overlays, timeout_s=min(20.0, timeout_s / 3.0))
        tb_text = (out0 or "") + "\n" + (err0 or "")
    if rc0 == 0:
        return {"status": "ALREADY_PASSING", "verified": False, "via_container_bridge": True}
    if bridge.toolchain.has_pytest and rc0 in (2, 3, 4, 5) and "FAILED " not in tb_text:
        return {"status": "COLLECTION_OR_ENV_ERROR", "verified": False, "pre_rc": rc0, "via_container_bridge": True}

    sites, exc_type = _parse_traceback_sites(tb_text, ws, bridge.workdir, test_targets)
    # Deduplicate traceback sites to at most 1 per (file, enclosing_func) so wrapper frames
    # never crowd out the real BM25-localized fault function!
    dedup_sites: list[tuple[str, int]] = []
    seen_funcs: set[tuple[str, str]] = set()
    for rf_p, rf_ln in sites:
        try:
            _t = ast.parse((ws / rf_p).read_text(encoding="utf-8", errors="replace"))
            _fn = _enclosing_function(_t, rf_ln)
            fkey = (rf_p, _fn.name if _fn else f"L{rf_ln}")
        except Exception:
            fkey = (rf_p, f"L{rf_ln}")
        if fkey not in seen_funcs:
            seen_funcs.add(fkey)
            dedup_sites.append((rf_p, rf_ln))
    sites = dedup_sites

    # ALWAYS place Top-3 BM25-localized functions right after traceback sites — BEFORE alphabetical symbol scans!
    # Enrich BM25 query with clean failing test stems/names (`tests/test_utils.py::test_redirect` -> `utils redirect`)!
    _q_parts: list[str] = [issue_text] if issue_text else []
    for _t in test_targets:
        _stem = pathlib.PurePosixPath(_t.split("::", 1)[0]).stem
        _q_parts.append(re.sub(r"^test_|_test$", "", _stem))
    for _m_fail in re.finditer(r"FAILED\s+\S+::([A-Za-z0-9_]+)", tb_text):
        _q_parts.append(re.sub(r"^test_", "", _m_fail.group(1)))
    bm25_query = " ".join(p for p in _q_parts if p)
    if bm25_query.strip():
        from canonical.swe_kernel import bm25_code_localizer_v1 as _bm25

        for rf in _bm25.localize_functions_bm25(ws, bm25_query, language="python", top_k=3):
            fkey = (rf.rel_path, rf.name)
            if fkey not in seen_funcs:
                seen_funcs.add(fkey)
                sites.append((rf.rel_path, rf.lineno))

    if len(sites) < 3:
        sym_pool = list(referenced_symbols) + _extract_test_imported_symbols(ws, test_targets)
        for sp_p, sp_ln in _find_symbol_sites(ws, sym_pool):
            fkey = (sp_p, f"L{sp_ln}")
            if fkey not in seen_funcs:
                seen_funcs.add(fkey)
                sites.append((sp_p, sp_ln))
            if len(sites) >= 6:
                break
    if not sites:
        return {
            "status": "NO_LOCALIZED_SITES",
            "verified": False,
            "exc_type": exc_type,
            "via_container_bridge": True,
        }

    # Step 2: Generate & verify candidates directly inside the real container!
    # Supports monotonic multi-hunk / multi-file composition: whenever a candidate strictly reduces
    # pytest failure count (`0 < n_fail < best_fail`), accept it into `committed_overlays` and continue!
    tried = 0
    best_fail = _count_pytest_failures(tb_text)
    committed_overlays: dict[str, str] = {}
    committed_descs: list[str] = []

    for rel_file, ln in sites[:5]:
        if time.monotonic() - t0 > timeout_s or tried >= max_candidates:
            break
        orig_src = committed_overlays.get(rel_file) or (ws / rel_file).read_text(encoding="utf-8", errors="replace")
        cands = _generate_python_candidates_at_site(orig_src, ln, exc_type, tb_text)
        # Prioritize exception-specific operators before generic corpus transfer rules; cap per site!
        per_site_budget = max(6, max_candidates // max(1, min(len(sites), 5)))
        for desc, patched_src in cands[:per_site_budget]:
            if time.monotonic() - t0 > timeout_s or tried >= max_candidates:
                break
            tried += 1
            ov = dict(base_overlays)
            ov.update(committed_overlays)
            ov[rel_file] = patched_src
            rc, out_c, err_c = bridge.run_cmd(test_cmd, overlays=ov, timeout_s=min(20.0, max(8.0, timeout_s - (time.monotonic() - t0))))
            comb_c = (out_c or "") + "\n" + (err_c or "")
            if rc == 0 and "no tests ran" not in comb_c.lower():
                all_patched = dict(committed_overlays)
                all_patched[rel_file] = patched_src
                full_desc = " + ".join(committed_descs + [desc])
                return {
                    "status": "VERIFIED",
                    "verified": True,
                    "via_container_bridge": True,
                    "candidates_tried": tried,
                    "winner": {
                        "file": rel_file,
                        "lineno": ln,
                        "tier": "CONTAINER_BRIDGE_CAUSAL_AND_TRANSFER",
                        "description": full_desc,
                        "patched_source": patched_src,
                        "extra_patches": {k: v for k, v in all_patched.items() if k != rel_file},
                    },
                }
            # Monotonic progress? Keep the partial patch and move to the next fault site!
            n_fail = _count_pytest_failures(comb_c)
            if best_fail is not None and n_fail is not None and 0 < n_fail < best_fail:
                best_fail = n_fail
                committed_overlays[rel_file] = patched_src
                committed_descs.append(desc)
                break

    return {
        "status": "UNSOLVED",
        "verified": False,
        "via_container_bridge": True,
        "candidates_tried": tried,
        "exc_type": exc_type,
        "sites_checked": sites[:3],
    }
