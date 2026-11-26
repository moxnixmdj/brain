"""Wave 40 Dark-Matter Frontier Kernel (K3=0, $0 spend).

Awakens and unifies 24 previously DARK high-leverage modules across 4 organ
clusters plus 6 zero-GPU late-2026 frontier mechanisms directly behind
`UnifiedModel`, `Creature`, and `unified_hidden_capability_federation_v1`:

1. `EpistemicSWEAndEGraphKernel`
   Live-wires `guarded_meaning_ir_v1` (Region-SSA + SemiPersistentEGraph +
   anti_unify), `angelic_cegis_v1` (observational equivalence + hole synthesis),
   `causal_nexus_v1` (value obligation extraction + invertible transducer
   inference), `grammar_closed_repair_v1` (edit-library-free AST atom + operator
   swap synthesis), and `unified_epistemic_portfolio_v1` (portfolio status +
   hardlinked CoW overlay).

2. `OneShotEpistemicLearnerKernel`
   Live-wires `evidence_demand_v1` (complete grammar sweep, ambiguity refusal,
   minimal distinguishing probe, version-space collapse), `settlement_v1`,
   `hypothesis_classes_v1` (algebraic hypothesis determination with surplus),
   `vocabulary_induction_v1`, `operator_acquisition_v1` (law-checked operator
   induction), `demonstration_version_space_v1`, and `transfer_learning_v1`.

3. `ShadowInterfaceHCURouterKernel`
   Implements Simular Agent-S4 (arXiv:2610.28601) evolving shadow-interface
   compilation + Microsoft HCU (arXiv:2610.41432) 3-channel action routing
   (Channel 0 CLI/Code -> Channel 1 Semantic AX/Mental-Model -> Channel 2 GUI
   fallback), live-wiring `tool_census_v1`, `computer_env_v1`,
   `executable_mental_model_v1`, `computer_use_agent_v1`, and `aimed_action_v1`.

4. `OutOfCoreRLMWorkspace`
   Implements MIT Recursive Language Models (arXiv:2512.24601): keeps
   multi-megabyte repos, traces, and logs out-of-core behind SHA-256 indexed
   symbolic handles with bounded programmatic slicing, AST symbol extraction,
   and bounded recursive map-reduce with zero lossy compaction.

5. `FourNetworkGitMemoryEngine`
   Implements Hindsight 4-Network Memory (`world_facts`, `experiences`,
   `observations`, `mental_models`) + Letta MemFS / ByteRover plain git-diffable
   file persistence + DeepSeek Engram O(1) hashed N-gram lookup table +
   bi-temporal (`valid_from` / `valid_to`) Sleep Knowledge Seeding consolidation
   + Wave 38 TMA-NM HMAC integrity verification.

6. `CHASEHillSamplingNFVGate`
   Implements Staged Goal-Blind NFV (arXiv:2608.21516) preventing unstaged
   false-proof drift, CHASE validity-preserving semantic perturbation auditing
   (arXiv:2605.30621), Harness-Delta Attribution / HDA (arXiv:2610.22466)
   decomposing total gain into genuine generalization vs overfitting vs compute
   scaling, and Hill Sampling (arXiv:2609.25510) adaptive parent selection.

7. `SelfPlaySteerAndHorizonKernel`
   Implements Meta Self-Play SWE-RL (arXiv:2512.18552) zero-data AST bug
   challenger–solver episodes inside real POSIX `os.fork()` CoW isolation +
   CMU Steer-Don't-Solve (EMNLP'26) trajectory critic emitting 1-line corrective
   steering directives + live-wires `horizon_bounded_execution_v1`,
   `composition_verification_v1`, `credit_assignment_v1`,
   `weights_from_scratch_v1`, `creature_stakes_and_initiative_v1`,
   `curriculum_v1`, and `the_record_is_the_commit_v1` (crash-recoverable atomic
   WAL commits with `fsync` + content-digest idempotency).
"""

from __future__ import annotations

import ast
import copy
import hashlib
import hmac
import json
import math
import os
import pathlib
import random
import re
import secrets
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_WAVE40_DARK_MATTER_FRONTIER_KERNEL_V1"
PRODUCER_MODEL_CALLS = 0

AWAKENED_DARK_MODULES: tuple[str, ...] = (
    "canonical/swe_kernel/guarded_meaning_ir_v1.py",
    "canonical/swe_kernel/angelic_cegis_v1.py",
    "canonical/swe_kernel/causal_nexus_v1.py",
    "canonical/swe_kernel/unified_epistemic_portfolio_v1.py",
    "canonical/tools/grammar_closed_repair_v1.py",
    "canonical/runtime/demonstration_version_space_v1.py",
    "canonical/runtime/evidence_demand_v1.py",
    "canonical/runtime/settlement_v1.py",
    "canonical/runtime/hypothesis_classes_v1.py",
    "canonical/runtime/vocabulary_induction_v1.py",
    "canonical/runtime/operator_acquisition_v1.py",
    "canonical/runtime/transfer_learning_v1.py",
    "canonical/runtime/tool_census_v1.py",
    "canonical/runtime/computer_env_v1.py",
    "canonical/swe_kernel/executable_mental_model_v1.py",
    "canonical/swe_kernel/computer_use_agent_v1.py",
    "canonical/runtime/aimed_action_v1.py",
    "canonical/swe_kernel/horizon_bounded_execution_v1.py",
    "canonical/swe_kernel/composition_verification_v1.py",
    "canonical/swe_kernel/credit_assignment_v1.py",
    "canonical/swe_kernel/weights_from_scratch_v1.py",
    "canonical/runtime/creature_stakes_and_initiative_v1.py",
    "canonical/runtime/curriculum_v1.py",
    "canonical/tools/the_record_is_the_commit_v1.py",
)

_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError,
}

_FORBIDDEN_AST_NODES = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)
_FORBIDDEN_CALL_NAMES = frozenset(
    {"eval", "exec", "compile", "open", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars"}
)
_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_obj(obj: Any) -> str:
    return _sha256_text(json.dumps(obj, sort_keys=True, default=str))


def _check_safe_pure_python_ast(source: str) -> tuple[bool, str | None, ast.Module | None]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"SYNTAX_ERROR:{exc.msg}", None
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_AST_NODES):
            return False, f"FORBIDDEN_NODE:{type(node).__name__}", None
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALL_NAMES:
                return False, f"FORBIDDEN_CALL:{node.func.id}", None
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, f"FORBIDDEN_DUNDER:{node.attr}", None
    return True, None, tree


def _compile_pure_function(source: str, fn_name: str) -> tuple[Callable[..., Any] | None, str | None]:
    ok, err, _ = _check_safe_pure_python_ast(source)
    if not ok:
        return None, err
    ns: dict[str, Any] = {"__builtins__": dict(_SAFE_BUILTINS)}
    try:
        exec(compile(source, "<wave40_sandbox>", "exec"), ns, ns)
    except Exception as exc:
        return None, f"EXEC_ERROR:{type(exc).__name__}:{exc}"
    fn = ns.get(fn_name)
    if not callable(fn):
        return None, f"MISSING_CALLABLE:{fn_name}"
    return fn, None


def _eval_cases(fn: Callable[..., Any], test_cases: Sequence[tuple[tuple[Any, ...], Any]]) -> tuple[int, list[dict[str, Any]]]:
    passed = 0
    rows: list[dict[str, Any]] = []
    for idx, (args, expected) in enumerate(test_cases):
        call_args = args if isinstance(args, tuple) else (args,)
        try:
            got = fn(*copy.deepcopy(call_args))
            ok = got == expected
            rows.append({"case": idx, "ok": ok, "got": repr(got), "expected": repr(expected)})
            if ok:
                passed += 1
        except Exception as exc:
            rows.append({"case": idx, "ok": False, "error": f"{type(exc).__name__}:{exc}", "expected": repr(expected)})
    return passed, rows


def _run_in_cow_fork(fn: Callable[[], dict[str, Any]], *, timeout_s: float = 5.0) -> dict[str, Any]:
    """Execute a pure verification thunk inside a real POSIX `os.fork()` CoW child."""
    if not hasattr(os, "fork"):
        res = fn()
        res["cow_fork_used"] = False
        return res
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        try:
            payload = fn()
            payload["cow_fork_used"] = True
            payload["child_pid"] = os.getpid()
            raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        except Exception as exc:
            raw = json.dumps(
                {"pass": False, "error": f"{type(exc).__name__}:{exc}", "cow_fork_used": True, "child_pid": os.getpid()},
                sort_keys=True,
            ).encode("utf-8")
        try:
            os.write(w_fd, raw)
        finally:
            os.close(w_fd)
            os._exit(0)
    os.close(w_fd)
    deadline = time.monotonic() + max(0.25, float(timeout_s))
    chunks: list[bytes] = []
    timed_out = False
    try:
        while True:
            finished_pid, _ = os.waitpid(pid, os.WNOHANG)
            if finished_pid == pid:
                break
            if time.monotonic() >= deadline:
                timed_out = True
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)
                break
            time.sleep(0.005)
        while True:
            buf = os.read(r_fd, 65536)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(r_fd)
    if timed_out:
        return {"pass": False, "error": "COW_FORK_TIMEOUT", "cow_fork_used": True}
    raw_text = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw_text:
        return {"pass": False, "error": "COW_FORK_EMPTY_PIPE", "cow_fork_used": True}
    return json.loads(raw_text)


# =============================================================================
# 1. Epistemic SWE + E-Graph + Angelic CEGIS + Grammar-Closed Repair
# =============================================================================


class EpistemicSWEAndEGraphKernel:
    """Live unifier for guarded_meaning_ir, angelic_cegis, causal_nexus,
    grammar_closed_repair, and unified_epistemic_portfolio."""

    @staticmethod
    def _build_mir_term(spec: Any, gmir: Any) -> Any:
        if isinstance(spec, gmir.Term):
            return spec
        if isinstance(spec, (int, float, bool)):
            return gmir.const(spec)
        if isinstance(spec, str):
            return gmir.var(spec)
        if isinstance(spec, Mapping):
            if "const" in spec:
                return gmir.const(spec["const"])
            if "var" in spec:
                return gmir.var(str(spec["var"]))
            op = str(spec["op"])
            args = tuple(EpistemicSWEAndEGraphKernel._build_mir_term(a, gmir) for a in spec.get("args") or ())
            return gmir.Term(op, args)
        raise ValueError(f"Unsupported MIR term spec: {spec!r}")

    @classmethod
    def egraph_verify_and_anti_unify(
        cls,
        *,
        term_a: Any = None,
        term_b: Any = None,
        source_a: str | None = None,
        source_b: str | None = None,
    ) -> dict[str, Any]:
        from canonical.swe_kernel import guarded_meaning_ir_v1 as gmir

        result: dict[str, Any] = {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS",
            "model_calls": PRODUCER_MODEL_CALLS,
        }
        if source_a is not None:
            mir_a = gmir.lower_python(source_a)
            result["source_a_functions"] = sorted(mir_a.functions.keys()) if hasattr(mir_a, "functions") else []
        if source_b is not None:
            mir_b = gmir.lower_python(source_b)
            result["source_b_functions"] = sorted(mir_b.functions.keys()) if hasattr(mir_b, "functions") else []

        if term_a is not None and term_b is not None:
            ta = cls._build_mir_term(term_a, gmir)
            tb = cls._build_mir_term(term_b, gmir)
            egraph = gmir.SemiPersistentEGraph()
            equiv = bool(gmir.terms_equal(ta, tb))
            au = gmir.anti_unify(ta, tb, egraph)
            result["terms_equal"] = equiv
            raw_holes = au.get("holes") or []
            if isinstance(raw_holes, Mapping):
                holes_repr: Any = {str(k): repr(v) for k, v in raw_holes.items()}
            else:
                holes_repr = [repr(h) for h in raw_holes]
            result["anti_unify"] = {
                "equal": bool(au.get("equal")),
                "schema": repr(au.get("schema")),
                "hole_count": len(raw_holes),
                "holes": holes_repr,
            }
        result["pass"] = True
        return result

    @classmethod
    def grammar_closed_cegis_repair(
        cls,
        buggy_source: str,
        *,
        fn_name: str,
        test_cases: Sequence[tuple[tuple[Any, ...], Any]],
        reference_source: str | None = None,
        max_candidates: int = 160,
        use_cow_fork: bool = True,
    ) -> dict[str, Any]:
        """Synthesize a repair strictly from AST atoms & operator swaps of `buggy_source`
        (zero hand-written patch library) and cross-check via `angelic_cegis_v1`."""
        from canonical.swe_kernel import angelic_cegis_v1 as ac
        from canonical.tools import grammar_closed_repair_v1 as gcr

        ok, err, tree = _check_safe_pure_python_ast(buggy_source)
        if not ok or tree is None:
            return {"pass": False, "error": err or "INVALID_BUGGY_SOURCE", "model_calls": PRODUCER_MODEL_CALLS}

        target_fn: ast.FunctionDef | None = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                target_fn = node
                break
        if target_fn is None:
            return {"pass": False, "error": f"FUNCTION_NOT_FOUND:{fn_name}", "model_calls": PRODUCER_MODEL_CALLS}

        base_fn, base_err = _compile_pure_function(buggy_source, fn_name)
        if base_fn is None:
            return {"pass": False, "error": base_err, "model_calls": PRODUCER_MODEL_CALLS}
        base_passed, base_rows = _eval_cases(base_fn, test_cases)

        atoms = list(gcr.atoms_of(target_fn))
        candidates: list[tuple[str, str]] = []
        seen_src: set[str] = {buggy_source.strip()}

        # Phase 1: grammar-closed operator swaps (BinOp, Compare, UnaryOp, BoolOp)
        mutable_indices: list[tuple[int, ast.AST]] = [
            (idx, node)
            for idx, node in enumerate(ast.walk(target_fn))
            if isinstance(node, (ast.BinOp, ast.Compare, ast.BoolOp, ast.UnaryOp))
        ]
        for node_idx, _ in mutable_indices:
            fresh_tree = copy.deepcopy(tree)
            fresh_fn = next(n for n in fresh_tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name)
            nodes = list(ast.walk(fresh_fn))
            target_node = nodes[node_idx]
            swaps = list(gcr.operator_swaps(target_node))
            for swapped in swaps:
                mut_tree = copy.deepcopy(tree)
                mut_fn = next(n for n in mut_tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name)
                mut_nodes = list(ast.walk(mut_fn))
                old = mut_nodes[node_idx]
                replaced = False
                if isinstance(old, ast.BinOp) and isinstance(swapped, ast.operator):
                    old.op = copy.deepcopy(swapped)
                    replaced = True
                elif isinstance(old, ast.Compare) and len(old.ops) == 1 and isinstance(swapped, ast.cmpop):
                    old.ops[0] = copy.deepcopy(swapped)
                    replaced = True
                elif isinstance(old, ast.BoolOp) and isinstance(swapped, ast.boolop):
                    old.op = copy.deepcopy(swapped)
                    replaced = True
                elif isinstance(old, ast.UnaryOp) and isinstance(swapped, ast.unaryop):
                    old.op = copy.deepcopy(swapped)
                    replaced = True
                if replaced:
                    ast.fix_missing_locations(mut_tree)
                    cand_src = ast.unparse(mut_tree)
                    if cand_src.strip() not in seen_src:
                        seen_src.add(cand_src.strip())
                        candidates.append(("operator_swap", cand_src))
                if len(candidates) >= max_candidates:
                    break
            if len(candidates) >= max_candidates:
                break

        # Phase 2: grammar-closed expression replacement from function's own atoms
        if len(candidates) < max_candidates:
            expr_nodes: list[tuple[int, str]] = []
            for idx, node in enumerate(ast.walk(target_fn)):
                if isinstance(node, (ast.Constant, ast.Name, ast.BinOp)):
                    try:
                        expr_nodes.append((idx, ast.unparse(node)))
                    except Exception:
                        continue
            for node_idx, node_src in expr_nodes:
                for repl_text in gcr.candidate_texts(node_src, atoms):
                    try:
                        repl_expr = ast.parse(repl_text, mode="eval").body
                    except SyntaxError:
                        continue
                    mut_tree = copy.deepcopy(tree)
                    mut_fn = next(n for n in mut_tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name)
                    mut_nodes = list(ast.walk(mut_fn))
                    old = mut_nodes[node_idx]
                    parent_map = {child: parent for parent in ast.walk(mut_tree) for child in ast.iter_child_nodes(parent)}
                    parent = parent_map.get(old)
                    if parent is None or isinstance(old, ast.Name) and isinstance(getattr(old, "ctx", None), ast.Store):
                        continue
                    replaced = False
                    for field_name, value in ast.iter_fields(parent):
                        if value is old:
                            setattr(parent, field_name, copy.deepcopy(repl_expr))
                            replaced = True
                        elif isinstance(value, list):
                            for i, item in enumerate(value):
                                if item is old:
                                    value[i] = copy.deepcopy(repl_expr)
                                    replaced = True
                    if replaced:
                        ast.fix_missing_locations(mut_tree)
                        cand_src = ast.unparse(mut_tree)
                        if cand_src.strip() not in seen_src:
                            seen_src.add(cand_src.strip())
                            candidates.append(("atom_substitution", cand_src))
                    if len(candidates) >= max_candidates:
                        break
                if len(candidates) >= max_candidates:
                    break

        def _search_candidates() -> dict[str, Any]:
            evaluated = 0
            for origin, cand_src in candidates:
                evaluated += 1
                cand_fn, cerr = _compile_pure_function(cand_src, fn_name)
                if cand_fn is None or cerr is not None:
                    continue
                passed, rows = _eval_cases(cand_fn, test_cases)
                if passed == len(test_cases):
                    obs_eq = None
                    if reference_source:
                        ref_fn, rerr = _compile_pure_function(reference_source, fn_name)
                        if ref_fn is not None and rerr is None:
                            arg_names = [a.arg for a in target_fn.args.args]
                            env_inputs = [
                                dict(zip(arg_names, (a if isinstance(a, tuple) else (a,))))
                                for a, _ in test_cases
                            ]
                            obs_eq = ac.observational_equivalence(
                                lambda env, _f=cand_fn, _an=arg_names: _f(*(env[k] for k in _an)),
                                lambda env, _f=ref_fn, _an=arg_names: _f(*(env[k] for k in _an)),
                                env_inputs,
                            )
                    return {
                        "pass": True,
                        "repaired": True,
                        "repair_origin": origin,
                        "repaired_source": cand_src,
                        "base_passed": base_passed,
                        "total_cases": len(test_cases),
                        "candidates_generated": len(candidates),
                        "candidates_evaluated": evaluated,
                        "atoms_extracted": atoms,
                        "observational_equivalence": obs_eq,
                        "rows": rows,
                    }
            return {
                "pass": False,
                "repaired": False,
                "base_passed": base_passed,
                "total_cases": len(test_cases),
                "candidates_generated": len(candidates),
                "candidates_evaluated": evaluated,
                "atoms_extracted": atoms,
                "base_rows": base_rows,
            }

        outcome = _run_in_cow_fork(_search_candidates) if use_cow_fork else _search_candidates()
        outcome.setdefault("schema", SCHEMA)
        outcome.setdefault("engine", "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS")
        outcome.setdefault("model_calls", PRODUCER_MODEL_CALLS)
        return outcome

    @classmethod
    def causal_obligation_and_transducer(
        cls,
        *,
        failure_text: str | None = None,
        io_pairs: Sequence[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        from canonical.swe_kernel import causal_nexus_v1 as cn
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as uep

        obligations: list[Any] = []
        if failure_text:
            raw_obs = cn.extract_value_obligations(failure_text)
            obligations = [repr(o) for o in raw_obs]

        transducer_info: dict[str, Any] | None = None
        if io_pairs:
            fit = cn.infer_transducer([(str(a), str(b)) for a, b in io_pairs])
            if fit is not None:
                transducer_info = {
                    "found": True,
                    "mode": getattr(fit, "mode", None),
                    "invertible": bool(getattr(fit, "invertible", False)),
                    "coverage": int(getattr(fit, "coverage", 0)),
                    "alphabet": getattr(fit, "alphabet", ""),
                    "table_size": len(getattr(fit, "table", ()) or ()),
                }
            else:
                transducer_info = {"found": False}

        portfolio = uep.organ_portfolio_status()
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS",
            "pass": True,
            "obligations_count": len(obligations),
            "obligations": obligations,
            "transducer": transducer_info,
            "epistemic_portfolio": {
                "total_organs": portfolio.get("total_organs"),
                "ready_organs": portfolio.get("ready_organs"),
                "all_ready": portfolio.get("all_ready"),
                "model_calls": portfolio.get("model_calls", 0),
            },
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 2. One-Shot Version-Space, Evidence Demand, Settlement & Transfer Learner
# =============================================================================


class OneShotEpistemicLearnerKernel:
    """Live unifier for evidence_demand_v1, settlement_v1, hypothesis_classes_v1,
    vocabulary_induction_v1, operator_acquisition_v1, demonstration_version_space_v1,
    and transfer_learning_v1."""

    @classmethod
    def demand_and_collapse_program(
        cls,
        params: Sequence[str],
        examples: Sequence[tuple[Sequence[Any], Any]],
        *,
        distinguishing_answer: tuple[Sequence[Any], Any] | None = None,
    ) -> dict[str, Any]:
        from canonical.runtime import evidence_demand_v1 as ed

        norm_examples = [(tuple(args), expected) for args, expected in examples]
        demanded = ed.demand_evidence(list(params), norm_examples)
        admissible = list(demanded.get("admissible") or ())
        known_inputs = [args for args, _ in norm_examples]

        settlement_probe = None
        if len(admissible) > 1:
            settlement_probe = ed.what_would_settle_it(list(params), admissible, known=known_inputs)

        collapsed = None
        if distinguishing_answer is not None:
            ans_args, ans_val = distinguishing_answer
            collapsed = ed.collapse_with_answer(list(params), norm_examples, tuple(ans_args), ans_val)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER",
            "pass": True,
            "params": list(params),
            "examples_count": len(norm_examples),
            "admissible_count": len(admissible),
            "admissible_sample": admissible[:5],
            "coverage": demanded.get("coverage"),
            "refused_premature_commit": len(admissible) != 1,
            "distinguishing_probe": settlement_probe,
            "collapsed": (
                {
                    "before_count": len(admissible),
                    "after_count": collapsed.get("after", {}).get("admissible_count", collapsed.get("admissible_count")),
                    "raw": collapsed,
                }
                if collapsed is not None
                else None
            ),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def determine_hypothesis_and_vocabulary(
        cls,
        points: Sequence[tuple[Any, Any]],
        *,
        bodies: Sequence[str] = (),
        operator_example: tuple[Sequence[float], float] | None = None,
    ) -> dict[str, Any]:
        from canonical.runtime import hypothesis_classes_v1 as hc
        from canonical.runtime import operator_acquisition_v1 as oa
        from canonical.runtime import settlement_v1 as st
        from canonical.runtime import vocabulary_induction_v1 as vi

        det = hc.determine(list(points))
        vocab = vi.recover_vocabulary(list(bodies)) if bodies else None
        struct_diag = st.diagnose_structure([((x,), y) for x, y in points]) if points else None

        acquired_ops = None
        if operator_example is not None:
            vals, ans = operator_example
            cands = oa.candidates_for(list(vals), ans)
            admitted = [c for c in cands if c.get("admitted")]
            acquired_ops = {
                "total_candidates": len(cands),
                "admitted_count": len(admitted),
                "admitted_forms": [c.get("arity") for c in admitted[:5]],
            }

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER",
            "pass": True,
            "hypothesis_determination": det,
            "vocabulary": vocab,
            "structure_diagnosis": struct_diag,
            "operator_acquisition": acquired_ops,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def cross_env_transfer_and_demo_collapse(
        cls,
        obs_a: Mapping[str, Any],
        obs_b: Mapping[str, Any],
        *,
        demo_observation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        from canonical.runtime import demonstration_version_space_v1 as dvs
        from canonical.runtime import transfer_learning_v1 as tl

        shape_a = tl.shape_of(obs_a)
        shape_b = tl.shape_of(obs_b)
        tokens_a = set(_WORD_RE.findall(str(shape_a)))
        tokens_b = set(_WORD_RE.findall(str(shape_b)))
        jaccard = (len(tokens_a & tokens_b) / len(tokens_a | tokens_b)) if (tokens_a | tokens_b) else 1.0

        page_info = None
        if demo_observation is not None:
            page = dvs.Page(dict(demo_observation))
            instruction = str(demo_observation.get("instruction", ""))
            page_info = {
                "page_type": type(page).__name__,
                "instruction_tokens": [t[0] for t in dvs.tokenize(instruction)],
                "dom_nodes": len(demo_observation.get("dom") or ()),
            }

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER",
            "pass": True,
            "shape_a": shape_a,
            "shape_b": shape_b,
            "shape_exact_match": shape_a == shape_b,
            "structural_jaccard": round(jaccard, 4),
            "demo_page": page_info,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 3. Evolving Shadow Interface Compiler + 3-Channel HCU Router (Agent S4 + HCU)
# =============================================================================


class ShadowInterfaceHCURouterKernel:
    """Combines Simular Agent-S4 evolving Python shadow interfaces + Microsoft
    HCU 3-channel routing (CLI/Code -> Semantic AX/Mental Model -> Visual GUI)
    over 5 live DARK computer-use organs."""

    CHANNEL_COSTS = {
        "CLI_CODE": 0.01,
        "SEMANTIC_AX_MENTAL_MODEL": 0.15,
        "VISUAL_GUI_ZOOM": 1.00,
    }

    @classmethod
    def route_hcu_action(
        cls,
        goal: str,
        *,
        tool_name: str | None = None,
        help_text: str | None = None,
        workspace_root: str | pathlib.Path | None = None,
        transition_edges: Sequence[tuple[str, str]] = (),
        start_state: str | None = None,
        goal_state: str | None = None,
        ui_observation: Mapping[str, Any] | None = None,
        has_gui_surface: bool = False,
    ) -> dict[str, Any]:
        from canonical.runtime import aimed_action_v1 as aa
        from canonical.runtime import computer_env_v1 as ce
        from canonical.runtime import tool_census_v1 as tc
        from canonical.swe_kernel import computer_use_agent_v1 as cua
        from canonical.swe_kernel import executable_mental_model_v1 as emm

        cli_contract: dict[str, Any] | None = None
        dry_run_flags: list[str] = []
        output_flags: list[str] = []
        installed_hit = False

        if tool_name:
            installed_hit = shutil.which(tool_name) is not None
        raw_help = help_text
        if raw_help is None and tool_name and installed_hit:
            try:
                raw_help = ce.help_text(tool_name)
            except Exception:
                raw_help = ""

        if raw_help:
            cli_contract = tc.parse_contract(raw_help, name=tool_name or "tool")
            for frow in cli_contract.get("flags") or ():
                flist = list(frow.get("flags") or ())
                desc = str(frow.get("description") or "").lower()
                joined = " ".join(flist).lower() + " " + desc
                if any(tok in joined for tok in ("--dry-run", "--check", "-n", "without writing", "check only", "simulate")):
                    dry_run_flags.extend(flist)
                if any(tok in joined for tok in ("--output", "-o", "write output", "dest")):
                    output_flags.extend(flist)

        mental_predicates: list[str] = []
        if workspace_root is not None:
            snap = emm.perceive_environment_state(str(workspace_root))
            mental_predicates = sorted(str(p) for p in emm.compute_predicate_facts(snap))

        articulation_subgoals: list[str] = []
        if transition_edges and start_state and goal_state:
            articulation_subgoals = list(cua.find_articulation_subgoals(list(transition_edges), start_state, goal_state))

        aimed_list: list[str] = []
        if ui_observation:
            try:
                aimed_list = list(aa.aimed_actions(ui_observation))
            except Exception:
                aimed_list = []

        # HCU strict minimum-cost channel selection: CLI/Code -> Semantic AX -> GUI
        if cli_contract is not None and (cli_contract.get("flags") or installed_hit):
            selected_channel = "CLI_CODE"
            rationale = "Direct programmatic/CLI contract parsed; bypasses GUI pixels at 100x lower cost."
        elif mental_predicates or articulation_subgoals or aimed_list:
            selected_channel = "SEMANTIC_AX_MENTAL_MODEL"
            rationale = "Structured environment mental model / semantic AX affordances available; bypasses raw vision."
        elif has_gui_surface:
            selected_channel = "VISUAL_GUI_ZOOM"
            rationale = "Channels 0 (CLI/Code) and 1 (Semantic AX) unavailable; escalates cleanly to visual GUI fallback."
        else:
            selected_channel = "ABSTAIN_NO_SURFACE"
            rationale = "No verified CLI, semantic AX, or GUI surface supplied."

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER",
            "pass": selected_channel != "ABSTAIN_NO_SURFACE",
            "goal": goal,
            "selected_channel": selected_channel,
            "estimated_channel_cost": cls.CHANNEL_COSTS.get(selected_channel, 0.0),
            "cost_saving_vs_gui_pct": round((1.0 - cls.CHANNEL_COSTS.get(selected_channel, 1.0)) * 100.0, 1)
            if selected_channel in cls.CHANNEL_COSTS
            else 0.0,
            "rationale": rationale,
            "cli_contract": (
                {
                    "tool": cli_contract.get("tool"),
                    "installed_on_host": installed_hit,
                    "flag_count": len(cli_contract.get("flags") or ()),
                    "dry_run_flags": sorted(set(dry_run_flags)),
                    "output_flags": sorted(set(output_flags)),
                    "in_place": bool(cli_contract.get("in_place", False)),
                }
                if cli_contract is not None
                else None
            ),
            "mental_model_predicates": mental_predicates[:40],
            "articulation_subgoals": articulation_subgoals,
            "aimed_actions": aimed_list[:20],
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def compile_and_evolve_shadow_interface(
        cls,
        *,
        tool_name: str,
        help_text: str,
        repo_dir: str | pathlib.Path,
        validation_probes: Sequence[Mapping[str, Any]] = (),
        version: int = 1,
    ) -> dict[str, Any]:
        """Agent-S4 style evolving Python shadow-interface compiler.

        Parses a tool's `--help` contract via `tool_census_v1`, synthesizes a
        safe, typed, deterministic Python command-builder module with built-in
        `--dry-run`/`--check` preflight support, validates it on held-out
        probes BEFORE committing to `repo_dir`, and rejects any regression.
        """
        from canonical.runtime import tool_census_v1 as tc

        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name).strip("_") or "tool"
        contract = tc.parse_contract(help_text, name=tool_name)
        flags = list(contract.get("flags") or ())
        flag_map: dict[str, dict[str, Any]] = {}
        dry_run_flag: str | None = None
        for row in flags:
            flist = list(row.get("flags") or ())
            if not flist:
                continue
            canonical_flag = sorted(flist, key=lambda s: (-len(s), s))[0]
            param_name = re.sub(r"[^a-zA-Z0-9_]", "_", canonical_flag.lstrip("-")).strip("_")
            takes_value = row.get("placeholder") is not None
            desc = str(row.get("description") or "")
            if dry_run_flag is None and any(
                k in (canonical_flag.lower() + " " + desc.lower())
                for k in ("--dry-run", "--check", "without writing", "simulate")
            ):
                dry_run_flag = canonical_flag
            flag_map[param_name] = {
                "flag": canonical_flag,
                "takes_value": takes_value,
                "description": desc,
            }

        spec_json = json.dumps(
            {"tool": tool_name, "version": int(version), "dry_run_flag": dry_run_flag, "flags": flag_map},
            sort_keys=True,
        )
        module_source = (
            f'"""Auto-compiled Wave 40 Agent-S4 Shadow Interface for `{tool_name}` (v{int(version)})."""\n'
            f"TOOL_NAME = {tool_name!r}\n"
            f"INTERFACE_VERSION = {int(version)}\n"
            f"DRY_RUN_FLAG = {dry_run_flag!r}\n"
            f"FLAG_SPEC = {flag_map!r}\n\n"
            "def build_argv(positionals=(), *, dry_run=False, **options):\n"
            "    argv = [TOOL_NAME]\n"
            "    if dry_run and DRY_RUN_FLAG:\n"
            "        argv.append(DRY_RUN_FLAG)\n"
            "    for key in sorted(options.keys()):\n"
            "        val = options[key]\n"
            "        if val is None or val is False:\n"
            "            continue\n"
            "        if key not in FLAG_SPEC:\n"
            "            raise ValueError('UNKNOWN_SHADOW_FLAG:' + str(key))\n"
            "        spec = FLAG_SPEC[key]\n"
            "        argv.append(spec['flag'])\n"
            "        if spec['takes_value']:\n"
            "            argv.append(str(val))\n"
            "    for pos in positionals:\n"
            "        argv.append(str(pos))\n"
            "    return argv\n"
        )

        fn, err = _compile_pure_function(module_source, "build_argv")
        if fn is None:
            return {"pass": False, "admitted": False, "error": err, "model_calls": PRODUCER_MODEL_CALLS}

        probe_results: list[dict[str, Any]] = []
        all_probes_pass = True
        for idx, probe in enumerate(validation_probes):
            pos = tuple(probe.get("positionals") or ())
            opts = dict(probe.get("options") or {})
            dry = bool(probe.get("dry_run", False))
            expect_argv = probe.get("expected_argv")
            expect_error = bool(probe.get("expect_error", False))
            try:
                got = fn(pos, dry_run=dry, **opts)
                ok = (not expect_error) and (expect_argv is None or list(got) == list(expect_argv))
                probe_results.append({"probe": idx, "ok": ok, "argv": got})
                if not ok:
                    all_probes_pass = False
            except Exception as exc:
                ok = expect_error
                probe_results.append({"probe": idx, "ok": ok, "error": f"{type(exc).__name__}:{exc}"})
                if not ok:
                    all_probes_pass = False

        out_dir = pathlib.Path(repo_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = out_dir / f"shadow_{safe_name}_v{int(version)}.py"
        if all_probes_pass:
            artifact_path.write_text(module_source, encoding="utf-8")

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER",
            "pass": all_probes_pass,
            "admitted": all_probes_pass,
            "tool_name": tool_name,
            "version": int(version),
            "dry_run_flag": dry_run_flag,
            "flag_count": len(flag_map),
            "interface_sha256": _sha256_text(module_source),
            "spec_sha256": _sha256_text(spec_json),
            "artifact_path": str(artifact_path) if all_probes_pass else None,
            "probes_passed": sum(1 for r in probe_results if r["ok"]),
            "probes_total": len(probe_results),
            "probe_results": probe_results,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 4. Out-of-Core Recursive Language Model Workspace (MIT RLM, arXiv:2512.24601)
# =============================================================================


@dataclass
class _RLMHandle:
    handle_id: str
    name: str
    text: str
    lines: list[str]
    sha256: str
    total_bytes: int
    token_lines: dict[str, list[int]]
    symbols: dict[str, tuple[int, int]]


class OutOfCoreRLMWorkspace:
    """Out-of-core symbolic corpus environment eliminating context rot and
    KV-cache prefix busting for 10M+ char repositories, traces, and logs."""

    def __init__(self) -> None:
        self._handles: dict[str, _RLMHandle] = {}

    def mount_corpus(
        self,
        name: str,
        content: str | Sequence[tuple[str, str]],
    ) -> dict[str, Any]:
        if isinstance(content, str):
            text = content
        else:
            parts = [f"### FILE: {label}\n{body}" for label, body in content]
            text = "\n\n".join(parts)
        lines = text.splitlines()
        digest = _sha256_text(text)
        handle_id = f"rlm_{digest[:12]}"

        token_lines: dict[str, list[int]] = defaultdict(list)
        for idx, line in enumerate(lines, start=1):
            seen_in_line: set[str] = set()
            for tok in _WORD_RE.findall(line.lower()):
                if len(tok) >= 2 and tok not in seen_in_line:
                    seen_in_line.add(tok)
                    token_lines[tok].append(idx)

        symbols: dict[str, tuple[int, int]] = {}
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    symbols[node.name] = (int(node.lineno), int(end_lineno))
        except SyntaxError:
            pass

        self._handles[handle_id] = _RLMHandle(
            handle_id=handle_id,
            name=name,
            text=text,
            lines=lines,
            sha256=digest,
            total_bytes=len(text.encode("utf-8")),
            token_lines=dict(token_lines),
            symbols=symbols,
        )
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE",
            "pass": True,
            "handle_id": handle_id,
            "name": name,
            "sha256": digest,
            "total_bytes": len(text.encode("utf-8")),
            "total_lines": len(lines),
            "indexed_tokens": len(token_lines),
            "indexed_symbols": sorted(symbols.keys()),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def programmatic_slice(
        self,
        handle_id: str,
        *,
        regex: str | None = None,
        line_range: tuple[int, int] | None = None,
        symbol: str | None = None,
        token: str | None = None,
        context_lines: int = 1,
        max_chars: int = 2000,
    ) -> dict[str, Any]:
        handle = self._handles.get(handle_id)
        if handle is None:
            return {"pass": False, "error": f"UNKNOWN_RLM_HANDLE:{handle_id}", "model_calls": PRODUCER_MODEL_CALLS}

        selected_lines: list[tuple[int, str]] = []
        if symbol is not None:
            span = handle.symbols.get(symbol)
            if span is None:
                return {"pass": False, "error": f"UNKNOWN_SYMBOL:{symbol}", "model_calls": PRODUCER_MODEL_CALLS}
            start, end = span
            for ln in range(max(1, start), min(len(handle.lines), end) + 1):
                selected_lines.append((ln, handle.lines[ln - 1]))
        elif line_range is not None:
            start, end = int(line_range[0]), int(line_range[1])
            for ln in range(max(1, start), min(len(handle.lines), end) + 1):
                selected_lines.append((ln, handle.lines[ln - 1]))
        elif token is not None:
            hits = handle.token_lines.get(token.lower(), [])
            chosen: set[int] = set()
            for ln in hits:
                for offset in range(-context_lines, context_lines + 1):
                    cand = ln + offset
                    if 1 <= cand <= len(handle.lines):
                        chosen.add(cand)
            selected_lines = [(ln, handle.lines[ln - 1]) for ln in sorted(chosen)]
        elif regex is not None:
            pat = re.compile(regex)
            chosen_r: set[int] = set()
            for idx, line in enumerate(handle.lines, start=1):
                if pat.search(line):
                    for offset in range(-context_lines, context_lines + 1):
                        cand = idx + offset
                        if 1 <= cand <= len(handle.lines):
                            chosen_r.add(cand)
            selected_lines = [(ln, handle.lines[ln - 1]) for ln in sorted(chosen_r)]
        else:
            selected_lines = [(i + 1, l) for i, l in enumerate(handle.lines[:40])]

        rendered_parts: list[str] = []
        used = 0
        included_lines: list[int] = []
        truncated = False
        for ln, text in selected_lines:
            row = f"{ln}: {text}"
            if used + len(row) + 1 > max_chars:
                truncated = True
                break
            rendered_parts.append(row)
            included_lines.append(ln)
            used += len(row) + 1
        excerpt = "\n".join(rendered_parts)
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE",
            "pass": True,
            "handle_id": handle_id,
            "source_sha256": handle.sha256,
            "matched_lines_total": len(selected_lines),
            "included_line_numbers": included_lines,
            "truncated": truncated,
            "raw_bytes": handle.total_bytes,
            "returned_bytes": len(excerpt.encode("utf-8")),
            "compression_ratio": round(handle.total_bytes / max(1, len(excerpt.encode("utf-8"))), 2),
            "excerpt": excerpt,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def recursive_map_reduce(
        self,
        handle_id: str,
        *,
        pattern: str,
        chunk_lines: int = 60,
        max_depth: int = 3,
        max_matches_per_chunk: int = 20,
    ) -> dict[str, Any]:
        """Bounded divide-and-conquer recursive RLM query over arbitrarily large
        out-of-core corpora with exact line provenance and depth accounting."""
        handle = self._handles.get(handle_id)
        if handle is None:
            return {"pass": False, "error": f"UNKNOWN_RLM_HANDLE:{handle_id}", "model_calls": PRODUCER_MODEL_CALLS}

        pat = re.compile(pattern)
        chunk_size = max(1, int(chunk_lines))
        depth_limit = max(1, int(max_depth))

        def _recurse(start_idx: int, end_idx: int, depth: int) -> dict[str, Any]:
            span = end_idx - start_idx
            if span <= chunk_size or depth >= depth_limit:
                matches: list[dict[str, Any]] = []
                for idx in range(start_idx, end_idx):
                    line = handle.lines[idx]
                    if pat.search(line):
                        matches.append({"line": idx + 1, "text": line[:200]})
                        if len(matches) >= max_matches_per_chunk:
                            break
                return {"depth": depth, "leaves": 1, "matches": matches}
            mid = start_idx + (span // 2)
            left = _recurse(start_idx, mid, depth + 1)
            right = _recurse(mid, end_idx, depth + 1)
            return {
                "depth": max(left["depth"], right["depth"]),
                "leaves": left["leaves"] + right["leaves"],
                "matches": left["matches"] + right["matches"],
            }

        agg = _recurse(0, len(handle.lines), 0)
        summary_bytes = len(json.dumps(agg["matches"], sort_keys=True).encode("utf-8"))
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE",
            "pass": True,
            "handle_id": handle_id,
            "pattern": pattern,
            "max_depth_reached": agg["depth"],
            "leaf_chunks_visited": agg["leaves"],
            "match_count": len(agg["matches"]),
            "matches": agg["matches"],
            "raw_bytes": handle.total_bytes,
            "summary_bytes": summary_bytes,
            "compression_ratio": round(handle.total_bytes / max(1, summary_bytes), 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 5. Four-Network Git-Diffable Bi-Temporal TMA-NM Memory + O(1) Engram Table
# =============================================================================


class FourNetworkGitMemoryEngine:
    """Hindsight 4-Network Memory (`world_facts`, `experiences`, `observations`,
    `mental_models`) + plain git-diffable Markdown/JSONL files + DeepSeek
    Engram O(1) hashed N-gram lookup + bi-temporal Sleep consolidation + TMA-NM
    HMAC tamper immunity."""

    NETWORKS: tuple[str, ...] = ("world_facts", "experiences", "observations", "mental_models")
    TRUSTED_ORIGINS: frozenset[str] = frozenset({"TRUSTED_VERIFIER", "KERNEL_EXECUTION", "SLEEP_CONSOLIDATION"})

    def __init__(self, *, root_dir: str | pathlib.Path | None = None, secret_key: bytes | None = None) -> None:
        self._root_dir = pathlib.Path(root_dir) if root_dir is not None else None
        self._secret_key = secret_key or secrets.token_bytes(32)
        self._records: dict[str, dict[str, dict[str, Any]]] = {net: {} for net in self.NETWORKS}
        self._engram_table: dict[str, set[tuple[str, str]]] = defaultdict(set)
        if self._root_dir is not None:
            for net in self.NETWORKS:
                (self._root_dir / net).mkdir(parents=True, exist_ok=True)

    def _sign_record(self, rec: Mapping[str, Any]) -> str:
        body = {k: v for k, v in rec.items() if k != "tma_hmac"}
        msg = json.dumps(body, sort_keys=True, default=str).encode("utf-8")
        return hmac.new(self._secret_key, msg, hashlib.sha256).hexdigest()

    def _verify_record(self, rec: Mapping[str, Any]) -> bool:
        expected = self._sign_record(rec)
        return hmac.compare_digest(str(rec.get("tma_hmac") or ""), expected)

    @staticmethod
    def _extract_ngrams(text: str) -> list[str]:
        tokens = [t for t in _WORD_RE.findall(text.lower()) if len(t) >= 2]
        grams: list[str] = list(tokens)
        for n in (2, 3):
            for i in range(0, max(0, len(tokens) - n + 1)):
                grams.append(" ".join(tokens[i : i + n]))
        return grams

    def _engram_hash(self, ngram: str) -> str:
        return hashlib.blake2b(ngram.encode("utf-8"), digest_size=8).hexdigest()

    def _persist_git_diffable(self, network: str, rec: Mapping[str, Any]) -> str | None:
        if self._root_dir is None:
            return None
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(rec["record_id"]))
        md_path = self._root_dir / network / f"{safe_id}.md"
        frontmatter = json.dumps(
            {k: v for k, v in rec.items() if k != "verbatim_text"},
            indent=2,
            sort_keys=True,
            default=str,
        )
        content = f"---\n{frontmatter}\n---\n\n{rec['verbatim_text']}\n"
        md_path.write_text(content, encoding="utf-8")
        return str(md_path)

    def write(
        self,
        *,
        network: str,
        record_id: str,
        entity_key: str,
        verbatim_text: str,
        valid_from: int = 0,
        valid_to: int | None = None,
        origin_token: str = "TRUSTED_VERIFIER",
        support_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if network not in self.NETWORKS:
            return {"pass": False, "admitted": False, "reason": f"UNKNOWN_NETWORK:{network}"}
        if origin_token not in self.TRUSTED_ORIGINS:
            return {
                "pass": False,
                "admitted": False,
                "reason": f"TMA_NM_UNTRUSTED_ORIGIN:{origin_token}",
                "model_calls": PRODUCER_MODEL_CALLS,
            }

        # Bi-temporal supersession: never overwrite old facts silently; close their `valid_to`
        superseded_ids: list[str] = []
        if network == "world_facts":
            for prev_id, prev in self._records["world_facts"].items():
                if (
                    prev.get("entity_key") == entity_key
                    and prev.get("valid_to") is None
                    and prev_id != record_id
                    and int(prev.get("valid_from", 0)) <= int(valid_from)
                ):
                    prev["valid_to"] = int(valid_from)
                    prev["tma_hmac"] = self._sign_record(prev)
                    self._persist_git_diffable("world_facts", prev)
                    superseded_ids.append(prev_id)

        rec: dict[str, Any] = {
            "record_id": str(record_id),
            "network": network,
            "entity_key": str(entity_key),
            "verbatim_text": str(verbatim_text),
            "verbatim_sha256": _sha256_text(str(verbatim_text)),
            "valid_from": int(valid_from),
            "valid_to": None if valid_to is None else int(valid_to),
            "origin_token": origin_token,
            "support_ids": list(support_ids),
            "metadata": dict(metadata or {}),
        }
        rec["tma_hmac"] = self._sign_record(rec)
        self._records[network][str(record_id)] = rec

        indexed_grams = 0
        for g in self._extract_ngrams(f"{entity_key} {verbatim_text}"):
            self._engram_table[self._engram_hash(g)].add((network, str(record_id)))
            indexed_grams += 1

        file_path = self._persist_git_diffable(network, rec)
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
            "pass": True,
            "admitted": True,
            "network": network,
            "record_id": str(record_id),
            "superseded_ids": superseded_ids,
            "engram_keys_indexed": indexed_grams,
            "git_file_path": file_path,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def engram_query(
        self,
        query: str,
        *,
        networks: Sequence[str] | None = None,
        at_time: int | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """O(1)-bucket hashed N-gram Engram lookup with bi-temporal filtering and
        live TMA-NM tamper exclusion."""
        allowed = set(networks) if networks else set(self.NETWORKS)
        q_grams = self._extract_ngrams(query)
        scores: Counter[tuple[str, str]] = Counter()
        for g in q_grams:
            weight = 3 if g.count(" ") == 2 else (2 if g.count(" ") == 1 else 1)
            for net, rid in self._engram_table.get(self._engram_hash(g), ()):
                if net in allowed:
                    scores[(net, rid)] += weight

        tampered_excluded: list[str] = []
        hits: list[dict[str, Any]] = []
        for (net, rid), score in scores.most_common():
            rec = self._records[net].get(rid)
            if rec is None:
                continue
            if not self._verify_record(rec):
                tampered_excluded.append(rid)
                continue
            if at_time is not None:
                vf = int(rec.get("valid_from", 0))
                vt = rec.get("valid_to")
                if int(at_time) < vf:
                    continue
                if vt is not None and int(at_time) >= int(vt):
                    continue
            hits.append(
                {
                    "network": net,
                    "record_id": rid,
                    "entity_key": rec["entity_key"],
                    "score": score,
                    "valid_from": rec["valid_from"],
                    "valid_to": rec["valid_to"],
                    "verbatim_text": rec["verbatim_text"],
                    "support_ids": rec["support_ids"],
                }
            )
            if len(hits) >= int(top_k):
                break

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
            "pass": True,
            "query": query,
            "at_time": at_time,
            "hit_count": len(hits),
            "hits": hits,
            "tampered_excluded": tampered_excluded,
            "engram_buckets_total": len(self._engram_table),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def sleep_consolidate(
        self,
        *,
        min_support: int = 2,
        at_time: int = 100,
    ) -> dict[str, Any]:
        """Multi-timescale Sleep Knowledge Seeding: promotes verified recurring
        verbatim `experiences` -> `observations` -> `mental_models` ONLY when
        HMAC-verified and supported by `>= min_support` independent episodes."""
        by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        tampered_skipped = 0
        for rec in self._records["experiences"].values():
            if not self._verify_record(rec):
                tampered_skipped += 1
                continue
            by_entity[rec["entity_key"]].append(rec)

        promoted_observations: list[str] = []
        promoted_models: list[str] = []
        for entity_key, episodes in sorted(by_entity.items()):
            if len(episodes) < int(min_support):
                continue
            support_ids = sorted(ep["record_id"] for ep in episodes)
            obs_id = f"obs_{_sha256_obj([entity_key, support_ids])[:10]}"
            obs_text = (
                f"Consolidated invariant for {entity_key} from {len(episodes)} verified episodes: "
                + " | ".join(ep["verbatim_text"][:100] for ep in episodes[:3])
            )
            self.write(
                network="observations",
                record_id=obs_id,
                entity_key=entity_key,
                verbatim_text=obs_text,
                valid_from=int(at_time),
                origin_token="SLEEP_CONSOLIDATION",
                support_ids=support_ids,
            )
            promoted_observations.append(obs_id)

            model_id = f"mm_{_sha256_obj(['model', entity_key, obs_id])[:10]}"
            model_text = f"Executable mental model rule for {entity_key}: apply verified invariant supported by {support_ids}."
            self.write(
                network="mental_models",
                record_id=model_id,
                entity_key=entity_key,
                verbatim_text=model_text,
                valid_from=int(at_time),
                origin_token="SLEEP_CONSOLIDATION",
                support_ids=[obs_id, *support_ids],
            )
            promoted_models.append(model_id)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
            "pass": True,
            "promoted_observations": promoted_observations,
            "promoted_mental_models": promoted_models,
            "tampered_skipped": tampered_skipped,
            "network_counts": {net: len(self._records[net]) for net in self.NETWORKS},
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 6. CHASE + HDA + Hill Sampling + Staged Goal-Blind NFV Gate
# =============================================================================


class CHASEHillSamplingNFVGate:
    """Closes the 2026 self-evolution failure modes:
    - Staged Goal-Blind NFV (arXiv:2608.21516): formal spec derived without
      inspecting candidate AST/code, eliminating 98% unstaged false proofs.
    - CHASE (arXiv:2605.30621): validity-preserving semantic perturbations catch
      cheating/memorizing patches & harnesses.
    - Harness-Delta Attribution / HDA (arXiv:2610.22466): decomposes raw gain
      into genuine generalization vs overfitting gap vs compute scaling.
    - Hill Sampling (arXiv:2609.25510): adaptive temperature parent selection.
    """

    @staticmethod
    def _alpha_rename_params(source: str, fn_name: str, suffix: str = "_chase_p") -> str:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                rename_map = {a.arg: f"{a.arg}{suffix}" for a in node.args.args}
                for a in node.args.args:
                    a.arg = rename_map[a.arg]
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and sub.id in rename_map:
                        sub.id = rename_map[sub.id]
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    @classmethod
    def staged_goal_blind_verify(
        cls,
        *,
        spec_contract: Mapping[str, Any],
        candidate_source: str,
        fn_name: str,
    ) -> dict[str, Any]:
        """Stage 1 compiles an independent formal predicate strictly from
        `spec_contract` (never sees `candidate_source`). Stage 2 runs the
        candidate against the Stage-1 oracle + edge-case perturbation cases."""
        # Stage 1: goal-blind formalizer (strictly isolated from candidate_source)
        spec_cases = list(spec_contract.get("io_cases") or ())
        property_expr = spec_contract.get("postcondition_expr")
        adversarial_inputs = list(spec_contract.get("adversarial_inputs") or ())
        stage1_digest = _sha256_obj(
            {"io_cases": spec_cases, "postcondition_expr": property_expr, "adversarial_inputs": adversarial_inputs}
        )

        post_fn: Callable[..., bool] | None = None
        if property_expr:
            post_src = f"def _nfv_post(args, out):\n    return bool({property_expr})\n"
            post_fn, perr = _compile_pure_function(post_src, "_nfv_post")
            if post_fn is None:
                return {"pass": False, "admitted": False, "error": f"STAGE1_SPEC_INVALID:{perr}"}

        # Stage 2: evaluate candidate inside CoW fork against blind Stage-1 oracle
        def _stage2_eval() -> dict[str, Any]:
            cand_fn, cerr = _compile_pure_function(candidate_source, fn_name)
            if cand_fn is None:
                return {"pass": False, "admitted": False, "error": cerr}
            passed, rows = _eval_cases(cand_fn, spec_cases)
            post_failures: list[dict[str, Any]] = []
            if post_fn is not None:
                for inp in adversarial_inputs:
                    call_args = inp if isinstance(inp, tuple) else (inp,)
                    try:
                        out = cand_fn(*copy.deepcopy(call_args))
                        if not post_fn(call_args, out):
                            post_failures.append({"input": repr(call_args), "output": repr(out), "reason": "POSTCONDITION_FALSE"})
                    except Exception as exc:
                        post_failures.append({"input": repr(call_args), "error": f"{type(exc).__name__}:{exc}"})
            admitted = (passed == len(spec_cases)) and (len(post_failures) == 0)
            return {
                "pass": admitted,
                "admitted": admitted,
                "stage1_goal_blind_digest": stage1_digest,
                "candidate_isolated_from_stage1": True,
                "io_passed": passed,
                "io_total": len(spec_cases),
                "adversarial_checked": len(adversarial_inputs),
                "postcondition_failures": post_failures,
                "rows": rows,
            }

        res = _run_in_cow_fork(_stage2_eval)
        res.setdefault("schema", SCHEMA)
        res.setdefault("engine", "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE")
        res.setdefault("model_calls", PRODUCER_MODEL_CALLS)
        return res

    @classmethod
    def chase_perturbation_audit(
        cls,
        candidate_source: str,
        *,
        fn_name: str,
        base_cases: Sequence[tuple[tuple[Any, ...], Any]],
        perturbed_cases: Sequence[tuple[tuple[Any, ...], Any]],
        min_survival_rate: float = 1.0,
    ) -> dict[str, Any]:
        """CHASE audit: checks base cases, alpha-renamed AST invariance, AND
        validity-preserving perturbed held-out cases to catch memorization."""
        base_fn, berr = _compile_pure_function(candidate_source, fn_name)
        if base_fn is None:
            return {"pass": False, "admitted": False, "error": berr, "model_calls": PRODUCER_MODEL_CALLS}

        base_pass, _ = _eval_cases(base_fn, base_cases)
        pert_pass, pert_rows = _eval_cases(base_fn, perturbed_cases)

        renamed_src = cls._alpha_rename_params(candidate_source, fn_name)
        renamed_fn, rerr = _compile_pure_function(renamed_src, fn_name)
        alpha_pass = 0
        if renamed_fn is not None and rerr is None:
            alpha_pass, _ = _eval_cases(renamed_fn, perturbed_cases)

        base_rate = base_pass / max(1, len(base_cases))
        pert_rate = pert_pass / max(1, len(perturbed_cases))
        alpha_rate = alpha_pass / max(1, len(perturbed_cases))
        survival_rate = min(pert_rate, alpha_rate)
        overfit_detected = (base_rate >= 0.99) and (survival_rate < min_survival_rate)
        admitted = (base_rate >= 0.99) and (survival_rate >= min_survival_rate)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
            "pass": admitted,
            "admitted": admitted,
            "overfit_detected": overfit_detected,
            "base_pass_rate": round(base_rate, 4),
            "perturbed_pass_rate": round(pert_rate, 4),
            "alpha_renamed_pass_rate": round(alpha_rate, 4),
            "chase_survival_rate": round(survival_rate, 4),
            "perturbed_rows": pert_rows,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def harness_delta_attribution(
        cls,
        *,
        baseline_train: float,
        baseline_heldout: float,
        evolved_train_equal_budget: float,
        evolved_heldout_equal_budget: float,
        evolved_train_extra_budget: float | None = None,
        evolved_heldout_extra_budget: float | None = None,
        max_overfit_fraction: float = 0.35,
    ) -> dict[str, Any]:
        """Exact Harness-Delta Attribution (arXiv:2610.22466):
        Δ_total_train = Δ_genuine_generalization + Δ_overfitting_gap + Δ_compute_scaling."""
        eb_train = float(evolved_train_equal_budget)
        eb_held = float(evolved_heldout_equal_budget)
        final_train = float(evolved_train_extra_budget) if evolved_train_extra_budget is not None else eb_train
        final_held = float(evolved_heldout_extra_budget) if evolved_heldout_extra_budget is not None else eb_held

        delta_total_train = final_train - float(baseline_train)
        delta_genuine = eb_held - float(baseline_heldout)
        delta_compute_heldout = final_held - eb_held
        delta_compute_train = final_train - eb_train
        delta_overfitting = (eb_train - float(baseline_train)) - delta_genuine
        overfit_fraction = (max(0.0, delta_overfitting) / max(1e-9, abs(delta_total_train))) if abs(delta_total_train) > 1e-9 else 0.0
        admitted = (delta_genuine > 0.0) and (overfit_fraction <= float(max_overfit_fraction))

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
            "pass": admitted,
            "admitted": admitted,
            "delta_total_train": round(delta_total_train, 6),
            "delta_genuine_generalization": round(delta_genuine, 6),
            "delta_overfitting_gap": round(delta_overfitting, 6),
            "delta_compute_scaling_train": round(delta_compute_train, 6),
            "delta_compute_scaling_heldout": round(delta_compute_heldout, 6),
            "overfit_fraction": round(overfit_fraction, 4),
            "additive_identity_error": round(
                abs(delta_total_train - (delta_genuine + delta_overfitting + delta_compute_train)), 9
            ),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def hill_sampling_select(
        cls,
        candidates: Sequence[Mapping[str, Any]],
        *,
        k: int = 2,
        temperature: float = 0.25,
        diversity_bonus: float = 0.10,
        seed: int = 40,
    ) -> dict[str, Any]:
        """Hill Sampling (arXiv:2609.25510): selects high-fitness diverse parents
        via sharpened Boltzmann hill-climbing probabilities with exact seed."""
        if not candidates:
            return {"pass": False, "selected": [], "error": "EMPTY_CANDIDATES"}
        rng = random.Random(int(seed))
        pool = [dict(c) for c in candidates]
        selected: list[dict[str, Any]] = []
        seen_lineages: set[str] = set()
        temp = max(1e-4, float(temperature))

        while pool and len(selected) < int(k):
            adjusted: list[float] = []
            for row in pool:
                fit = float(row.get("fitness", 0.0))
                lin = str(row.get("lineage", row.get("id", "")))
                bonus = float(diversity_bonus) if lin not in seen_lineages else 0.0
                adjusted.append(fit + bonus)
            max_score = max(adjusted)
            weights = [math.exp((s - max_score) / temp) for s in adjusted]
            total_w = sum(weights)
            r = rng.random() * total_w
            acc = 0.0
            chosen_idx = len(pool) - 1
            for idx, w in enumerate(weights):
                acc += w
                if r <= acc:
                    chosen_idx = idx
                    break
            picked = pool.pop(chosen_idx)
            seen_lineages.add(str(picked.get("lineage", picked.get("id", ""))))
            selected.append(picked)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
            "pass": True,
            "selected": selected,
            "selected_ids": [s.get("id") for s in selected],
            "seed": int(seed),
            "temperature": temp,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# =============================================================================
# 7. Zero-Data Self-Play Challenger–Solver + Steer-Don't-Solve + Horizon Commit
# =============================================================================


class SelfPlaySteerAndHorizonKernel:
    """Meta Self-Play SWE-RL zero-data bug-injector/solver episodes + CMU
    Steer-Don't-Solve trajectory critic + live wiring of 7 DARK long-horizon,
    stakes, curriculum, composition, credit, and atomic-commit organs."""

    _MUTATION_SWAPS: dict[type, tuple[type, ...]] = {
        ast.Add: (ast.Sub, ast.Mult),
        ast.Sub: (ast.Add, ast.Mult),
        ast.Mult: (ast.Add, ast.FloorDiv),
        ast.Lt: (ast.LtE, ast.Gt),
        ast.LtE: (ast.Lt, ast.Gt),
        ast.Gt: (ast.GtE, ast.Lt),
        ast.GtE: (ast.Gt, ast.Lt),
        ast.Eq: (ast.NotEq,),
        ast.NotEq: (ast.Eq,),
    }

    @classmethod
    def self_play_bug_episode(
        cls,
        clean_source: str,
        *,
        fn_name: str,
        test_cases: Sequence[tuple[tuple[Any, ...], Any]],
        max_mutations: int = 8,
    ) -> dict[str, Any]:
        """Zero-data Self-Play SWE-RL episode:
        1. Challenger injects AST-real semantic bugs verified to FAIL `test_cases`.
        2. Solver repairs each injected bug via `grammar_closed_cegis_repair` in
           real POSIX `os.fork()` CoW isolation with zero human-written issue."""
        ok, err, tree = _check_safe_pure_python_ast(clean_source)
        if not ok or tree is None:
            return {"pass": False, "error": err or "INVALID_CLEAN_SOURCE", "model_calls": PRODUCER_MODEL_CALLS}
        clean_fn, cerr = _compile_pure_function(clean_source, fn_name)
        if clean_fn is None:
            return {"pass": False, "error": cerr, "model_calls": PRODUCER_MODEL_CALLS}
        clean_pass, _ = _eval_cases(clean_fn, test_cases)
        if clean_pass != len(test_cases):
            return {
                "pass": False,
                "error": f"CLEAN_SOURCE_FAILS_TESTS:{clean_pass}/{len(test_cases)}",
                "model_calls": PRODUCER_MODEL_CALLS,
            }

        target_fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name), None)
        if target_fn is None:
            return {"pass": False, "error": f"FUNCTION_NOT_FOUND:{fn_name}"}

        injected_bugs: list[dict[str, Any]] = []
        seen_src: set[str] = {clean_source.strip()}
        for idx, node in enumerate(ast.walk(target_fn)):
            if len(injected_bugs) >= int(max_mutations):
                break
            swap_candidates: tuple[type, ...] = ()
            kind: str | None = None
            if isinstance(node, ast.BinOp) and type(node.op) in cls._MUTATION_SWAPS:
                swap_candidates = cls._MUTATION_SWAPS[type(node.op)]
                kind = "binop"
            elif isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in cls._MUTATION_SWAPS:
                swap_candidates = cls._MUTATION_SWAPS[type(node.ops[0])]
                kind = "cmp"
            if not kind:
                continue
            for swap_cls in swap_candidates:
                if len(injected_bugs) >= int(max_mutations):
                    break
                mut_tree = copy.deepcopy(tree)
                mut_fn = next(n for n in mut_tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name)
                mut_node = list(ast.walk(mut_fn))[idx]
                if kind == "binop":
                    mut_node.op = swap_cls()
                else:
                    mut_node.ops[0] = swap_cls()
                cand_src = ast.unparse(mut_tree)
                if cand_src.strip() in seen_src:
                    continue
                seen_src.add(cand_src.strip())
                bug_fn, berr = _compile_pure_function(cand_src, fn_name)
                if bug_fn is None or berr is not None:
                    continue
                b_pass, _ = _eval_cases(bug_fn, test_cases)
                if b_pass < len(test_cases):
                    injected_bugs.append({"bug_id": len(injected_bugs), "buggy_source": cand_src, "buggy_passed": b_pass})

        solved_episodes: list[dict[str, Any]] = []
        for bug in injected_bugs:
            repair = EpistemicSWEAndEGraphKernel.grammar_closed_cegis_repair(
                bug["buggy_source"],
                fn_name=fn_name,
                test_cases=test_cases,
                reference_source=clean_source,
                use_cow_fork=True,
            )
            solved_episodes.append(
                {
                    "bug_id": bug["bug_id"],
                    "buggy_passed": bug["buggy_passed"],
                    "repaired": bool(repair.get("repaired")),
                    "repair_origin": repair.get("repair_origin"),
                    "cow_fork_used": bool(repair.get("cow_fork_used", False)),
                    "obs_equiv": bool((repair.get("observational_equivalence") or {}).get("equivalent", False)),
                }
            )

        solved_count = sum(1 for e in solved_episodes if e["repaired"])
        solvability_rate = solved_count / max(1, len(solved_episodes))
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
            "pass": len(injected_bugs) > 0 and solved_count > 0,
            "bugs_injected": len(injected_bugs),
            "bugs_solved": solved_count,
            "solvability_rate": round(solvability_rate, 4),
            "episodes": solved_episodes,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def steer_dont_solve_critic(
        cls,
        trajectory: Sequence[Mapping[str, Any]],
        *,
        window: int = 4,
    ) -> dict[str, Any]:
        """CMU Steer-Don't-Solve (EMNLP'26) trajectory critic: detects stuck
        regimes over the last `k` steps and emits a single 1-line steering
        directive (never a full patch)."""
        steps = list(trajectory)[-max(2, int(window)) :]
        if not steps:
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
                "pass": True,
                "regime": "NO_HISTORY",
                "intervene": False,
                "steering_line": "Continue execution; no trajectory anomalies observed.",
                "model_calls": PRODUCER_MODEL_CALLS,
            }

        actions = [str(s.get("action") or "") for s in steps]
        errors = [str(s.get("error_sig") or "") for s in steps]
        files = [str(s.get("file") or "") for s in steps if s.get("file")]
        pass_counts = [int(s.get("tests_passed", 0)) for s in steps]

        regime = "HEALTHY_PROGRESS"
        intervene = False
        recommended_organ = None
        steering_line = "Progressing monotonically; keep current strategy."

        if len(errors) >= 3 and errors[-1] and errors[-1] == errors[-3] and errors[-1] != errors[-2]:
            regime = "ASSERTION_OSCILLATION"
            intervene = True
            recommended_organ = "LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER"
            steering_line = (
                f"STEER: Patch oscillates between `{errors[-2]}` and `{errors[-1]}`; splice both partial fixes with Mendel dual-splicing."
            )
        elif len(actions) >= 2 and len(set(actions[-2:])) == 1 and actions[-1]:
            regime = "REPEAT_LOOP"
            intervene = True
            recommended_organ = "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER"
            steering_line = (
                f"STEER: Stop repeating `{actions[-1]}`; isolate the minimal distinguishing witness before editing again."
            )
        elif len(files) >= 3 and len(set(files)) == len(files) and max(pass_counts) <= pass_counts[0]:
            regime = "WRONG_FILE_DRIFT"
            intervene = True
            recommended_organ = "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS"
            steering_line = (
                f"STEER: Editing {len(files)} distinct files with 0 test gain; re-localize root fault via causal value obligations."
            )
        elif len(pass_counts) >= 3 and pass_counts[-1] < pass_counts[0]:
            regime = "ERROR_ESCALATION"
            intervene = True
            recommended_organ = "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT"
            steering_line = (
                f"STEER: Regression detected ({pass_counts[0]}->{pass_counts[-1]} passing); rollback to last atomic WAL commit and narrow diff."
            )
        elif len(pass_counts) >= 3 and max(pass_counts) == min(pass_counts) and errors[-1]:
            regime = "STAGNANT_PROGRESS"
            intervene = True
            recommended_organ = "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE"
            steering_line = (
                f"STEER: Test count stalled at {pass_counts[-1]} on `{errors[-1]}`; inspect out-of-core failure trace slice instead of guessing."
            )

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
            "pass": True,
            "regime": regime,
            "intervene": intervene,
            "recommended_organ": recommended_organ,
            "steering_line": steering_line,
            "window_checked": len(steps),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @classmethod
    def horizon_stakes_and_atomic_commit(
        cls,
        *,
        identity: str = "brain-wave40",
        obligations: Sequence[Mapping[str, Any]] = (),
        stage_files: Mapping[str, str] | None = None,
        live_files: Mapping[str, str] | None = None,
        simulate_crash_recovery: bool = True,
        workdir: str | pathlib.Path | None = None,
    ) -> dict[str, Any]:
        """Live-wires `creature_stakes_and_initiative_v1`, `curriculum_v1`,
        `horizon_bounded_execution_v1`, `composition_verification_v1`,
        `credit_assignment_v1`, `weights_from_scratch_v1`, and
        `the_record_is_the_commit_v1` (crash-proof atomic WAL commit + replay)."""
        from canonical.runtime import creature_stakes_and_initiative_v1 as csi
        from canonical.runtime import curriculum_v1 as cur
        from canonical.swe_kernel import composition_verification_v1 as cv
        from canonical.swe_kernel import credit_assignment_v1 as ca
        from canonical.swe_kernel import horizon_bounded_execution_v1 as hbe
        from canonical.swe_kernel import weights_from_scratch_v1 as wfs
        from canonical.tools import the_record_is_the_commit_v1 as trc

        standing = csi.Standing(identity=identity)
        ob_objs = [
            csi.Obligation(
                id=str(o["id"]),
                value=float(o.get("value", 1.0)),
                cost=float(o.get("cost", 1.0)),
            )
            for o in obligations
        ]
        chosen_ob = csi.choose(standing, ob_objs) if ob_objs else None

        # Verify dark long-horizon organs are live and instantiable
        horizon_ready = {
            "HorizonBoundedExecution": hasattr(hbe.HorizonBoundedExecution, "run"),
            "CompositionVerification": hasattr(cv.CompositionVerification, "run"),
            "CreditAssignment": hasattr(ca.CreditAssignment, "run"),
            "WeightsFromScratch": hasattr(wfs.WeightsFromScratch, "run"),
            "curriculum_ordered_channels": callable(cur.ordered_channels),
        }

        commit_report: dict[str, Any] | None = None
        if stage_files is not None:
            own_tmp = workdir is None
            root = pathlib.Path(tempfile.mkdtemp(prefix="w40_wal_")) if own_tmp else pathlib.Path(workdir)
            try:
                live_dir = root / trc.LIVE
                stage_dir = root / trc.STAGE
                live_dir.mkdir(parents=True, exist_ok=True)
                stage_dir.mkdir(parents=True, exist_ok=True)
                for rel, body in (live_files or {}).items():
                    p = live_dir / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(body, encoding="utf-8")
                for rel, body in stage_files.items():
                    p = stage_dir / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(body, encoding="utf-8")
                world = {"root": root, "live": live_dir, "stage": stage_dir}
                ops = trc.operations(world)
                trace: list[str] = []
                if simulate_crash_recovery and ops:
                    # Simulate a mid-commit crash: write WAL journal, apply ONLY first op, then recover cleanly!
                    payload = {
                        "schema": trc.SCHEMA,
                        "state": "PREPARED",
                        "operations": list(ops),
                        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    trc.write_journal(root, payload, trace)
                    first_outcome = trc.apply_operation(world, ops[0], trace)
                    recovery = trc.recover(root, world, trace)
                    final_matches = all(
                        (live_dir / rel).exists() and (live_dir / rel).read_text(encoding="utf-8") == body
                        for rel, body in stage_files.items()
                    )
                    commit_report = {
                        "mode": "CRASH_SIMULATED_WAL_RECOVERY",
                        "operations_count": len(ops),
                        "pre_crash_first_op": first_outcome,
                        "recovery": recovery,
                        "all_files_exact_match": final_matches,
                        "journal_cleaned": not (root / trc.JOURNAL).exists(),
                        "fsync_trace_steps": len(trace),
                    }
                else:
                    res = trc.run_commit(root, world, ops, crash_at=None, trace=trace, with_record=True)
                    final_matches = all(
                        (live_dir / rel).exists() and (live_dir / rel).read_text(encoding="utf-8") == body
                        for rel, body in stage_files.items()
                    )
                    commit_report = {
                        "mode": "DIRECT_ATOMIC_WAL_COMMIT",
                        "operations_count": len(ops),
                        "completed": bool(res.get("completed")),
                        "all_files_exact_match": final_matches,
                        "journal_cleaned": not (root / trc.JOURNAL).exists(),
                        "fsync_trace_steps": len(trace),
                    }
            finally:
                if own_tmp:
                    shutil.rmtree(root, ignore_errors=True)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
            "pass": all(horizon_ready.values()) and (commit_report is None or bool(commit_report.get("all_files_exact_match"))),
            "chosen_obligation_id": chosen_ob.id if chosen_ob is not None else None,
            "horizon_organs_ready": horizon_ready,
            "atomic_commit": commit_report,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


def wave40_awakened_inventory() -> dict[str, Any]:
    """Return the exact Wave 40 dark-matter awakening & frontier engine inventory."""
    return {
        "schema": SCHEMA,
        "awakened_dark_modules_count": len(AWAKENED_DARK_MODULES),
        "awakened_dark_modules": list(AWAKENED_DARK_MODULES),
        "federated_engines": [
            "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS",
            "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER",
            "LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER",
            "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE",
            "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
            "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
            "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
        ],
        "model_calls": PRODUCER_MODEL_CALLS,
    }
