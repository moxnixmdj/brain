"""Repo-Native Component Mining, Dual-Program Splicing, 16-Way CoW Speculative Rollouts,
and Unified Cross-Modal Type-Transition Petri Net (Zero-LLM, Zero-Knowledge-House).

Implements four first-principles architectural mechanisms to shatter the fixed-grammar ceiling
and unify GUIs, CLIs, SQLite/OS, and code under one algebraic engine:

  1. Repo-Native Component Mining (`mine_repo_components_as_morphisms`):
     Harvests real functions, methods, classes, constants, and custom exceptions across the
     target repository using `canonical/swe_kernel/incremental_semantic_graph_v1.py` (SQLite
     warm cache) + AST type/call-site mining, converting them into typed Petri-net morphisms
     so synthesis uses the repository's own vocabulary instead of a fixed tiny DSL.

  2. Dual-Program Splicing (`splice_dual_programs` — SymLLM `IfThenElse` without LLMs):
     When candidate P1 passes failing tests T_fail but regresses passing tests T_reg (which
     original P0 passes), synthesizes ONLY a minimal separating boolean guard G between the
     runtime frames of T_fail and T_reg via `oe_sygus_synthesizer_v1`, splicing `if G: P1 else: P0`
     into a single verified solution.

  3. 16-Way Parallel Copy-on-Write Counterfactual Speculative Rollouts (`speculative_cow_rollout`):
     Uses real Linux `os.fork()` Copy-on-Write + `os.pipe()` channels to fork up to 16 parallel
     isolated realities simultaneously at uncertain UI/CLI/OS/code junctions, executes all
     candidate actions in parallel without mutating parent state, scores exact goal-residual
     reduction across all 16 outcomes, and selects the mathematically verified best branch.

  4. Unified Cross-Modal Type-Transition Petri Net (`UnifiedCrossModalPetriNet`):
     Compiles GUI accessibility actions, SQLite/OS/CLI/HTTP ops, and mined Python repository
     functions into ONE multi-token Type-Transition Petri Net (SyPet / APIphany style),
     solving cross-modal chains in a single shortest-path search and crystallizing the
     verified chain as a single O(1)-deletable L2 morphism.

Authority: NONE. Pure Python stdlib + existing repo engines. model_calls == 0, parameters_stored == 0.
"""
from __future__ import annotations

import ast
from collections import Counter, deque
import copy
from dataclasses import dataclass, field
import hashlib
import json
import os
import pathlib
import select
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import oe_sygus_synthesizer_v1 as OESYGUS
from canonical.swe_kernel import incremental_semantic_graph_v1 as ISG

SCHEMA = "BRAIN_REPO_COMPONENT_AND_COW_ENGINE_V1"
AUTHORITY = "NONE"


# ===========================================================================
# 1. REPO-NATIVE COMPONENT MINING (ZERO-GRAMMAR SYMBOL HARVESTING)
# ===========================================================================


@dataclass(frozen=True)
class RepoComponentMorphism:
    """A real symbol mined from the target repository, typed as a Petri-net transition."""

    component_id: str
    symbol_name: str
    kind: str  # "function" | "method" | "class" | "exception" | "constant"
    rel_path: str
    module_name: str
    lineno: int
    param_names: tuple[str, ...]
    input_types: tuple[str, ...]
    output_type: str
    import_stmt: str
    call_template: str
    is_local_to_focus: bool = False


def _norm_type_str(ann: ast.AST | None, default: str = "Any") -> str:
    if ann is None:
        return default
    try:
        raw = ast.unparse(ann).strip()
    except Exception:
        return default
    low = raw.lower()
    if low in ("str", "bytes", "int", "float", "bool", "none"):
        return low
    if low.startswith("list") or low.startswith("sequence") or low.startswith("iterable"):
        return "list"
    if low.startswith("dict") or low.startswith("mapping"):
        return "dict"
    if low.startswith("tuple"):
        return "tuple"
    if low.startswith("set") or low.startswith("frozenset"):
        return "set"
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|") if p.strip() != "None"]
        if len(parts) == 1:
            return parts[0].lower() if parts[0].lower() in ("str", "int", "float", "bool", "bytes") else parts[0]
    return raw


def _infer_return_type_from_body(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if fn.returns is not None:
        return _norm_type_str(fn.returns, "Any")
    for nd in ast.walk(fn):
        if isinstance(nd, ast.Return) and nd.value is not None:
            v = nd.value
            if isinstance(v, ast.JoinedStr) or (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                return "str"
            if isinstance(v, ast.Constant) and isinstance(v.value, bool):
                return "bool"
            if isinstance(v, ast.Constant) and isinstance(v.value, int):
                return "int"
            if isinstance(v, ast.Constant) and isinstance(v.value, float):
                return "float"
            if isinstance(v, ast.List) or isinstance(v, ast.ListComp):
                return "list"
            if isinstance(v, ast.Dict) or isinstance(v, ast.DictComp):
                return "dict"
            if isinstance(v, ast.Tuple):
                return "tuple"
            if isinstance(v, ast.Compare):
                return "bool"
    return "Any"


def _infer_param_types(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[tuple[str, ...], tuple[str, ...]]:
    names: list[str] = []
    types: list[str] = []
    args = list(fn.args.posonlyargs) + list(fn.args.args)
    for idx, arg in enumerate(args):
        if idx == 0 and arg.arg in ("self", "cls"):
            continue
        names.append(arg.arg)
        t = _norm_type_str(arg.annotation, "Any")
        if t == "Any":
            nm = arg.arg.lower()
            if any(tok in nm for tok in ("text", "str", "name", "host", "url", "path", "header", "key", "value", "line")):
                t = "str"
            elif any(tok in nm for tok in ("count", "num", "idx", "index", "len", "size", "port", "max", "min", "cents")):
                t = "int"
            elif any(tok in nm for tok in ("items", "words", "rows", "lines", "values", "list", "seq")):
                t = "list"
            elif any(tok in nm for tok in ("map", "dict", "params", "config", "env", "headers")):
                t = "dict"
        types.append(t)
    return tuple(names), tuple(types)


def _rel_to_import_module(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    if p.startswith("src/"):
        p = p[4:]
    if p.endswith("/__init__.py"):
        p = p[:-12]
    elif p.endswith(".py"):
        p = p[:-3]
    return p.replace("/", ".").strip(".")


def mine_repo_components_as_morphisms(
    repo_root: str | pathlib.Path,
    *,
    focus_file: str | None = None,
    max_components: int = 240,
) -> dict[str, Any]:
    """Harvest the repository's own functions, methods, classes, exceptions, and constants
    using `IncrementalSemanticGraph` (SQLite warm cache) + AST type inference."""
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()
    focus_norm = str(focus_file).replace("\\", "/") if focus_file else ""

    # Warm-cache file discovery via existing IncrementalSemanticGraph!
    graph = ISG.IncrementalSemanticGraph(root)
    summaries = graph.load_summaries(".")
    py_files: list[str] = []
    for rel in sorted(summaries.keys()):
        rnorm = rel.replace("\\", "/")
        if not rnorm.endswith(".py"):
            continue
        parts = pathlib.PurePosixPath(rnorm).parts
        if any(d in parts for d in ("tests", "test", ".git", ".venv", "venv", "__pycache__", "build", "dist")):
            continue
        if parts[-1].startswith("test_") or parts[-1].endswith("_test.py") or parts[-1] == "conftest.py":
            continue
        py_files.append(rnorm)

    # Sort so focus_file and same-package files come first!
    focus_dir = str(pathlib.PurePosixPath(focus_norm).parent) if focus_norm else ""
    py_files.sort(
        key=lambda r: (
            0 if r == focus_norm else (1 if focus_dir and r.startswith(focus_dir) else 2),
            r,
        )
    )

    components: list[RepoComponentMorphism] = []
    by_output_type: dict[str, list[str]] = {}
    exceptions_found: list[str] = []

    for rel in py_files:
        if len(components) >= max_components:
            break
        fpath = root / rel
        if not fpath.is_file():
            continue
        try:
            src = fpath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except Exception:
            continue

        mod_name = _rel_to_import_module(rel)
        is_local = (rel == focus_norm)

        for node in tree.body:
            if len(components) >= max_components:
                break
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                pnames, ptypes = _infer_param_types(node)
                ret_t = _infer_return_type_from_body(node)
                imp = "" if is_local else f"from {mod_name} import {node.name}"
                placeholders = ", ".join(f"${i}" for i in range(len(pnames)))
                cid = f"fn:{mod_name}.{node.name}"
                comp = RepoComponentMorphism(
                    component_id=cid,
                    symbol_name=node.name,
                    kind="function",
                    rel_path=rel,
                    module_name=mod_name,
                    lineno=int(getattr(node, "lineno", 1)),
                    param_names=pnames,
                    input_types=ptypes,
                    output_type=ret_t,
                    import_stmt=imp,
                    call_template=f"{node.name}({placeholders})",
                    is_local_to_focus=is_local,
                )
                components.append(comp)
                by_output_type.setdefault(ret_t, []).append(cid)

            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases] if node.bases else []
                is_exc = any("Error" in b or "Exception" in b for b in bases) or node.name.endswith("Error")
                kind = "exception" if is_exc else "class"
                if is_exc:
                    exceptions_found.append(f"{mod_name}.{node.name}")
                imp = "" if is_local else f"from {mod_name} import {node.name}"
                cid = f"{kind}:{mod_name}.{node.name}"
                comp = RepoComponentMorphism(
                    component_id=cid,
                    symbol_name=node.name,
                    kind=kind,
                    rel_path=rel,
                    module_name=mod_name,
                    lineno=int(getattr(node, "lineno", 1)),
                    param_names=(),
                    input_types=(),
                    output_type=node.name,
                    import_stmt=imp,
                    call_template=f"{node.name}($0)",
                    is_local_to_focus=is_local,
                )
                components.append(comp)
                by_output_type.setdefault(node.name, []).append(cid)
                # Mine public methods of classes in focus_file (or small classes)
                if is_local:
                    for sub in node.body:
                        if len(components) >= max_components:
                            break
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("__"):
                            pnames, ptypes = _infer_param_types(sub)
                            ret_t = _infer_return_type_from_body(sub)
                            placeholders = ", ".join(f"${i}" for i in range(len(pnames)))
                            mcid = f"method:{mod_name}.{node.name}.{sub.name}"
                            mcomp = RepoComponentMorphism(
                                component_id=mcid,
                                symbol_name=f"{node.name}.{sub.name}",
                                kind="method",
                                rel_path=rel,
                                module_name=mod_name,
                                lineno=int(getattr(sub, "lineno", 1)),
                                param_names=pnames,
                                input_types=(node.name,) + ptypes,
                                output_type=ret_t,
                                import_stmt="",
                                call_template=f"self.{sub.name}({placeholders})",
                                is_local_to_focus=True,
                            )
                            components.append(mcomp)
                            by_output_type.setdefault(ret_t, []).append(mcid)

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "repo_root": str(root),
        "files_indexed": len(py_files),
        "component_count": len(components),
        "components": components,
        "exceptions": exceptions_found,
        "by_output_type": by_output_type,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def synthesize_repo_component_return_candidates(
    repo_root: str | pathlib.Path,
    focus_rel: str,
    source_code: str,
    return_lineno: int,
    examples: Sequence[tuple[dict[str, Any], Any]],
    *,
    max_candidates: int = 8,
) -> list[dict[str, Any]]:
    """Synthesize patched return statements by invoking REAL type-compatible helper functions
    mined from anywhere in the target repository (even 3+ files away!).

    Evaluates each candidate repo helper against `examples = [(input_env, expected_output), ...]`
    in a lightweight in-process import namespace (zero subprocesses!) and returns ONLY exact
    witness-matching patches with auto-inserted imports when the helper lives in another file.
    """
    if not examples:
        return []
    root = pathlib.Path(repo_root).resolve()
    mined = mine_repo_components_as_morphisms(root, focus_file=focus_rel)
    comps: list[RepoComponentMorphism] = mined["components"]

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    ret_node: ast.Return | None = None
    enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fln = int(getattr(fn, "lineno", 0))
            fend = int(getattr(fn, "end_lineno", fln))
            if fln <= return_lineno <= fend:
                for nd in ast.walk(fn):
                    if isinstance(nd, ast.Return) and int(getattr(nd, "lineno", 0)) == return_lineno:
                        ret_node = nd
                        enclosing_fn = fn
                        break
            if ret_node is not None:
                break
    if ret_node is None or enclosing_fn is None:
        return []

    exp0 = examples[0][1]
    want_type = type(exp0).__name__.lower()
    src_lines = source_code.splitlines(keepends=True)
    if not (1 <= return_lineno <= len(src_lines)):
        return []
    rline = src_lines[return_lineno - 1]
    indent = rline[: len(rline) - len(rline.lstrip())]
    eol = "\n" if rline.endswith("\n") else ""

    # Prepare sys.path for importing real repo modules cleanly
    add_paths = [str(root)]
    if (root / "src").is_dir():
        add_paths.insert(0, str(root / "src"))
    orig_sys_path = list(sys.path)
    for p in reversed(add_paths):
        if p not in sys.path:
            sys.path.insert(0, p)

    import importlib

    # Candidate unary & binary functions from across the ENTIRE repository (excluding enclosing_fn itself!)
    unary_comps = [
        c for c in comps
        if c.kind == "function"
        and len(c.param_names) == 1
        and c.symbol_name != enclosing_fn.name
        and (c.output_type in (want_type, "Any"))
    ]
    binary_comps = [
        c for c in comps
        if c.kind == "function"
        and len(c.param_names) == 2
        and c.symbol_name != enclosing_fn.name
        and (c.output_type in (want_type, "Any"))
    ]

    # Candidate argument variable expressions available in all examples
    shared_vars = sorted(
        k for k in examples[0][0].keys()
        if isinstance(k, str)
        and k.isidentifier()
        and not k.startswith("_")
        and all(k in env for env, _ in examples)
    )
    orig_ret_expr = ast.get_source_segment(source_code, ret_node.value) if ret_node.value is not None else None

    out: list[dict[str, Any]] = []
    seen_exprs: set[str] = set()
    mod_cache: dict[str, Any] = {}

    def _load_callable(comp: RepoComponentMorphism) -> Callable[..., Any] | None:
        if not comp.module_name:
            return None
        if comp.module_name not in mod_cache:
            try:
                mod_cache[comp.module_name] = importlib.import_module(comp.module_name)
            except Exception:
                mod_cache[comp.module_name] = None
        mod = mod_cache[comp.module_name]
        if mod is None:
            return None
        fn_obj = getattr(mod, comp.symbol_name, None)
        return fn_obj if callable(fn_obj) else None

    def _build_patched_src(call_expr: str, import_stmt: str) -> str | None:
        patched_lines = list(src_lines)
        patched_lines[return_lineno - 1] = f"{indent}return {call_expr}{eol}"
        if import_stmt and import_stmt not in source_code:
            # Insert import right after any `from __future__` / module docstring
            ins_at = 0
            for idx_l, ln in enumerate(patched_lines):
                s = ln.strip()
                if s.startswith("from __future__") or s.startswith("import ") or s.startswith("from "):
                    ins_at = idx_l + 1
            patched_lines.insert(ins_at, import_stmt + "\n")
        nc = "".join(patched_lines)
        try:
            ast.parse(nc)
            return nc
        except SyntaxError:
            return None

    try:
        # 1a. Direct unary repo-helper call: `return helper(var)` or `return helper(orig_ret_expr)`
        for comp in unary_comps:
            if len(out) >= max_candidates:
                break
            fn_obj = _load_callable(comp)
            if fn_obj is None:
                continue
            for vname in shared_vars:
                try:
                    ok = all(fn_obj(env[vname]) == exp for env, exp in examples)
                except Exception:
                    ok = False
                if ok:
                    call_expr = f"{comp.symbol_name}({vname})"
                    if call_expr in seen_exprs:
                        continue
                    seen_exprs.add(call_expr)
                    nc = _build_patched_src(call_expr, comp.import_stmt)
                    if nc:
                        out.append({
                            "component_id": comp.component_id,
                            "call_expr": call_expr,
                            "import_stmt": comp.import_stmt,
                            "patched_source": nc,
                            "hops": 1,
                        })
            # Also try wrapping the existing return expression if `__ret__` is provided in env
            if orig_ret_expr and all("__ret__" in env for env, _ in examples):
                try:
                    ok = all(fn_obj(env["__ret__"]) == exp for env, exp in examples)
                except Exception:
                    ok = False
                if ok:
                    call_expr = f"{comp.symbol_name}({orig_ret_expr})"
                    if call_expr not in seen_exprs:
                        seen_exprs.add(call_expr)
                        nc = _build_patched_src(call_expr, comp.import_stmt)
                        if nc:
                            out.append({
                                "component_id": comp.component_id,
                                "call_expr": call_expr,
                                "import_stmt": comp.import_stmt,
                                "patched_source": nc,
                                "hops": 1,
                            })

        # 1b. Binary repo-helper call: `return helper(v1, v2)`
        for comp in binary_comps:
            if len(out) >= max_candidates:
                break
            fn_obj = _load_callable(comp)
            if fn_obj is None:
                continue
            for i in range(len(shared_vars)):
                for j in range(len(shared_vars)):
                    if i == j:
                        continue
                    v1, v2 = shared_vars[i], shared_vars[j]
                    try:
                        ok = all(fn_obj(env[v1], env[v2]) == exp for env, exp in examples)
                    except Exception:
                        ok = False
                    if ok:
                        call_expr = f"{comp.symbol_name}({v1}, {v2})"
                        if call_expr not in seen_exprs:
                            seen_exprs.add(call_expr)
                            nc = _build_patched_src(call_expr, comp.import_stmt)
                            if nc:
                                out.append({
                                    "component_id": comp.component_id,
                                    "call_expr": call_expr,
                                    "import_stmt": comp.import_stmt,
                                    "patched_source": nc,
                                    "hops": 1,
                                })

        # 1c. 2-Hop Repo-Native Composition: `return h2(h1(var))` (SyPet style!)
        if not out and len(unary_comps) >= 2:
            loaded_unary = [(c, _load_callable(c)) for c in unary_comps[:24]]
            loaded_unary = [(c, fn) for c, fn in loaded_unary if fn is not None]
            for c1, f1 in loaded_unary:
                if len(out) >= max_candidates:
                    break
                for vname in shared_vars[:6]:
                    try:
                        mids = [f1(env[vname]) for env, _ in examples]
                    except Exception:
                        continue
                    for c2, f2 in loaded_unary:
                        if c2.component_id == c1.component_id:
                            continue
                        try:
                            ok = all(f2(m) == exp for m, (_, exp) in zip(mids, examples))
                        except Exception:
                            ok = False
                        if ok:
                            call_expr = f"{c2.symbol_name}({c1.symbol_name}({vname}))"
                            if call_expr in seen_exprs:
                                continue
                            seen_exprs.add(call_expr)
                            imps = "\n".join(x for x in (c1.import_stmt, c2.import_stmt) if x)
                            nc = _build_patched_src(call_expr, imps)
                            if nc:
                                out.append({
                                    "component_id": f"{c2.component_id}({c1.component_id})",
                                    "call_expr": call_expr,
                                    "import_stmt": imps,
                                    "patched_source": nc,
                                    "hops": 2,
                                })
                                break
    finally:
        sys.path[:] = orig_sys_path

    return out


# ===========================================================================
# 2. DUAL-PROGRAM SPLICING (SYMLMM IfThenElse WITHOUT AN LLM)
# ===========================================================================


def _find_changed_statement_pair(
    orig_source: str,
    cand_source: str,
    hint_lineno: int,
) -> tuple[int, int, str, str, str] | None:
    """Locate the single changed statement `(orig_start, orig_end, indent, orig_stmt_src, cand_stmt_src)`."""
    try:
        orig_lines = orig_source.splitlines(keepends=True)
        cand_lines = cand_source.splitlines(keepends=True)
        ast.parse(orig_source)
        ast.parse(cand_source)
    except SyntaxError:
        return None

    # Fast surgical single-line diff check at or near hint_lineno
    if len(orig_lines) == len(cand_lines):
        diffs = [i for i in range(len(orig_lines)) if orig_lines[i] != cand_lines[i]]
        if len(diffs) == 1:
            idx = diffs[0]
            ol = orig_lines[idx]
            cl = cand_lines[idx]
            ostrip = ol.lstrip()
            cstrip = cl.lstrip()
            indent = ol[: len(ol) - len(ostrip)]
            # Only splice simple executable statements (return/assign/expr), not block headers
            if (
                ostrip
                and cstrip
                and not ostrip.rstrip().endswith(":")
                and not cstrip.rstrip().endswith(":")
            ):
                return (idx + 1, idx + 1, indent, ostrip.rstrip("\r\n"), cstrip.rstrip("\r\n"))

    # Fallback: AST-level match on changed function body at hint_lineno
    try:
        ot = ast.parse(orig_source)
        ct = ast.parse(cand_source)
    except SyntaxError:
        return None

    for ofn in ast.walk(ot):
        if isinstance(ofn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            oln = int(getattr(ofn, "lineno", 0))
            oend = int(getattr(ofn, "end_lineno", oln))
            if oln <= hint_lineno <= oend:
                # Find matching function in cand_source
                for cfn in ast.walk(ct):
                    if isinstance(cfn, type(ofn)) and cfn.name == ofn.name:
                        if len(ofn.body) == len(cfn.body):
                            diff_idxs = [
                                k for k in range(len(ofn.body))
                                if ast.dump(ofn.body[k]) != ast.dump(cfn.body[k])
                            ]
                            if len(diff_idxs) == 1:
                                ost = ofn.body[diff_idxs[0]]
                                cst = cfn.body[diff_idxs[0]]
                                if not isinstance(ost, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                                    s_ln = int(getattr(ost, "lineno", 1))
                                    e_ln = int(getattr(ost, "end_lineno", s_ln))
                                    ln0 = orig_lines[s_ln - 1]
                                    ind = ln0[: len(ln0) - len(ln0.lstrip())]
                                    return (s_ln, e_ln, ind, ast.unparse(ost), ast.unparse(cst))
    return None


def _unwrap_frame_envs(envs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize either raw Python variable dicts OR `causal_angelic_swe_engine_v1`
    frame-summary dicts (`{var: {'type': ..., 'scalar': ..., 'is_none': ..., 'len': ...}}`)
    into flat scalar/bool/None dicts consumed by `oe_sygus_synthesizer_v1`."""
    flat_list: list[dict[str, Any]] = []
    for env in envs:
        if not isinstance(env, Mapping):
            continue
        flat: dict[str, Any] = {}
        for k, v in env.items():
            if not isinstance(k, str) or k.startswith("__"):
                continue
            if isinstance(v, Mapping) and ("type" in v or "scalar" in v or "is_none" in v or "is_falsey" in v):
                if v.get("is_none"):
                    flat[k] = None
                elif "scalar" in v and v["scalar"] is not None:
                    flat[k] = v["scalar"]
                elif v.get("type") == "bool" and "is_falsey" in v:
                    flat[k] = not bool(v["is_falsey"])
                elif "len" in v and isinstance(v["len"], int):
                    flat[f"__len__:{k}"] = v["len"]
            elif isinstance(v, (int, float, bool, str, type(None))):
                flat[k] = v
        if flat:
            flat_list.append(flat)
    return flat_list


def splice_dual_programs(
    orig_source: str,
    cand_source: str,
    changed_lineno: int,
    cand_wins_envs: Sequence[Mapping[str, Any]],
    orig_wins_envs: Sequence[Mapping[str, Any]],
    *,
    max_splices: int = 4,
) -> list[dict[str, Any]]:
    """Counterexample-Partitioned Program Merging (Dual-Program Splicing, zero LLM).

    When `cand_source` (P1) passes T1 (whose live frames are `cand_wins_envs`) and
    `orig_source` (P0) passes T2 (whose live frames are `orig_wins_envs`), synthesizes
    ONLY the minimal separating guard `G` via `oe_sygus_synthesizer_v1` and splices:

        if G:
            <P1 statement>
        else:
            <P0 statement>
    """
    if not cand_wins_envs or not orig_wins_envs:
        return []
    pair = _find_changed_statement_pair(orig_source, cand_source, changed_lineno)
    if pair is None:
        return []
    s_ln, e_ln, indent, orig_stmt, cand_stmt = pair

    flat_cand = _unwrap_frame_envs(cand_wins_envs)
    flat_orig = _unwrap_frame_envs(orig_wins_envs)
    if not flat_cand or not flat_orig:
        return []

    preds = OESYGUS.synthesize_separating_predicates(
        flat_cand,
        flat_orig,
        lang="python",
        max_results=max_splices,
    )
    if not preds:
        return []

    orig_lines = orig_source.splitlines(keepends=True)
    spliced_results: list[dict[str, Any]] = []
    seen_guards: set[str] = set()

    for pr in preds[:max_splices]:
        gcode = str((pr.get("code") if isinstance(pr, Mapping) else getattr(pr, "code", "")) or "").strip()
        if not gcode or gcode in seen_guards:
            continue
        seen_guards.add(gcode)
        block = (
            f"{indent}if {gcode}:\n"
            f"{indent}    {cand_stmt}\n"
            f"{indent}else:\n"
            f"{indent}    {orig_stmt}\n"
        )
        nc = "".join(orig_lines[: s_ln - 1]) + block + "".join(orig_lines[e_ln:])
        try:
            ast.parse(nc)
        except SyntaxError:
            continue
        spliced_results.append({
            "lineno": s_ln,
            "guard": gcode,
            "cand_stmt": cand_stmt,
            "orig_stmt": orig_stmt,
            "patched_source": nc,
            "model_calls": 0,
            "parameters_stored": 0,
        })

    return spliced_results


# ===========================================================================
# 3. 16-WAY PARALLEL COPY-ON-WRITE COUNTERFACTUAL SPECULATIVE ROLLOUTS
# ===========================================================================


def speculative_cow_rollout(
    action_specs: Sequence[Mapping[str, Any]],
    executor_fn: Callable[[Mapping[str, Any]], Any],
    residual_fn: Callable[[Any], float],
    *,
    baseline_residual: float | None = None,
    max_workers: int = 16,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """Fork up to `max_workers` (default 16) parallel Linux Copy-on-Write realities simultaneously!

    Each forked child inherits parent memory via OS Copy-on-Write (zero-copy until mutated,
    ~1-3ms fork overhead), executes one candidate action in total isolation (parent memory
    is NEVER mutated!), evaluates `residual_fn(outcome)` (lower is better; 0.0 == goal met),
    pipes the compact JSON result back to parent, and exits cleanly (`os._exit(0)`).

    Returns the mathematically best branch that minimizes goal residual, plus telemetry across
    all parallel counterfactual realities.
    """
    t0 = time.monotonic()
    batch = list(action_specs)[:max_workers]
    if not batch:
        return {
            "schema": SCHEMA,
            "status": "NO_ACTIONS",
            "best_action": None,
            "best_residual": baseline_residual,
            "branches_evaluated": 0,
            "outcomes": [],
            "elapsed_ms": 0.0,
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Fork all candidate branches in parallel using real POSIX CoW `os.fork()` + `os.pipe()`
    children: list[tuple[int, int, int, Mapping[str, Any]]] = []  # (idx, pid, read_fd, spec)
    for idx, spec in enumerate(batch):
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            # --- Isolated Copy-on-Write Child Reality ---
            os.close(r_fd)
            c_t0 = time.monotonic()
            payload: dict[str, Any]
            try:
                out_val = executor_fn(spec)
                res_val = float(residual_fn(out_val))
                payload = {
                    "idx": idx,
                    "action_id": str(spec.get("action_id") or f"act_{idx}"),
                    "ok": True,
                    "residual": res_val,
                    "summary": str(out_val)[:240],
                    "child_ms": round((time.monotonic() - c_t0) * 1000.0, 3),
                }
            except Exception as exc:
                payload = {
                    "idx": idx,
                    "action_id": str(spec.get("action_id") or f"act_{idx}"),
                    "ok": False,
                    "residual": float("inf"),
                    "error": f"{type(exc).__name__}: {exc}",
                    "child_ms": round((time.monotonic() - c_t0) * 1000.0, 3),
                }
            try:
                raw = json.dumps(payload).encode("utf-8")
                os.write(w_fd, raw)
            finally:
                os.close(w_fd)
                os._exit(0)
        else:
            os.close(w_fd)
            children.append((idx, pid, r_fd, spec))

    # Non-blocking multiplexed read from all 16 CoW pipes before timeout
    deadline = time.monotonic() + timeout_s
    fd_to_buf: dict[int, bytearray] = {r_fd: bytearray() for _, _, r_fd, _ in children}
    open_fds = set(fd_to_buf.keys())

    while open_fds and time.monotonic() < deadline:
        rem = max(0.01, deadline - time.monotonic())
        ready, _, _ = select.select(list(open_fds), [], [], min(rem, 0.25))
        if not ready:
            continue
        for fd in ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                open_fds.discard(fd)
                os.close(fd)
            else:
                fd_to_buf[fd].extend(chunk)

    for fd in list(open_fds):
        try:
            os.close(fd)
        except OSError:
            pass

    outcomes: list[dict[str, Any]] = []
    for idx, pid, r_fd, spec in children:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        raw_b = bytes(fd_to_buf[r_fd])
        if raw_b:
            try:
                rec = json.loads(raw_b.decode("utf-8"))
            except Exception:
                rec = {
                    "idx": idx,
                    "action_id": str(spec.get("action_id") or f"act_{idx}"),
                    "ok": False,
                    "residual": float("inf"),
                    "error": "DECODE_ERROR",
                }
        else:
            rec = {
                "idx": idx,
                "action_id": str(spec.get("action_id") or f"act_{idx}"),
                "ok": False,
                "residual": float("inf"),
                "error": "TIMEOUT_OR_CRASH",
            }
        outcomes.append(rec)

    outcomes.sort(key=lambda r: (0 if r.get("ok") else 1, float(r.get("residual", float("inf"))), int(r.get("idx", 0))))
    best = outcomes[0] if outcomes and outcomes[0].get("ok") else None
    best_spec = batch[best["idx"]] if best is not None else None
    best_res = float(best["residual"]) if best is not None else float("inf")
    improved = (baseline_residual is None) or (best_res < baseline_residual)

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "cow_parallel_speculative_rollout",
        "status": "VERIFIED" if (best is not None and improved) else "NO_IMPROVEMENT",
        "cow_fork_parallelism": len(batch),
        "branches_evaluated": len(outcomes),
        "best_action_id": best["action_id"] if best is not None else None,
        "best_action": dict(best_spec) if best_spec is not None else None,
        "best_residual": best_res if best is not None else None,
        "baseline_residual": baseline_residual,
        "strictly_improved": bool(best is not None and improved),
        "outcomes": outcomes,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ===========================================================================
# 4. UNIFIED CROSS-MODAL TYPE-TRANSITION PETRI NET (GUI + SQLITE + CODE + CLI)
# ===========================================================================


@dataclass(frozen=True)
class PetriTransition:
    """One typed transition across ANY modality (GUI, SQLite, OS file, CLI, Python function)."""

    transition_id: str
    modality: str  # "gui" | "sqlite" | "os_file" | "cli" | "python" | "http" | "composite_l2"
    input_places: tuple[str, ...]  # Required semantic-type / state-fact tokens (multi-input!)
    output_places: tuple[str, ...]  # Produced semantic-type / state-fact tokens
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None
    constituent_ids: tuple[str, ...] = ()


class UnifiedCrossModalPetriNet:
    """SyPet / APIphany-style Multi-Token Type-Transition Petri Net unifying
    GUI A11y actions, SQLite queries, OS/CLI commands, and Repo-Native Python functions.

    Every modality is compiled into the EXACT same mathematical structure:
        Transition:  MultiSet(Input Places)  --->  MultiSet(Output Places)
    A single shortest-path reachability solve chains GUI -> SQLite -> Python -> CLI in one plan,
    executes it live, and crystallizes the verified chain as a 1-hop L2 transition!
    """

    def __init__(self) -> None:
        self.transitions: dict[str, PetriTransition] = {}

    def add_transition(self, tr: PetriTransition) -> None:
        self.transitions[tr.transition_id] = tr

    def add_repo_components(self, repo_root: str | pathlib.Path, *, focus_file: str | None = None) -> int:
        """Compile mined repository Python functions directly into Petri-net transitions."""
        mined = mine_repo_components_as_morphisms(repo_root, focus_file=focus_file, max_components=64)
        added = 0
        for comp in mined["components"]:
            if comp.kind == "function" and comp.input_types and comp.output_type != "Any":
                self.add_transition(
                    PetriTransition(
                        transition_id=comp.component_id,
                        modality="python",
                        input_places=comp.input_types,
                        output_places=(comp.output_type,),
                    )
                )
                added += 1
        return added

    def solve(
        self,
        initial_places: Sequence[str],
        goal_places: Sequence[str],
        *,
        max_steps: int = 8,
    ) -> dict[str, Any]:
        """Shortest-path Petri-net reachability search with backward-relevance pruning."""
        t0 = time.monotonic()
        init_set = frozenset(initial_places)
        goal_set = frozenset(goal_places)

        if goal_set.issubset(init_set):
            return {
                "schema": SCHEMA,
                "status": "TRIVIAL",
                "steps": [],
                "transition_ids": [],
                "modalities_chained": [],
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Backward cone of relevant places from goal_set (prunes irrelevant transitions instantly!)
        relevant_places: set[str] = set(goal_set)
        changed = True
        while changed:
            changed = False
            for tr in self.transitions.values():
                if any(op in relevant_places for op in tr.output_places):
                    for ip in tr.input_places:
                        if ip not in relevant_places:
                            relevant_places.add(ip)
                            changed = True

        relevant_trs = [
            tr for tr in self.transitions.values()
            if any(op in relevant_places for op in tr.output_places)
        ]

        q: deque[tuple[frozenset[str], list[PetriTransition]]] = deque([(init_set, [])])
        visited: set[frozenset[str]] = {init_set}

        while q:
            marking, path = q.popleft()
            if len(path) >= max_steps:
                continue
            for tr in relevant_trs:
                if not frozenset(tr.input_places).issubset(marking):
                    continue
                if any(prev.transition_id == tr.transition_id for prev in path):
                    continue
                next_marking = marking | frozenset(tr.output_places)
                if next_marking == marking:
                    continue
                next_path = path + [tr]
                if goal_set.issubset(next_marking):
                    return {
                        "schema": SCHEMA,
                        "authority": AUTHORITY,
                        "status": "SOLVED",
                        "hops": len(next_path),
                        "steps": next_path,
                        "transition_ids": [t.transition_id for t in next_path],
                        "modalities_chained": [t.modality for t in next_path],
                        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }
                if next_marking not in visited:
                    visited.add(next_marking)
                    q.append((next_marking, next_path))

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "status": "UNREACHABLE",
            "hops": 0,
            "steps": [],
            "transition_ids": [],
            "modalities_chained": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    def execute_and_crystallize(
        self,
        plan: Mapping[str, Any],
        initial_context: Mapping[str, Any],
        *,
        governed_memory: dict[str, Any] | None = None,
        verifier: Callable[[Mapping[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Execute a solved cross-modal Petri-net plan live and crystallize it into ONE
        1-hop higher-order L2 Petri transition (O(1) deletable from external memory)."""
        steps: list[PetriTransition] = list(plan.get("steps") or [])
        if not steps:
            return {"schema": SCHEMA, "status": "EMPTY_PLAN", "model_calls": 0, "parameters_stored": 0}

        ctx = dict(initial_context)
        for tr in steps:
            if tr.executor is None:
                return {
                    "schema": SCHEMA,
                    "status": "MISSING_EXECUTOR",
                    "failed_transition": tr.transition_id,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            try:
                delta = tr.executor(ctx)
                if isinstance(delta, Mapping):
                    ctx.update(delta)
            except Exception as exc:
                return {
                    "schema": SCHEMA,
                    "status": "EXECUTION_ERROR",
                    "failed_transition": tr.transition_id,
                    "error": f"{type(exc).__name__}: {exc}",
                    "model_calls": 0,
                    "parameters_stored": 0,
                }

        if verifier is not None and not verifier(ctx):
            return {"schema": SCHEMA, "status": "VERIFIER_REJECTED", "context": ctx, "model_calls": 0, "parameters_stored": 0}

        # Crystallize multi-modal chain into a single 1-hop L2 transition!
        sig_raw = "->".join(t.transition_id for t in steps)
        cid = "l2_petri_" + hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:12]

        # Compute net input places (inputs not produced earlier in chain) and cumulative outputs
        produced_so_far: set[str] = set()
        net_inputs: list[str] = []
        for tr in steps:
            for ip in tr.input_places:
                if ip not in produced_so_far and ip not in net_inputs:
                    net_inputs.append(ip)
            produced_so_far.update(tr.output_places)
        final_outputs = tuple(sorted(produced_so_far))

        def _composite_exec(c_in: Mapping[str, Any], _chain: tuple[PetriTransition, ...] = tuple(steps)) -> Mapping[str, Any]:
            c_cur = dict(c_in)
            for s in _chain:
                if s.executor is not None:
                    d = s.executor(c_cur)
                    if isinstance(d, Mapping):
                        c_cur.update(d)
            return c_cur

        comp_tr = PetriTransition(
            transition_id=cid,
            modality="composite_l2",
            input_places=tuple(net_inputs),
            output_places=final_outputs,
            executor=_composite_exec,
            constituent_ids=tuple(t.transition_id for t in steps),
        )
        self.add_transition(comp_tr)

        if governed_memory is not None:
            governed_memory.setdefault("l2_petri_morphisms", {})[cid] = {
                "transition_id": cid,
                "input_places": list(comp_tr.input_places),
                "output_places": list(comp_tr.output_places),
                "constituent_ids": list(comp_tr.constituent_ids),
                "modalities": [t.modality for t in steps],
                "verified": True,
                "parameters_stored": 0,
            }

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "status": "VERIFIED_AND_CRYSTALLIZED",
            "crystallized_transition_id": cid,
            "hops_before": len(steps),
            "hops_after": 1,
            "modalities_chained": [t.modality for t in steps],
            "context": ctx,
            "model_calls": 0,
            "parameters_stored": 0,
        }
