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
        if any(part in (".git", ".venv", "venv", "node_modules", "__pycache__", "tests", "test") for part in p.parts):
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


def _generate_python_candidates_at_site(
    src: str,
    lineno: int,
    exc_type: str,
    tb_text: str,
) -> list[tuple[str, str]]:
    """Combine Causal Angelic AST mutators + 1-hole Minimal-Subtree transfer + guard repairs."""
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
    for d, s in _transfer_candidates_at_line(src, lineno):
        _add(d, s)

    # 3. Direct safe line-level guard & boundary operators
    lines = src.splitlines(keepends=True)
    if 1 <= lineno <= len(lines):
        raw = lines[lineno - 1]
        for old_op, new_op in ((" < ", " <= "), (" <= ", " < "), (" > ", " >= "), (" >= ", " > "), (" == ", " != "), (" != ", " == "), (" is None", " is not None"), (" is not None", " is None"), (" and ", " or "), (" or ", " and ")):
            if old_op in raw:
                _add(
                    f"op_flip({old_op.strip()}->{new_op.strip()})",
                    "".join(lines[: lineno - 1] + [raw.replace(old_op, new_op, 1)] + lines[lineno:]),
                )
        # KeyError / subscript safe .get() rewrite: `d[k]` -> `d.get(k)`
        if exc_type == "KeyError":
            m_sub = re.search(r"\b([A-Za-z_]\w*)\[([^\[\]\n]+)\]", raw)
            if m_sub and "=" not in raw[m_sub.end() : m_sub.end() + 3]:
                repl = f"{m_sub.group(1)}.get({m_sub.group(2)})"
                new_line = raw[: m_sub.start()] + repl + raw[m_sub.end() :]
                _add("keyerror_dict_get", "".join(lines[: lineno - 1] + [new_line] + lines[lineno:]))

    return cands[:36]


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
    if rc0 == 0:
        return {"status": "ALREADY_PASSING", "verified": False, "via_container_bridge": True}

    sites, exc_type = _parse_traceback_sites(tb_text, ws, bridge.workdir, test_targets)
    if not sites:
        sym_pool = list(referenced_symbols) + _extract_test_imported_symbols(ws, test_targets)
        sites = _find_symbol_sites(ws, sym_pool)
    if issue_text and len(sites) < 3:
        from canonical.swe_kernel import bm25_code_localizer_v1 as _bm25

        for rf in _bm25.localize_functions_bm25(ws, issue_text, language="python", top_k=5):
            # Include body lines of each BM25-localized function!
            for extra_site in _find_symbol_sites(ws, [rf.name]):
                if extra_site[0] == rf.rel_path and extra_site not in sites:
                    sites.append(extra_site)
            if (rf.rel_path, rf.lineno) not in sites:
                sites.append((rf.rel_path, rf.lineno))
    if not sites:
        return {
            "status": "NO_LOCALIZED_SITES",
            "verified": False,
            "exc_type": exc_type,
            "via_container_bridge": True,
        }

    # Step 2: Generate & verify candidates directly inside the real container!
    tried = 0
    for rel_file, ln in sites[:3]:
        if time.monotonic() - t0 > timeout_s or tried >= max_candidates:
            break
        orig_src = (ws / rel_file).read_text(encoding="utf-8", errors="replace")
        cands = _generate_python_candidates_at_site(orig_src, ln, exc_type, tb_text)
        for desc, patched_src in cands:
            if time.monotonic() - t0 > timeout_s or tried >= max_candidates:
                break
            tried += 1
            ov = dict(base_overlays)
            ov[rel_file] = patched_src
            rc, _, _ = bridge.run_cmd(test_cmd, overlays=ov, timeout_s=min(20.0, max(8.0, timeout_s - (time.monotonic() - t0))))
            if rc == 0:
                return {
                    "status": "VERIFIED",
                    "verified": True,
                    "via_container_bridge": True,
                    "candidates_tried": tried,
                    "winner": {
                        "file": rel_file,
                        "lineno": ln,
                        "tier": "CONTAINER_BRIDGE_CAUSAL_AND_TRANSFER",
                        "description": desc,
                        "patched_source": patched_src,
                    },
                }

    return {
        "status": "UNSOLVED",
        "verified": False,
        "via_container_bridge": True,
        "candidates_tried": tried,
        "exc_type": exc_type,
        "sites_checked": sites[:3],
    }
