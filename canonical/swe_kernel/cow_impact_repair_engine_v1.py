#!/usr/bin/env python3
"""Zero-Copy CoW Impact-Sliced STUN Guard & Coupled Multi-File Repair Engine (`K3 = 0`).

Composes five existing repository organs to break the single-expression and
subprocess-latency ceilings (`HISTORICAL_REPAIR_TRANSFER_20261101_V1.md`,
`HARDCORE_SWE_ALL_PROBLEMS_20261101_V4.md`):
  1. Zero-Copy Hardlink CoW Workspace (`create_zero_copy_cow_workspace` + `cow_write_text`):
     Clones multi-hundred-file workspaces in `< 10 ms` via `os.link` (vs ~540 ms+
     `shutil.copytree`) while guaranteeing zero mutation of the live tree (`unlink`
     before write breaks the hardlink cleanly).
  2. Tree-Sitter Incremental Index & Test-Impact Slicer (`code_tree_sitter_incremental_index_v1`
     + `code_tree_sitter_impact_v1`): runs ONLY tests transitively importing changed files.
  3. Bottom-Up Observational-Equivalence + STUN Guard Synthesizer
     (`swe_observational_program_synthesizer_v1`): synthesizes `if/elif/else` guards,
     edge-case insertions, and multi-branch function bodies from failing test assertions.
  4. Coupled Multi-File Fault Localizer (`python_coupled_software_repair_loop_v1`):
     ranks coupled caller/callee modules from tracebacks + imports and proposes
     coordinated 2-file patches.
  5. `ZygotePrewarmedPool` (`os.fork()` CoW in-memory candidate evaluation):
     evaluates 32-64 single-file, STUN-guard, or coupled 2-file patches in `< 180 ms`
     instead of `16.8 s` of cold `pytest` subprocesses.
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import itertools
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import types
from typing import Any, Mapping, Sequence

from canonical.runtime import swe_observational_program_synthesizer_v1 as obs_synth
from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as ts_impact
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as ts_index
from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as coupled_loop
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

SCHEMA = "PROJECT_BRAIN_COW_IMPACT_REPAIR_ENGINE_V1"

_IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "build", "dist",
})

_BINOP_SWAPS: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
    ast.Add: (ast.Sub, ast.Mult),
    ast.Sub: (ast.Add,),
    ast.Mult: (ast.Add, ast.FloorDiv, ast.Div),
    ast.Div: (ast.FloorDiv, ast.Mult),
    ast.FloorDiv: (ast.Div, ast.Mult),
}

_CMPOP_SWAPS: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
    ast.Lt: (ast.LtE, ast.Gt, ast.GtE),
    ast.LtE: (ast.Lt, ast.GtE, ast.Gt),
    ast.Gt: (ast.GtE, ast.Lt, ast.LtE),
    ast.GtE: (ast.Gt, ast.LtE, ast.Lt),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}

_BOOLOP_SWAPS: dict[type[ast.boolop], tuple[type[ast.boolop], ...]] = {
    ast.And: (ast.Or,),
    ast.Or: (ast.And,),
}


def create_zero_copy_cow_workspace(src_root: pathlib.Path, dst_root: pathlib.Path) -> dict[str, Any]:
    """Materialize a zero-copy `os.link` CoW clone of `src_root` at `dst_root` in `< 10 ms`."""
    t0 = time.perf_counter_ns()
    src_root = pathlib.Path(src_root).resolve()
    dst_root = pathlib.Path(dst_root).resolve()
    dst_root.mkdir(parents=True, exist_ok=True)
    linked = 0
    copied = 0
    for cur_dir, dirnames, filenames in os.walk(src_root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
        rel_dir = pathlib.Path(cur_dir).relative_to(src_root)
        target_dir = dst_root / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            sp = pathlib.Path(cur_dir) / fn
            if sp.is_symlink():
                continue
            dp = target_dir / fn
            try:
                os.link(sp, dp)
                linked += 1
            except OSError:
                shutil.copy2(sp, dp)
                copied += 1
    return {
        "files_linked": linked,
        "files_copied": copied,
        "clone_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }


def cow_write_text(path: pathlib.Path, content: str) -> None:
    """Break any hardlink (`unlink`) before writing and purge stale `.pyc` bytecode caches."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.unlink()
    p.write_text(content, encoding="utf-8")
    if p.suffix == ".py":
        pycache = p.parent / "__pycache__"
        if pycache.is_dir():
            for pyc in pycache.glob(f"{p.stem}.*.pyc"):
                try:
                    pyc.unlink()
                except OSError:
                    pass


def _extract_changed_method_pair(old_src: str, new_src: str) -> tuple[str, str] | None:
    """When exactly one `ClassDef` method changed between `old_src` and `new_src`, return canonical `(before_fn, after_fn)`."""
    try:
        old_tree = ast.parse(old_src)
        new_tree = ast.parse(new_src)
    except SyntaxError:
        return None
    old_methods: dict[tuple[str, str], ast.FunctionDef] = {}
    new_methods: dict[tuple[str, str], ast.FunctionDef] = {}
    for node in old_tree.body:
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    old_methods[(node.name, sub.name)] = sub
    for node in new_tree.body:
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    new_methods[(node.name, sub.name)] = sub
    changed: list[tuple[str, str]] = []
    for key, old_fn in old_methods.items():
        new_fn = new_methods.get(key)
        if new_fn is None:
            continue
        u_old = ast.unparse(old_fn) + "\n"
        u_new = ast.unparse(new_fn) + "\n"
        if u_old != u_new:
            changed.append((u_old, u_new))
    if len(changed) == 1:
        return changed[0]
    return None


def _iter_file_or_method_rule_candidates(src_txt: str, lang_rule: Mapping[str, Any], *, limit: int = 6) -> list[str]:
    """Yield candidate file patches from `lang_rule` applied at file scope AND individual `ClassDef` method scope, honoring `learned_scope`."""
    import textwrap
    from canonical.swe_kernel import operator_generalization_v1 as op_gen
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        iter_crystallized_code_rule_candidates,
    )

    learned_scope = str(lang_rule.get("learned_scope") or "")
    out: list[str] = []
    for cand in itertools.islice(iter_crystallized_code_rule_candidates(src_txt, lang_rule), limit):
        if cand and cand != src_txt and cand not in out:
            out.append(cand)
    if learned_scope != "SCOPE_STATEMENT" and len(out) < limit:
        for op_cand in itertools.islice(op_gen.propose_operator_swaps(src_txt, lang_rule, language="python"), limit - len(out)):
            if op_cand and op_cand != src_txt and op_cand not in out:
                out.append(op_cand)
    if len(out) >= limit:
        return out[:limit]
    try:
        tree = ast.parse(src_txt)
    except SyntaxError:
        return out
    lines = src_txt.splitlines(keepends=True)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if not isinstance(sub, ast.FunctionDef) or not getattr(sub, "end_lineno", None):
                continue
            start_idx = sub.lineno - 1
            end_idx = int(sub.end_lineno)
            raw_block = "".join(lines[start_idx:end_idx])
            indent_prefix = raw_block[: len(raw_block) - len(raw_block.lstrip(" "))]
            dedented = textwrap.dedent(raw_block)
            if not dedented.endswith("\n"):
                dedented += "\n"
            for m_cand in itertools.islice(iter_crystallized_code_rule_candidates(dedented, lang_rule), 4):
                if not m_cand or m_cand == dedented:
                    continue
                reindented = textwrap.indent(m_cand if m_cand.endswith("\n") else m_cand + "\n", indent_prefix)
                full_cand = "".join(lines[:start_idx]) + reindented + "".join(lines[end_idx:])
                try:
                    ast.parse(full_cand)
                except SyntaxError:
                    continue
                if full_cand != src_txt and full_cand not in out:
                    out.append(full_cand)
                    if len(out) >= limit:
                        return out
    return out


def select_impacted_tests_fast(
    repo_root: pathlib.Path,
    changed_rel_paths: Sequence[str],
    all_test_files: Sequence[pathlib.Path],
) -> dict[str, Any]:
    """Compute the minimal impacted test slice via SQLite-WAL `IncrementalSemanticGraph` first (`< 5 ms` warm), falling back to `code_tree_sitter_impact_v1`."""
    t0 = time.perf_counter_ns()
    repo = pathlib.Path(repo_root).resolve()
    selected_paths: list[pathlib.Path] = []
    used_semantic_graph = False
    used_tree_sitter = False

    # Fast Path 1: Content-addressed SQLite-WAL IncrementalSemanticGraph (no temp JSON files on disk!)
    try:
        from canonical.swe_kernel import incremental_semantic_graph_v1 as sem_graph

        sem_res = sem_graph.query_impacted_tests(repo, ".", list(changed_rel_paths))
        if sem_res.get("exact_hit") and sem_res.get("impacted_tests"):
            for p_rel in sem_res.get("impacted_tests") or []:
                cand_p = (repo / str(p_rel)).resolve()
                if cand_p.is_file():
                    selected_paths.append(cand_p)
            if selected_paths:
                used_semantic_graph = True
                used_tree_sitter = True
    except Exception:
        selected_paths = []

    # Fast Path 2: Tree-sitter incremental index + impact fallback
    if not selected_paths:
        idx_rel = ".brain_cow_ts_index.json"
        imp_rel = ".brain_cow_ts_impact.json"
        try:
            ts_index.run(
                {
                    "source_root": ".",
                    "index_path": idx_rel,
                    "output_path": idx_rel,
                },
                repo,
            )
            imp_res = ts_impact.run(
                {
                    "source_root": ".",
                    "index_path": idx_rel,
                    "changed_files": list(changed_rel_paths),
                    "output_path": imp_rel,
                },
                repo,
            )
            for p_rel in imp_res.get("selected_tests") or []:
                cand_p = (repo / str(p_rel)).resolve()
                if cand_p.is_file():
                    selected_paths.append(cand_p)
            used_tree_sitter = True
        except Exception:
            selected_paths = []
        finally:
            for tmp_name in (idx_rel, imp_rel):
                tp = repo / tmp_name
                if tp.exists():
                    tp.unlink()

    if not selected_paths:
        # Conservative fallback: run tests mentioning the changed module stems, else all tests
        stems = {pathlib.PurePosixPath(r).stem for r in changed_rel_paths}
        matched = [
            tf for tf in all_test_files
            if any(st in tf.read_text(encoding="utf-8", errors="replace") for st in stems)
        ]
        selected_paths = matched or list(all_test_files)

    return {
        "selected_tests": selected_paths,
        "selected_count": len(selected_paths),
        "total_tests": len(all_test_files),
        "used_semantic_graph": used_semantic_graph,
        "used_tree_sitter": used_tree_sitter,
        "slice_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }


def probe_concurrency_races_in_cow(
    workspace_root: pathlib.Path | str,
    *,
    threads: int = 8,
    iterations: int = 200,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """Run live multi-threaded concurrency race probing inside a zero-copy CoW clone via `multistep_repo_closed_loop_solver_v1`."""
    from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as mrs

    ws = pathlib.Path(workspace_root).resolve()
    with tempfile.TemporaryDirectory(prefix="brain_cow_race_") as tmp:
        cow_root = pathlib.Path(tmp) / "repo"
        clone_stats = create_hardlink_cow_clone(ws, cow_root)
        probe_res = mrs.probe_concurrency_races_live(
            cow_root,
            threads=int(threads),
            iterations=int(iterations),
            timeout=float(timeout),
        )
        return {
            "schema": SCHEMA,
            "clone": clone_stats,
            "race_probe": probe_res,
            "races_found": bool(probe_res.get("races") or probe_res.get("race_detected") or probe_res.get("failures")),
        }


def _extract_focus_lines(fail_trace: str, rel_path: str) -> list[int]:
    """Extract traceback line numbers referencing `rel_path` (or its basename) from `fail_trace`."""
    import re

    base = pathlib.PurePosixPath(rel_path).name
    found: list[int] = []
    for pat in (
        re.compile(rf"(?:{re.escape(rel_path)}|{re.escape(base)}):(\d+)"),
        re.compile(rf'File "[^"]*(?:{re.escape(rel_path)}|{re.escape(base)})", line (\d+)'),
    ):
        for m in pat.finditer(fail_trace or ""):
            ln = int(m.group(1))
            if ln not in found:
                found.append(ln)
    return found


def _single_file_ast_mutations(
    source_text: str,
    max_candidates: int = 24,
    *,
    focus_lines: Sequence[int] | None = None,
) -> list[str]:
    """Generate small syntactically valid operator/comparison/boolean/constant repairs, ranked by traceback proximity."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    lines = source_text.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))

    def _span(nd: ast.AST) -> tuple[int, int] | None:
        l0, c0 = getattr(nd, "lineno", None), getattr(nd, "col_offset", None)
        l1, c1 = getattr(nd, "end_lineno", None), getattr(nd, "end_col_offset", None)
        if None in (l0, c0, l1, c1):
            return None
        s_b = lines[l0 - 1].encode("utf-8")
        e_b = lines[l1 - 1].encode("utf-8")
        return (
            offsets[l0 - 1] + len(s_b[:c0].decode("utf-8", errors="replace")),
            offsets[l1 - 1] + len(e_b[:c1].decode("utf-8", errors="replace")),
        )

    out: list[str] = []
    seen: set[str] = {source_text}

    def _emit(s_i: int, e_i: int, repl: str) -> None:
        for wrapped in (repl, f"({repl})"):
            cand = source_text[:s_i] + wrapped + source_text[e_i:]
            if cand not in seen:
                try:
                    ast.parse(cand)
                    seen.add(cand)
                    out.append(cand)
                    return
                except SyntaxError:
                    continue

    nodes = [nd for nd in ast.walk(tree) if getattr(nd, "lineno", None) is not None]
    if focus_lines:
        fl_list = list(focus_lines)
        nodes.sort(key=lambda nd: (min(abs(int(nd.lineno) - fl) for fl in fl_list), int(nd.lineno)))

    for nd in nodes:
        sp = _span(nd)
        if sp is None:
            continue
        s_i, e_i = sp
        if isinstance(nd, ast.BinOp) and type(nd.op) in _BINOP_SWAPS:
            for alt in _BINOP_SWAPS[type(nd.op)]:
                dup = copy.deepcopy(nd)
                dup.op = alt()
                _emit(s_i, e_i, ast.unparse(dup))
        elif isinstance(nd, ast.Compare) and len(nd.ops) == 1 and type(nd.ops[0]) in _CMPOP_SWAPS:
            for alt_c in _CMPOP_SWAPS[type(nd.ops[0])]:
                dup = copy.deepcopy(nd)
                dup.ops = [alt_c()]
                _emit(s_i, e_i, ast.unparse(dup))
        elif isinstance(nd, ast.BoolOp) and type(nd.op) in _BOOLOP_SWAPS:
            for alt_b in _BOOLOP_SWAPS[type(nd.op)]:
                dup = copy.deepcopy(nd)
                dup.op = alt_b()
                _emit(s_i, e_i, ast.unparse(dup))
        elif isinstance(nd, ast.UnaryOp) and isinstance(nd.op, ast.Not):
            _emit(s_i, e_i, ast.unparse(nd.operand))
        elif isinstance(nd, ast.Constant) and isinstance(nd.value, bool):
            _emit(s_i, e_i, "False" if nd.value else "True")
        elif isinstance(nd, ast.Constant) and isinstance(nd.value, int) and not isinstance(nd.value, bool):
            for delta in (-1, 1, 0):
                nv = 0 if delta == 0 else nd.value + delta
                if nv != nd.value:
                    _emit(s_i, e_i, repr(nv))
        if len(out) >= max_candidates:
            break
    return out


def _fn_used_params(fn_node: ast.FunctionDef) -> set[str]:
    param_set = {a.arg for a in fn_node.args.args}
    return {
        sub.id
        for sub in ast.walk(fn_node)
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id in param_set
    }


def _passes_concrete_contract_oracle(source_text: str) -> bool:
    """Reject any candidate whose unary docstring `post:` contract fails on concrete execution witness."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return False
    from canonical.runtime.bound_capabilities import concrete_execution_oracle as concrete_oracle

    for nd in tree.body:
        if isinstance(nd, ast.FunctionDef) and len(nd.args.args) == 1:
            doc = ast.get_docstring(nd) or ""
            if "post:" in doc.lower() or "postcondition:" in doc.lower():
                try:
                    probe_src = source_text + f"\nf = {nd.name}\n"
                    res = concrete_oracle.check_source(probe_src)
                    if res.get("status") == "CONTRACT_VIOLATION_FOUND":
                        return False
                except Exception:
                    continue
    return True


def propose_stun_and_guard_repairs(
    source_text: str,
    test_sources: Sequence[str],
    *,
    max_candidates: int = 16,
) -> list[str]:
    """Synthesize minimal entry/mid-function guards first, then input-preserving STUN bodies (functions & class methods)."""
    from canonical.runtime.bound_capabilities.software_patch_cegis_z3_v1 import (
        _extract_method_io_examples_from_test_source,
    )

    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    combined_tests = "\n\n".join(test_sources)
    lines = source_text.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))

    out: list[str] = []
    seen: set[str] = {source_text}

    # Build safe evaluation namespace for domain helpers/classes/constants in `source_text`
    ctx_ns: dict[str, Any] = {"__builtins__": obs_synth._SAFE_EVAL_BUILTINS}
    try:
        exec(compile(source_text, "<stun_ctx>", "exec"), ctx_ns)
    except Exception:
        pass

    targets: list[tuple[str | None, ast.FunctionDef]] = []
    for top in tree.body:
        if isinstance(top, ast.FunctionDef):
            targets.append((None, top))
        elif isinstance(top, ast.ClassDef):
            for sub in top.body:
                if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("__"):
                    targets.append((top.name, sub))

    for cls_name, fn in targets:
        params = [a.arg for a in fn.args.args]
        orig_used_params = _fn_used_params(fn) - {"self"}
        fn_start = offsets[fn.lineno - 1]
        fn_end = offsets[fn.end_lineno - 1] + len(
            lines[fn.end_lineno - 1].encode("utf-8")[:fn.end_col_offset].decode("utf-8", errors="replace")
        )

        # 1. Deterministic entry / mid-function zero/empty guard insertions FIRST (minimal surgical diff)
        stmts = [
            s for s in fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
        ]
        for st in stmts:
            st_line_start = offsets[st.lineno - 1]
            st_col_indent = lines[st.lineno - 1][:st.col_offset]
            for sub in ast.walk(st):
                if isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    if isinstance(sub.right, ast.Name) and sub.right.id in params and sub.right.id != "self":
                        p_nm = sub.right.id
                        for ret_lit in ("0.0", "0", "None", "[]"):
                            guard = f"{st_col_indent}if {p_nm} == 0:\n{st_col_indent}    return {ret_lit}\n"
                            cand = source_text[:st_line_start] + guard + source_text[st_line_start:]
                            if cand not in seen and _passes_concrete_contract_oracle(cand):
                                try:
                                    ast.parse(cand)
                                    seen.add(cand)
                                    out.append(cand)
                                except SyntaxError:
                                    pass
            if len(out) >= max_candidates:
                return out

        is_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in ast.walk(fn))
        has_loop = any(isinstance(sub, (ast.For, ast.While, ast.ListComp)) for sub in ast.walk(fn))
        if (is_gen or has_loop) and stmts and params:
            st0 = stmts[0]
            st0_start = offsets[st0.lineno - 1]
            ind0 = lines[st0.lineno - 1][:st0.col_offset]
            for p_nm in params:
                if p_nm == "self":
                    continue
                ret_tail = "return" if is_gen else "return []"
                guard = f"{ind0}if {p_nm} == 0:\n{ind0}    {ret_tail}\n"
                cand = source_text[:st0_start] + guard + source_text[st0_start:]
                if cand not in seen and _passes_concrete_contract_oracle(cand):
                    try:
                        ast.parse(cand)
                        seen.add(cand)
                        out.append(cand)
                    except SyntaxError:
                        pass
                if len(out) >= max_candidates:
                    return out

        # 2. STUN + Bottom-Up Observational-Equivalence synthesis (functions & stateful class methods!)
        if params and combined_tests and len(out) < max_candidates:
            try:
                if cls_name is None:
                    exs, consts = obs_synth.extract_io_examples_from_test_source(combined_tests, fn.name, ctx_ns)
                else:
                    exs, consts = _extract_method_io_examples_from_test_source(
                        combined_tests, cls_name, fn.name, ctx_ns
                    )
                if exs:
                    synth_body = obs_synth.synthesize_python_function_body(params, exs, consts)
                    if synth_body:
                        body_indent = " " * (int(fn.col_offset) + 4)
                        indented = "\n".join(body_indent + ln for ln in synth_body.splitlines())
                        sig_end = offsets[fn.body[0].lineno - 1]
                        header = source_text[fn_start:sig_end].rstrip()
                        cand = source_text[:fn_start] + header + "\n" + indented + "\n" + source_text[fn_end:]
                        parsed_cand = ast.parse(cand)
                        if cls_name is None:
                            cand_fns = [
                                n for n in parsed_cand.body
                                if isinstance(n, ast.FunctionDef) and n.name == fn.name
                            ]
                        else:
                            cand_fns = [
                                sub
                                for top_n in parsed_cand.body
                                if isinstance(top_n, ast.ClassDef) and top_n.name == cls_name
                                for sub in top_n.body
                                if isinstance(sub, ast.FunctionDef) and sub.name == fn.name
                            ]
                        if (
                            cand_fns
                            and orig_used_params.issubset(_fn_used_params(cand_fns[0]) - {"self"})
                            and cand not in seen
                            and _passes_concrete_contract_oracle(cand)
                        ):
                            seen.add(cand)
                            out.append(cand)
            except Exception:
                pass
    return out


def _module_dotted_name(repo_root: pathlib.Path, file_path: pathlib.Path) -> list[str]:
    """Possible importable dotted names for `file_path` (preferring `src/`-stripped package names)."""
    rel = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    names: list[str] = []
    candidates = (rel[4:], rel) if rel.startswith("src/") else (rel,)
    for candidate_rel in candidates:
        if candidate_rel.endswith("/__init__.py"):
            mod = candidate_rel[:-12].replace("/", ".")
        elif candidate_rel.endswith(".py"):
            mod = candidate_rel[:-3].replace("/", ".")
        else:
            continue
        if mod and mod not in names:
            names.append(mod)
    return names


def evaluate_patch_batch_in_cow_zygote(
    repo_root: pathlib.Path,
    patch_candidates: Sequence[Mapping[str, str]],
    impacted_tests: Sequence[pathlib.Path],
    *,
    zygote: ZygotePrewarmedPool | None = None,
) -> dict[str, Any]:
    """Evaluate a batch of single-file or multi-file patch maps `{rel_path: new_src}` inside one CoW fork."""
    repo = pathlib.Path(repo_root).resolve()
    test_payloads = [
        (tf.relative_to(repo).as_posix(), tf.read_text(encoding="utf-8", errors="replace"))
        for tf in impacted_tests
    ]
    needs_pytest_runner = any(
        ("import pytest" in t_src or "from pytest" in t_src)
        for _, t_src in test_payloads
    ) or (repo / "conftest.py").is_file() or (repo / "testing" / "conftest.py").is_file() or (repo / "tests" / "conftest.py").is_file()

    def _batch_worker() -> dict[str, Any]:
        import contextlib
        import io as _io

        t_start = time.perf_counter_ns()
        repo_str = str(repo)
        repo_prefix = repo_str + os.sep
        src_str = str(repo / "src")
        sys.path[:] = [
            p for p in sys.path
            if p and not (p.startswith("/tmp/") and p != repo_str and p != src_str)
        ]
        for p_entry in (repo_str, src_str):
            if pathlib.Path(p_entry).is_dir() and p_entry not in sys.path:
                sys.path.insert(0, p_entry)
        sys.path_importer_cache.clear()
        shadow_pkgs = _repo_top_level_pkg_names(repo)
        for mod_k in list(sys.modules):
            if mod_k.split(".", 1)[0] in shadow_pkgs:
                sys.modules.pop(mod_k, None)

        # Pre-compile all test ASTs once inside the CoW worker when pure zero-arg runner applies!
        compiled_tests = (
            []
            if needs_pytest_runner
            else [(t_rel, compile(t_src, t_rel, "exec")) for t_rel, t_src in test_payloads]
        )
        pytest_mod = None
        if needs_pytest_runner:
            import pytest as _pytest_mod

            pytest_mod = _pytest_mod

        orig_disk_texts: dict[str, str] = {}
        if needs_pytest_runner:
            for pm in patch_candidates:
                for rp in pm:
                    if rp not in orig_disk_texts and (repo / rp).is_file():
                        orig_disk_texts[rp] = (repo / rp).read_text(encoding="utf-8")

        checked = 0
        for idx, patch_map in enumerate(patch_candidates):
            checked += 1
            if needs_pytest_runner and pytest_mod is not None:
                try:
                    for rel_p, new_src in patch_map.items():
                        cow_write_text(repo / rel_p, new_src)
                    top_pkgs = {
                        p.name
                        for base in (repo, repo / "src")
                        if base.is_dir()
                        for p in base.iterdir()
                        if p.is_dir() and (p / "__init__.py").is_file()
                    }
                    # Meta-guard: `pytest` itself depends on `pluggy` & `_pytest`; if the target repo
                    # redefines `pluggy` or `_pytest`, run isolated subprocess with `PYTHONPATH=src`
                    if top_pkgs & {"pluggy", "_pytest", "pytest"}:
                        sub_env = dict(os.environ)
                        sub_env["PYTHONDONTWRITEBYTECODE"] = "1"
                        sub_env["PYTHONPATH"] = os.pathsep.join(
                            [str(p) for p in (repo / "src", repo) if p.is_dir()]
                        )
                        sp = subprocess.run(
                            [sys.executable, "-B", "-m", "pytest", "-q", "--tb=no", "-x", "-p", "no:cacheprovider"]
                            + [str(repo / tr) for tr, _ in test_payloads],
                            cwd=str(repo),
                            env=sub_env,
                            capture_output=True,
                            timeout=12,
                        )
                        all_passed = sp.returncode == 0
                    else:
                        for m_name, m_val in list(sys.modules.items()):
                            if m_name.split(".", 1)[0] in top_pkgs:
                                sys.modules.pop(m_name, None)
                                continue
                            m_file = getattr(m_val, "__file__", None)
                            if isinstance(m_file, str) and m_file.startswith(repo_prefix):
                                sys.modules.pop(m_name, None)
                        sink = _io.StringIO()
                        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                            rc = pytest_mod.main(
                                ["-q", "--tb=no", "-x", "-p", "no:cacheprovider"]
                                + [str(repo / tr) for tr, _ in test_payloads]
                            )
                        all_passed = int(rc) == 0
                except BaseException:
                    all_passed = False
                finally:
                    for rel_p in patch_map:
                        if rel_p in orig_disk_texts:
                            cow_write_text(repo / rel_p, orig_disk_texts[rel_p])
                if all_passed:
                    return {
                        "found": True,
                        "winning_index": idx,
                        "candidates_evaluated": checked,
                        "worker_eval_ms": round((time.perf_counter_ns() - t_start) / 1e6, 3),
                    }
                continue

            saved_mods: dict[str, Any] = {}
            injected_names: list[str] = []
            compile_ok = True
            try:
                # 1. Compile and inject all patched modules in topological / sorted order
                mod_objs: list[tuple[list[str], Any, types.ModuleType]] = []
                for rel_p, new_src in sorted(patch_map.items()):
                    d_names = _module_dotted_name(repo, repo / rel_p)
                    code_obj = compile(new_src, str(repo / rel_p), "exec")
                    primary_name = d_names[0] if d_names else pathlib.PurePosixPath(rel_p).stem
                    # Ensure parent packages are imported before relative imports execute
                    if "." in primary_name:
                        parent_pkg = primary_name.rsplit(".", 1)[0]
                        try:
                            import importlib
                            importlib.import_module(parent_pkg)
                        except Exception:
                            pass
                    mod_obj = types.ModuleType(primary_name)
                    mod_obj.__file__ = str(repo / rel_p)
                    if rel_p.endswith("/__init__.py") or rel_p == "__init__.py":
                        mod_obj.__package__ = primary_name
                        mod_obj.__path__ = [str((repo / rel_p).parent)]
                    elif "." in primary_name:
                        mod_obj.__package__ = primary_name.rsplit(".", 1)[0]
                    else:
                        mod_obj.__package__ = ""
                    for dn in d_names:
                        if dn not in saved_mods:
                            saved_mods[dn] = sys.modules.get(dn)
                        sys.modules[dn] = mod_obj
                        injected_names.append(dn)
                    mod_objs.append((d_names, code_obj, mod_obj))

                parent_pkgs: set[str] = {
                    dn.rsplit(".", 1)[0] for d_names, _, _ in mod_objs for dn in d_names if "." in dn
                }
                # Evict non-parent intra-repo dependents before `exec`, keeping parent packages alive so relative imports succeed!
                for m_name, m_val in list(sys.modules.items()):
                    if m_name in injected_names or m_name in parent_pkgs:
                        continue
                    m_file = getattr(m_val, "__file__", None)
                    if isinstance(m_file, str) and m_file.startswith(repo_prefix) and m_name not in saved_mods:
                        saved_mods[m_name] = m_val
                        sys.modules.pop(m_name, None)

                for _, code_obj, mod_obj in mod_objs:
                    exec(code_obj, mod_obj.__dict__)

                # Re-bind parent package re-exports (e.g. `pluggy.__init__` importing `from ._manager import PluginManager`)
                import importlib
                for pp in sorted(parent_pkgs):
                    p_mod = sys.modules.get(pp)
                    if p_mod is not None:
                        if pp not in saved_mods:
                            saved_mods[pp] = p_mod
                        try:
                            importlib.reload(p_mod)
                        except Exception:
                            pass
            except Exception:
                compile_ok = False

            all_passed = False
            if compile_ok:
                all_passed = True
                for t_rel, t_code in compiled_tests:
                    t_ns: dict[str, Any] = {"__name__": "__cow_test__", "__file__": str(repo / t_rel)}
                    try:
                        exec(t_code, t_ns)
                        for attr, fn_obj in list(t_ns.items()):
                            if attr.startswith("test_") and callable(fn_obj):
                                fn_obj()
                            elif isinstance(fn_obj, type) and attr.startswith("Test"):
                                inst = fn_obj()
                                for m_attr in dir(inst):
                                    if m_attr.startswith("test_") and callable(getattr(inst, m_attr)):
                                        if hasattr(inst, "setUp"):
                                            inst.setUp()
                                        try:
                                            getattr(inst, m_attr)()
                                        finally:
                                            if hasattr(inst, "tearDown"):
                                                inst.tearDown()
                    except BaseException:
                        all_passed = False
                        break

            # Restore sys.modules before next candidate
            for k in list(sys.modules.keys()):
                if k not in saved_mods and k in injected_names:
                    sys.modules.pop(k, None)
            for k, old_v in saved_mods.items():
                if old_v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = old_v

            if all_passed:
                return {
                    "found": True,
                    "winning_index": idx,
                    "candidates_evaluated": checked,
                    "worker_eval_ms": round((time.perf_counter_ns() - t_start) / 1e6, 3),
                }

        return {
            "found": False,
            "winning_index": -1,
            "candidates_evaluated": checked,
            "worker_eval_ms": round((time.perf_counter_ns() - t_start) / 1e6, 3),
        }

    pool = zygote or ZygotePrewarmedPool()
    return pool.run_isolated(_batch_worker)


def _repo_top_level_pkg_names(repo_root: pathlib.Path) -> set[str]:
    names: set[str] = set()
    for base in (repo_root / "src", repo_root):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.name.startswith(".") or child.name in ("tests", "testing", "docs"):
                continue
            if child.is_dir() and (child / "__init__.py").is_file():
                names.add(child.name)
            elif child.is_file() and child.suffix == ".py" and not child.name.startswith("test_"):
                names.add(child.stem)
    return names


def _run_disk_suite_check(
    repo_root: pathlib.Path,
    test_files: Sequence[pathlib.Path],
    timeout: float = 12.0,
    *,
    zygote: ZygotePrewarmedPool | None = None,
) -> tuple[bool, str]:
    # Fast path: execute `pytest.main` inside a disposable CoW-forked Zygote child (`~25-120 ms` vs `750 ms` cold subprocess!)
    has_pytest_style = any(
        "def test_" in tf.read_text(encoding="utf-8", errors="replace")
        and "__main__" not in tf.read_text(encoding="utf-8", errors="replace")
        for tf in test_files
    )
    if has_pytest_style and zygote is not None:
        pkg_names = _repo_top_level_pkg_names(repo_root)
        tf_strs = [str(tf) for tf in test_files]
        repo_str = str(repo_root)
        src_str = str(repo_root / "src") if (repo_root / "src").is_dir() else None

        def _zygote_pytest_runner() -> dict[str, Any]:
            import importlib
            import inspect
            import traceback

            os.chdir(repo_str)
            # Strip stale temporary workspace paths & outer `_pytest` assertion hooks inherited across `os.fork()`
            sys.path[:] = [
                p for p in sys.path
                if p and not (p.startswith("/tmp/") and p != repo_str and p != src_str)
            ]
            sys.path.insert(0, repo_str)
            if src_str:
                sys.path.insert(0, src_str)
            sys.meta_path[:] = [m for m in sys.meta_path if "_pytest" not in type(m).__module__]
            sys.path_importer_cache.clear()
            for mod_k in list(sys.modules):
                top = mod_k.split(".", 1)[0]
                if top in pkg_names or mod_k.startswith("test_") or mod_k.startswith("testing"):
                    sys.modules.pop(mod_k, None)
            importlib.invalidate_caches()

            # Re-entrancy-safe, ~4 ms direct zero-fixture test runner inside forked CoW Zygote child;
            # raises `NEEDS_PYTEST_FIXTURE_SUBPROCESS` if any test uses pytest fixtures or `@pytest.mark`.
            failures: list[str] = []
            ran_count = 0
            for tf_s in tf_strs:
                tf_p = pathlib.Path(tf_s)
                src = tf_p.read_text(encoding="utf-8", errors="replace")
                if "@pytest.mark" in src or "@pytest.fixture" in src:
                    raise RuntimeError("NEEDS_PYTEST_FIXTURE_SUBPROCESS")
                ns: dict[str, Any] = {"__name__": "__zygote_suite__", "__file__": tf_s}
                exec(compile(src, tf_s, "exec"), ns)
                for attr, fn_obj in list(ns.items()):
                    if attr.startswith("test_") and callable(fn_obj):
                        sig = inspect.signature(fn_obj)
                        if any(p.default is inspect.Parameter.empty for p in sig.parameters.values()):
                            raise RuntimeError("NEEDS_PYTEST_FIXTURE_SUBPROCESS")
                        ran_count += 1
                        try:
                            fn_obj()
                        except BaseException:
                            rel_tf = tf_p.relative_to(repo_str).as_posix()
                            failures.append(f"FAILED {rel_tf}::{attr}\n{traceback.format_exc()}")
            if ran_count == 0:
                raise RuntimeError("NO_DIRECT_TESTS_FOUND")
            return {"suite_ok": len(failures) == 0, "output": "\n".join(failures)[-6000:]}

        try:
            z_res = zygote.run_isolated(_zygote_pytest_runner, timeout_s=timeout)
            if "suite_ok" in z_res:
                return bool(z_res["suite_ok"]), str(z_res.get("output") or "")
        except Exception:
            pass

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    py_entries = [str(repo_root)]
    if (repo_root / "src").is_dir():
        py_entries.insert(0, str(repo_root / "src"))
    if env.get("PYTHONPATH"):
        py_entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py_entries)

    combined_out: list[str] = []
    if has_pytest_style:
        cmd = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short"] + [str(tf) for tf in test_files]
        proc = subprocess.run(cmd, cwd=str(repo_root), env=env, capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0, ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-6000:]

    for tf in test_files:
        proc = subprocess.run([sys.executable, "-B", str(tf)], cwd=str(repo_root), env=env, capture_output=True, text=True, timeout=timeout)
        combined_out.append((proc.stdout or "") + "\n" + (proc.stderr or ""))
        if proc.returncode != 0:
            return False, "\n".join(combined_out)[-6000:]
    return True, "\n".join(combined_out)[-6000:]


def _dynamic_spectrum_and_provenance_boost(
    cow_root: pathlib.Path,
    all_non_test_py: Sequence[str],
    test_files: Sequence[pathlib.Path],
) -> tuple[list[str], dict[str, list[int]]]:
    """Use `python_dynamic_fault_localizer_v1` + `python_interprocedural_value_provenance_v1` when static traces lack line focus."""
    ranked_rels: list[str] = []
    focus_map: dict[str, list[int]] = {}
    saved_sys_path = list(sys.path)
    saved_modules = dict(sys.modules)
    try:
        from canonical.runtime.bound_capabilities import (
            python_dynamic_fault_localizer_v1 as dyn_loc,
            python_interprocedural_value_provenance_v1 as val_prov,
        )

        dyn_out = dyn_loc.run(
            {
                "source_root": ".",
                "test_paths": [tf.relative_to(cow_root).as_posix() for tf in test_files[:6]],
                "output_path": ".brain_dyn_loc.json",
            },
            cow_root,
        )
        for item in (dyn_out.get("suspects") or dyn_out.get("ranked_lines") or [])[:8]:
            if isinstance(item, Mapping):
                rp = str(item.get("file") or item.get("rel_path") or item.get("path") or "")
                ln = int(item.get("line") or item.get("lineno") or 0)
                if rp in all_non_test_py:
                    if rp not in ranked_rels:
                        ranked_rels.append(rp)
                    if ln > 0 and ln not in focus_map.setdefault(rp, []):
                        focus_map[rp].append(ln)

        prov_out = val_prov.run(
            {"source_root": ".", "output_path": ".brain_val_prov.json"},
            cow_root,
        )
        for edge in (prov_out.get("edges") or prov_out.get("producers") or [])[:8]:
            if isinstance(edge, Mapping):
                rp = str(edge.get("producer_file") or edge.get("file") or "")
                if rp in all_non_test_py and rp not in ranked_rels:
                    ranked_rels.append(rp)
    except Exception:
        pass
    finally:
        sys.path[:] = saved_sys_path
        for k in list(sys.modules):
            if k not in saved_modules:
                sys.modules.pop(k, None)
        sys.modules.update(saved_modules)
        for tmp in (".brain_dyn_loc.json", ".brain_val_prov.json"):
            tp = cow_root / tmp
            if tp.exists():
                tp.unlink()
    return ranked_rels, focus_map


def bisect_git_regression_in_cow(
    repo_root: str | pathlib.Path,
    test_command: str | Sequence[str],
    *,
    good_rev: str | None = None,
    bad_rev: str = "HEAD",
) -> dict[str, Any]:
    """Run `git_bisect_regression` inside an isolated temporary clone without mutating `repo_root`'s HEAD."""
    from canonical.runtime.bound_capabilities import git_bisect_regression

    src = pathlib.Path(repo_root).resolve()
    with tempfile.TemporaryDirectory(prefix="brain-cow-bisect-") as td:
        clone_dir = pathlib.Path(td) / "repo"
        shutil.copytree(src, clone_dir, symlinks=True)
        args: dict[str, Any] = {
            "repo_path": ".",
            "bad_rev": bad_rev,
            "test_cmd": list(test_command) if isinstance(test_command, (list, tuple)) else str(test_command),
            "output_path": ".brain_bisect_out.json",
        }
        if good_rev:
            args["good_rev"] = good_rev
        out = dict(git_bisect_regression.run(args, clone_dir))
        out["k3_external_llm_calls"] = 0
        return out


def repair_repository_in_cow_zygote(
    workspace_root: str | pathlib.Path,
    *,
    skill_store: VerifiedSkillStore | None = None,
    zygote: ZygotePrewarmedPool | None = None,
    apply_to_workspace: bool = False,
    max_candidates: int = 64,
    max_rounds: int = 3,
) -> dict[str, Any]:
    """Autonomously localize, synthesize (recall / STUN / coupled / multi-round), and verify in CoW + Zygote."""
    t_total = time.perf_counter_ns()
    ws = pathlib.Path(workspace_root).resolve()
    store = skill_store or VerifiedSkillStore()
    pool = zygote or ZygotePrewarmedPool()

    with tempfile.TemporaryDirectory(prefix="brain-cow-repair-") as td:
        cow_root = pathlib.Path(td) / "repo"
        clone_stats = create_zero_copy_cow_workspace(ws, cow_root)

        test_files = sorted(
            p for p in cow_root.rglob("test_*.py")
            if not any(part in _IGNORED_DIRS for part in p.parts)
        )
        if not test_files:
            return {"schema": SCHEMA, "pass": True, "status": "NO_TESTS_FOUND", "clone": clone_stats}

        ok_base, fail_trace = _run_disk_suite_check(cow_root, test_files, zygote=pool)
        if ok_base:
            return {"schema": SCHEMA, "pass": True, "status": "ALREADY_GREEN", "clone": clone_stats}

        initial_origins: dict[str, str] = {}
        cumulative_patch: dict[str, str] = {}
        crystallized_ids: list[str] = []
        round_modes: list[str] = []
        total_evaluated = 0
        total_zygote_ms = 0.0
        last_impact_info: dict[str, Any] = {"slice_ms": 0.0, "selected_count": len(test_files), "total_tests": len(test_files)}

        all_non_test_py = [
            p.relative_to(cow_root).as_posix()
            for p in sorted(cow_root.rglob("*.py"))
            if not any(part in _IGNORED_DIRS for part in p.parts)
            and not p.name.startswith("test_")
            and not p.name.endswith("_test.py")
            and "testing/" not in p.relative_to(cow_root).as_posix()
            and "tests/" not in p.relative_to(cow_root).as_posix()
        ]

        for round_idx in range(max(1, int(max_rounds))):
            trace_cited_rels = [rp for rp in all_non_test_py if _extract_focus_lines(fail_trace, rp)]
            if len(trace_cited_rels) >= 1 and store.lookup_rules("python"):
                # Fast Tier-0 `SKILL_RECALL` check directly on traceback-cited files before full AST localization!
                localized = [{"rel": rp, "symbols": []} for rp in trace_cited_rels[:2]]
            else:
                localized = list(
                    coupled_loop._localize(cow_root, cow_root, test_files, fail_trace, max_files=8, max_symbols=6)
                )
            dyn_focus_map: dict[str, list[int]] = {}
            if not trace_cited_rels:
                dyn_rels, dyn_focus_map = _dynamic_spectrum_and_provenance_boost(cow_root, all_non_test_py, test_files)
                trace_cited_rels = dyn_rels

            if trace_cited_rels:
                by_rel = {str(r["rel"]): r for r in localized}
                promoted: list[dict[str, Any]] = []
                for rp in trace_cited_rels:
                    promoted.append(by_rel.pop(rp, {"rel": rp, "symbols": []}))
                localized = promoted + [r for r in localized if str(r["rel"]) in by_rel]
            if not localized:
                return {"schema": SCHEMA, "pass": False, "status": "NO_SOURCE_CANDIDATES_LOCALIZED", "failure_trace": fail_trace}

            changed_rels = [str(row["rel"]) for row in localized[:2]]
            if len(test_files) <= 2:
                impact_info = {
                    "selected_tests": list(test_files),
                    "selected_count": len(test_files),
                    "total_tests": len(test_files),
                    "used_tree_sitter": False,
                    "slice_ms": 0.0,
                }
            else:
                impact_info = select_impacted_tests_fast(cow_root, changed_rels, test_files)
            last_impact_info = impact_info

            # Identify explicitly failing test files in `fail_trace` so multi-round sequential faults
            # can repair Fault #1 even when an independent test file still fails on Fault #2!
            explicitly_failing_tests = [
                tf for tf in test_files
                if f"FAILED {tf.relative_to(cow_root).as_posix()}" in fail_trace
                or f"{tf.relative_to(cow_root).as_posix()}:" in fail_trace
                or f"{tf.name}:" in fail_trace
            ]
            if explicitly_failing_tests and len(test_files) > 1 and max_rounds > 1:
                round_target_tests = explicitly_failing_tests
            else:
                impacted_set = list(impact_info["selected_tests"])
                for tf in test_files:
                    tf_rel = tf.relative_to(cow_root).as_posix()
                    if (tf_rel in fail_trace or tf.name in fail_trace) and tf not in impacted_set:
                        impacted_set.insert(0, tf)
                round_target_tests = impacted_set

            test_sources = [tf.read_text(encoding="utf-8", errors="replace") for tf in round_target_tests]

            # Tier-0 Fast Path: Test `SKILL_RECALL` proposals FIRST before generating 60 STUN/AST/coupled candidates!
            recall_candidates: list[dict[str, str]] = []
            recall_modes: list[str] = []
            misfired_recall_meta: list[tuple[str, str, str]] = []
            for row in localized[:2]:
                rel_p = str(row["rel"])
                orig_src = (cow_root / rel_p).read_text(encoding="utf-8")
                for lang_rule in store.lookup_rules("python"):
                    if lang_rule.get("state") == "INVALIDATED":
                        continue
                    sid_tag = str(lang_rule.get("skill_id") or "")
                    rule_cands = _iter_file_or_method_rule_candidates(orig_src, lang_rule, limit=6)
                    added_for_rule = False
                    for r_cand in rule_cands:
                        if r_cand and r_cand != orig_src:
                            recall_candidates.append({rel_p: r_cand})
                            recall_modes.append(f"SKILL_RECALL:{sid_tag}")
                            added_for_rule = True
                    if added_for_rule and sid_tag:
                        misfired_recall_meta.append((sid_tag, rel_p, orig_src))

            eval_res: dict[str, Any] = {"found": False}
            patch_candidates: list[dict[str, str]] = []
            candidate_modes: list[str] = []
            scope_refinements: list[dict[str, Any]] = []
            if recall_candidates:
                eval_res = evaluate_patch_batch_in_cow_zygote(
                    cow_root,
                    recall_candidates[:max_candidates],
                    round_target_tests,
                    zygote=pool,
                )
                total_evaluated += int(eval_res.get("candidates_evaluated", 0))
                total_zygote_ms += float(eval_res.get("worker_eval_ms", 0.0))
                if eval_res.get("found"):
                    patch_candidates = recall_candidates[:max_candidates]
                    candidate_modes = recall_modes[:max_candidates]
                elif misfired_recall_meta:
                    # Counterexample-driven rule scope refinement (`rule_scope_learning_v1` / `finite_capability_diagnosis`):
                    # Recalled rule(s) matched structurally on `orig_src` yet EVERY produced candidate failed the target test slice!
                    seen_misfired: set[tuple[str, str]] = set()
                    for sid_tag, misfire_rel, misfire_orig in misfired_recall_meta:
                        if (sid_tag, misfire_rel) in seen_misfired:
                            continue
                        seen_misfired.add((sid_tag, misfire_rel))
                        try:
                            def _verify_rule_cand(cand_txt: str, _rel: str = misfire_rel) -> bool:
                                r_chk = evaluate_patch_batch_in_cow_zygote(
                                    cow_root,
                                    [{_rel: cand_txt}],
                                    round_target_tests,
                                    zygote=pool,
                                )
                                return bool(r_chk.get("found"))

                            ref_rep = store.refine_scope_from_counterexample(
                                sid_tag,
                                {
                                    "label": f"counterexample:{misfire_rel}",
                                    "language": "python",
                                    "source_text": misfire_orig,
                                },
                                verifier=_verify_rule_cand,
                            )
                            scope_refinements.append({"skill_id": sid_tag, "file": misfire_rel, **ref_rep})
                        except Exception:
                            pass

            if not eval_res.get("found"):
                # Cold path: run full localization if skipped earlier + STUN + Whitebox Live-Trace/Dual-Span/Guard + AST + Coupled synthesis
                if len(localized) < 2 and len(all_non_test_py) > 1:
                    full_loc = list(
                        coupled_loop._localize(cow_root, cow_root, test_files, fail_trace, max_files=8, max_symbols=6)
                    )
                    seen_rels = {str(r["rel"]) for r in localized}
                    localized = localized + [r for r in full_loc if str(r["rel"]) not in seen_rels]
                    if len(localized) < 2:
                        try:
                            from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as mrs

                            diff_loc = mrs.localize_faults_by_differential_trace(
                                cow_root,
                                test_files=[str(tf.relative_to(cow_root)) for tf in round_target_tests],
                                timeout=4.0,
                            )
                            for d_item in diff_loc.get("ranked_files") or diff_loc.get("suspect_files") or []:
                                d_rel = str(d_item.get("file") if isinstance(d_item, Mapping) else d_item)
                                if d_rel and d_rel not in seen_rels and (cow_root / d_rel).is_file():
                                    localized.append({"rel": d_rel, "score": 1.0})
                                    seen_rels.add(d_rel)
                        except Exception:
                            pass

                try:
                    from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as wb_synth
                except Exception:
                    wb_synth = None  # type: ignore[assignment]

                per_file_pools: list[tuple[str, list[str]]] = []
                for row in localized[:2]:
                    rel_p = str(row["rel"])
                    orig_src = (cow_root / rel_p).read_text(encoding="utf-8")
                    seen_file_cands: set[str] = {orig_src}
                    stun_cands = propose_stun_and_guard_repairs(orig_src, test_sources, max_candidates=12)
                    for sc in stun_cands:
                        if sc not in seen_file_cands:
                            seen_file_cands.add(sc)
                            patch_candidates.append({rel_p: sc})
                            candidate_modes.append("STUN_OR_GUARD_SYNTHESIS")

                    wb_cands: list[str] = []
                    if wb_synth is not None:
                        try:
                            for wc in wb_synth.synthesize_candidates_for_file(
                                cow_root / rel_p,
                                cow_root,
                                round_target_tests,
                            )[:12]:
                                if wc and wc not in seen_file_cands:
                                    seen_file_cands.add(wc)
                                    wb_cands.append(wc)
                                    patch_candidates.append({rel_p: wc})
                                    candidate_modes.append("WHITEBOX_TRACE_AND_DUAL_SYNTHESIS")
                        except Exception:
                            pass

                    focus_lns = _extract_focus_lines(fail_trace, rel_p) or dyn_focus_map.get(rel_p, [])
                    ast_cands = _single_file_ast_mutations(orig_src, max_candidates=20, focus_lines=focus_lns)
                    for ac in ast_cands:
                        if ac not in seen_file_cands:
                            seen_file_cands.add(ac)
                            patch_candidates.append({rel_p: ac})
                            candidate_modes.append("SINGLE_FILE_AST")

                    file_pool = (stun_cands + wb_cands + ast_cands)[:8]
                    if file_pool:
                        per_file_pools.append((rel_p, file_pool))

                if len(per_file_pools) >= 2:
                    (rel_a, pool_a), (rel_b, pool_b) = per_file_pools[0], per_file_pools[1]
                    for ca, cb in itertools.islice(itertools.product(pool_a, pool_b), max(8, max_candidates - len(patch_candidates))):
                        patch_candidates.append({rel_a: ca, rel_b: cb})
                        candidate_modes.append("COUPLED_MULTIFILE_SYNTHESIS")

                patch_candidates = patch_candidates[:max_candidates]
                if not patch_candidates:
                    return {"schema": SCHEMA, "pass": False, "status": "NO_CANDIDATES_GENERATED", "rounds_completed": round_idx}

                eval_res = evaluate_patch_batch_in_cow_zygote(
                    cow_root,
                    patch_candidates,
                    round_target_tests,
                    zygote=pool,
                )
                total_evaluated += int(eval_res.get("candidates_evaluated", 0))
                total_zygote_ms += float(eval_res.get("worker_eval_ms", 0.0))

            if not eval_res.get("found"):
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "EXHAUSTED_CANDIDATE_BUDGET",
                    "rounds_completed": round_idx,
                    "candidates_evaluated": total_evaluated,
                    "zygote_eval_ms": round(total_zygote_ms, 3),
                    "clone": clone_stats,
                    "impact": {k: v for k, v in last_impact_info.items() if k != "selected_tests"},
                }

            win_idx = int(eval_res["winning_index"])
            winning_patch = patch_candidates[win_idx]
            win_mode = candidate_modes[win_idx]
            round_modes.append(win_mode)

            for rel_p, new_src in winning_patch.items():
                before_text = (cow_root / rel_p).read_text(encoding="utf-8")
                initial_origins.setdefault(rel_p, before_text)
                cow_write_text(cow_root / rel_p, new_src)
                cumulative_patch[rel_p] = new_src

            full_ok, full_out = _run_disk_suite_check(cow_root, test_files, zygote=pool)
            if full_ok:
                # Full repository test suite is 100% GREEN! Crystallize every repaired file's lesson,
                # record `rule_expiry_v1` freshness fingerprint, compile 7-language CST skeleton,
                # and emit `recursive_abstraction_v5` canonical signature digest!
                from canonical.runtime import recursive_abstraction_v5 as rec_abs
                from canonical.swe_kernel import rule_expiry_v1 as rule_exp
                from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
                    compile_rule_to_cst_skeleton,
                )

                cst_skeletons_compiled = 0
                abstraction_digests: list[str] = []
                rules_by_id = {str(r.get("skill_id")): r for r in store.lookup_rules("python")}
                for rel_p, new_src in cumulative_patch.items():
                    old_src = initial_origins[rel_p]
                    cryst = store.crystallize_code_fix(
                        before_snippet=old_src,
                        after_snippet=new_src,
                        language="python",
                        error_class=round_modes[-1],
                    )
                    if not cryst.get("crystallized"):
                        mpair = _extract_changed_method_pair(old_src, new_src)
                        if mpair is not None:
                            cryst = store.crystallize_code_fix(
                                before_snippet=mpair[0],
                                after_snippet=mpair[1],
                                language="python",
                                error_class=round_modes[-1],
                            )
                    if cryst.get("crystallized") and cryst.get("skill_id"):
                        sid = str(cryst["skill_id"])
                        crystallized_ids.append(sid)
                        try:
                            rule_exp.record_taught(store.db_path, sid)
                        except Exception:
                            pass
                        rule_row = rules_by_id.get(sid) or next(
                            (r for r in store.lookup_rules("python") if str(r.get("skill_id")) == sid),
                            None,
                        )
                        if rule_row is not None:
                            sk = compile_rule_to_cst_skeleton(rule_row)
                            if sk is not None:
                                cst_skeletons_compiled += 1
                        try:
                            abstraction_digests.append(
                                rec_abs.signature_digest([round_modes[-1], sid])
                            )
                        except Exception:
                            pass

                if apply_to_workspace:
                    for rel_p, new_src in cumulative_patch.items():
                        (ws / rel_p).write_text(new_src, encoding="utf-8")

                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__COW_ZYGOTE_REPAIRED_AND_VERIFIED",
                    "mode": round_modes[0] if len(round_modes) == 1 else "+".join(round_modes),
                    "rounds_used": round_idx + 1,
                    "round_modes": round_modes,
                    "files_repaired": sorted(cumulative_patch.keys()),
                    "crystallized_skill_ids": crystallized_ids,
                    "scope_refinements": scope_refinements,
                    "cst_skeletons_compiled": cst_skeletons_compiled,
                    "abstraction_signature_digests": abstraction_digests,
                    "candidates_evaluated": total_evaluated,
                    "zygote_eval_ms": round(total_zygote_ms, 3),
                    "clone_ms": clone_stats["clone_ms"],
                    "impact_slice_ms": last_impact_info["slice_ms"],
                    "impacted_test_count": last_impact_info["selected_count"],
                    "total_test_count": last_impact_info["total_tests"],
                    "total_elapsed_ms": round((time.perf_counter_ns() - t_total) / 1e6, 3),
                    "k3_external_llm_calls": 0,
                }

            # Suite still red: check whether `round_target_tests` genuinely stayed green & new fault emerged!
            still_ok_round, _ = _run_disk_suite_check(cow_root, round_target_tests, zygote=pool)
            if not still_ok_round or round_idx + 1 >= max(1, int(max_rounds)):
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "FAILED_FULL_SUITE_CONFIRMATION",
                    "rounds_completed": round_idx + 1,
                    "full_suite_output": full_out,
                }
            # Advance to Round `round_idx + 2` with the newly uncovered failure traceback!
            fail_trace = full_out

        return {"schema": SCHEMA, "pass": False, "status": "MAX_ROUNDS_EXHAUSTED"}
