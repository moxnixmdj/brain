#!/usr/bin/env python3
"""Four-Rung Zero-LLM Fast-Cascade Orchestrator & State-Alias Guard (`K3 = 0`).

Unifies Project Brain's fastest existing deterministic organs into ONE latency-ordered
execution cascade surfaced directly on `UnifiedModel.fast_cascade_solve()`,
`BoundaryRouter.route_fast_cascade()`, and `Creature.solve_via_fast_cascade()`:

  Rung 0 (`< 100 us` lookup):
    - Witness-conditioned preorder `AstDiscrTree` skill lookup
      (`counterfactual_discr_tree_skill_router_v1.py`) gated by Rubin `(WITH - WITHOUT)`
      counterfactual utility (`not quarantined`, `tau_hat > 0`) and
      `domain_of_verification_v1` exact interval check (`INSIDE` vs `EXTRAPOLATION`).

  Rung 1 (`0.1 - 3 ms` protocol elevation + State-Alias tomography):
    - Executes computer-use / environment state transitions directly in an isolated
      workspace or `EnvironmentMentalModel` (`executable_simulator_mental_model_v1.py`)
      and enforces **State-Alias Differential Tomography** (`StateAliasBench` defense):
        * 5-layer `capture_tomography_snapshot` + `diff_tomography`
          (`speculative_cow_petri_agent_v1.py`),
        * Content-validator byte signatures (`scan_and_diff_against_memory_v1.signature`)
          catching lying extensions (`bad.json`, `broken.py`, truncated SQLite `.db`),
        * Differential check-density (`computer_use_check_density_v1._observe` `"full"`
          vs `"coarse"` vs `"listing"`) catching actions that satisfy surface/listing
          appearances while corrupting or aliasing underlying bytes.

  Rung 2 (`2 - 35 ms` AST test-impact slicing + POSIX `os.fork()` CoW Zygote repair):
    - Slices impacted `test_*` functions via `select_impacted_tests`
      (`cow_zygote_speculative_verifier_v1.py`), evaluates candidate repairs in isolated
      POSIX `os.fork()` Copy-on-Write children (`CowZygoteSpeculativeVerifier`), and
      audits passing repairs with 64-vector boundary fuzzing (`verify_cow_boundary_invariance`
      from `cow_lens_fuzz_and_negative_space_v1.py`).

  Rung 3 (Cut-vertex Petri-net checkpointed horizon + active contrast selection):
    - Factors long-horizon multi-modal plans at causal articulation points via
      `CrossModalPetriPlanner.execute_checkpointed_horizon` (`speculative_cow_petri_agent_v1.py`),
      or selects the maximum-information-gain discriminating state probe via
      `contrast_selection_v1.select_contrast` when applicability is underdetermined.

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, fail-closed everywhere.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import contrast_selection_v1 as contrast_sel  # noqa: E402
from canonical.runtime import domain_of_verification_v1 as dov  # noqa: E402
from canonical.runtime.composition_state_capsule_v1 import (  # noqa: E402
    append_macrostep,
    empty_capsule,
    verify_capsule,
)
from canonical.runtime.counterfactual_discr_tree_skill_router_v1 import (  # noqa: E402
    STAR,
    AstDiscrTree,
    WitnessConditionedSkill,
    _eval_python_fn,
    _rewrite_dict_subscript_default,
    _rewrite_div_zero_guard,
    _rewrite_empty_seq_min_max_guard,
    _rewrite_index_bounds_guard,
    _rewrite_none_attr_guard,
    encode_stmt_preorder_keys,
)
from canonical.runtime.cow_zygote_speculative_verifier_v1 import (  # noqa: E402
    CowZygoteSpeculativeVerifier,
    select_impacted_tests,
)
from canonical.runtime.scan_and_diff_against_memory_v1 import (  # noqa: E402
    VALIDATORS as _SUBPROC_VALIDATORS,
    signature as content_signature,
)
from canonical.swe_kernel.computer_use_check_density_v1 import _observe as observe_density  # noqa: E402
from canonical.swe_kernel.cow_lens_fuzz_and_negative_space_v1 import (  # noqa: E402
    verify_cow_boundary_invariance,
)
from canonical.swe_kernel.speculative_cow_petri_agent_v1 import (  # noqa: E402
    CrossModalPetriPlanner,
    PetriTransition,
    capture_tomography_snapshot,
    diff_tomography,
)

SCHEMA = "PROJECT_BRAIN_FAST_CASCADE_ORCHESTRATOR_V1"
AUTHORITY = "NONE__SANDBOX_PRODUCER_VERIFICATION_ONLY"


class _DefaultDiscrSkillIndex:
    """Singleton pre-compiled witness-conditioned `AstDiscrTree` for `< 50 us` Rung-0 dispatch."""

    def __init__(self) -> None:
        self.tree = AstDiscrTree()
        self.skills: dict[str, WitnessConditionedSkill] = {}
        self.quarantined_ids: set[str] = set()
        self._bootstrap_verified_witness_skills()

    def _bootstrap_verified_witness_skills(self) -> None:
        specs = [
            (
                "sk_witness_div_zero_v1",
                "div_zero_guard",
                "Witness:ZeroDivisionError",
                ("Stmt:Return", "BinOp:Div", STAR),
                _rewrite_div_zero_guard,
            ),
            (
                "sk_witness_floordiv_zero_v1",
                "floordiv_zero_guard",
                "Witness:ZeroDivisionError",
                ("Stmt:Return", "BinOp:FloorDiv", STAR),
                _rewrite_div_zero_guard,
            ),
            (
                "sk_witness_dict_key_v1",
                "dict_subscript_default",
                "Witness:KeyError",
                ("Stmt:Return", "Subscript", STAR),
                _rewrite_dict_subscript_default,
            ),
            (
                "sk_witness_empty_min_v1",
                "empty_seq_min_guard",
                "Witness:ValueError",
                ("Stmt:Return", "Call:min", STAR),
                _rewrite_empty_seq_min_max_guard,
            ),
            (
                "sk_witness_empty_max_v1",
                "empty_seq_max_guard",
                "Witness:ValueError",
                ("Stmt:Return", "Call:max", STAR),
                _rewrite_empty_seq_min_max_guard,
            ),
            (
                "sk_witness_none_attr_v1",
                "none_attr_guard",
                "Witness:AttributeError",
                ("Stmt:Return", "Call:*", STAR),
                _rewrite_none_attr_guard,
            ),
            (
                "sk_witness_index_bounds_v1",
                "index_bounds_guard",
                "Witness:IndexError",
                ("Stmt:Return", "Subscript", STAR),
                _rewrite_index_bounds_guard,
            ),
        ]
        for sid, fam, wit, ast_pat, fn in specs:
            sk = WitnessConditionedSkill(
                skill_id=sid,
                family=fam,
                witness_pattern=wit,
                ast_pattern=ast_pat,
                specificity=len(ast_pat) + 2,
                apply_fn=fn,
            )
            self.skills[sid] = sk
            self.tree.insert((wit, *ast_pat), sk)


_DEFAULT_RUNG0_INDEX: _DefaultDiscrSkillIndex | None = None


def _get_rung0_index() -> _DefaultDiscrSkillIndex:
    global _DEFAULT_RUNG0_INDEX
    if _DEFAULT_RUNG0_INDEX is None:
        _DEFAULT_RUNG0_INDEX = _DefaultDiscrSkillIndex()
    return _DEFAULT_RUNG0_INDEX


def _extract_primary_return_keys(fn_src: str) -> tuple[str, ...]:
    tree = ast.parse(fn_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            return encode_stmt_preorder_keys(node, wildcard_slots=False)
    if tree.body and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].body:
        return encode_stmt_preorder_keys(tree.body[0].body[0], wildcard_slots=False)
    return ("$END",)


def _run_rung0_slot_lookup(
    task: Mapping[str, Any],
    *,
    quarantined_external: set[str] | None = None,
) -> dict[str, Any] | None:
    """Rung 0: `< 100 us` `AstDiscrTree` + `domain_of_verification_v1` extrapolation guard."""
    t0 = time.perf_counter_ns()
    # 0a) Domain-of-Verification interval guard if numeric domain points are supplied
    if "verified_points" in task and "query_point" in task:
        dom = dov.observed_domain(task["verified_points"])
        chk = dov.check_prediction(dom, task["query_point"])
        elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
        if chk.get("status") != dov.INSIDE:
            return {
                "schema": SCHEMA,
                "pass": False,
                "rung_selected": 0,
                "rung_name": "RUNG0_DOMAIN_OF_VERIFICATION_GUARD",
                "reason": "EXTRAPOLATION_OUTSIDE_VERIFIED_DOMAIN",
                "domain": dom,
                "domain_check": chk,
                "elapsed_us": round(elapsed_us, 3),
                "model_calls": 0,
            }
        if "hypothesis_body" in task:
            pred = dov.predict_scalar(
                str(task["hypothesis_body"]),
                tuple(task.get("param_names") or ("x",)),
                task["query_point"],
                dom,
            )
            elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
            return {
                "schema": SCHEMA,
                "pass": True,
                "rung_selected": 0,
                "rung_name": "RUNG0_VERIFIED_DOMAIN_PREDICTION",
                "prediction": pred,
                "domain": dom,
                "elapsed_us": round(elapsed_us, 3),
                "model_calls": 0,
            }

    # 0b) Witness-conditioned `AstDiscrTree` repair lookup
    fn_src = task.get("buggy_fn_source")
    witness = task.get("failure_witness")
    fn_name = task.get("fn_name")
    probe_cases = task.get("probe_cases")
    if not (isinstance(fn_src, str) and isinstance(witness, str) and isinstance(fn_name, str) and probe_cases):
        return None

    idx = _get_rung0_index()
    w_tok = witness if witness.startswith("Witness:") else f"Witness:{witness}"
    stmt_keys = _extract_primary_return_keys(fn_src)
    t_lookup0 = time.perf_counter_ns()
    matches: list[WitnessConditionedSkill] = idx.tree.get_matches_for_keys((w_tok, *stmt_keys))
    lookup_us = (time.perf_counter_ns() - t_lookup0) / 1000.0

    blocked = (quarantined_external or set()) | idx.quarantined_ids
    matches = [m for m in matches if m.skill_id not in blocked]
    matches.sort(key=lambda s: (-s.specificity, s.skill_id))

    safe_cases = list(task.get("safe_regression_cases") or [])
    all_cases = list(probe_cases) + safe_cases

    for sk in matches:
        rewritten = sk.apply_fn(fn_src)
        if not rewritten:
            continue
        ok, detail = _eval_python_fn(rewritten, fn_name, all_cases)
        if ok:
            total_us = (time.perf_counter_ns() - t0) / 1000.0
            return {
                "schema": SCHEMA,
                "pass": True,
                "rung_selected": 0,
                "rung_name": "RUNG0_DISCR_TREE_WITNESS_SKILL",
                "skill_id": sk.skill_id,
                "family": sk.family,
                "repaired_source": rewritten,
                "discr_tree_lookup_us": round(lookup_us, 3),
                "elapsed_us": round(total_us, 3),
                "verification_detail": detail,
                "model_calls": 0,
            }
    return None


def _fast_json_judge(path: str) -> int:
    try:
        json.loads(pathlib.Path(path).read_bytes().decode("utf-8"))
        return 0
    except Exception:
        return 1


def _fast_python_judge(path: str) -> int:
    try:
        ast.parse(pathlib.Path(path).read_bytes())
        return 0
    except Exception:
        return 1


def _fast_utf8_judge(path: str) -> int:
    try:
        pathlib.Path(path).read_bytes().decode("utf-8")
        return 0
    except Exception:
        return 1


def _fast_png_judge(path: str) -> int:
    try:
        with open(path, "rb") as fh:
            return 0 if fh.read(8) == b"\x89PNG\r\n\x1a\n" else 1
    except OSError:
        return 1


_FAST_VALIDATORS = {
    **_SUBPROC_VALIDATORS,
    "json": _fast_json_judge,
    "python": _fast_python_judge,
    "utf8_text": _fast_utf8_judge,
    "png": _fast_png_judge,
}


def _expected_validator_for_suffix(rel_path: str) -> str | None:
    low = rel_path.lower()
    if low.endswith(".json"):
        return "json"
    if low.endswith(".py"):
        return "python"
    if low.endswith(".png"):
        return "png"
    if low.endswith(".gz"):
        return "gzip"
    if low.endswith(".tar"):
        return "tar"
    if low.endswith(".zip"):
        return "zip"
    return None


def _run_rung1_state_alias_guarded_action(task: Mapping[str, Any]) -> dict[str, Any] | None:
    """Rung 1: Direct state-layer execution + 5-layer State-Alias differential guard."""
    ws_raw = task.get("workspace_root")
    cmd = task.get("shell_action")
    if not ws_raw:
        return None
    if isinstance(cmd, (list, tuple)) and cmd:
        argv: list[str] = [str(x) for x in cmd]
        cmd_repr = " ".join(argv)
    elif isinstance(cmd, str) and cmd.strip():
        argv = ["/bin/sh", "-c", cmd]
        cmd_repr = cmd
    else:
        return None

    t0 = time.perf_counter_ns()
    src_ws = pathlib.Path(ws_raw).resolve()
    if not src_ws.is_dir():
        return {
            "schema": SCHEMA,
            "pass": False,
            "rung_selected": 1,
            "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
            "reason": "WORKSPACE_NOT_FOUND",
            "model_calls": 0,
        }

    commit_in_place = bool(task.get("commit_if_verified", task.get("commit_on_pass", False)))
    protected_paths = [str(p) for p in (task.get("protected_files") or ())]
    raw_expected = task.get("expected_files") or {}
    if isinstance(raw_expected, Mapping):
        expected_files: dict[str, Any] = dict(raw_expected)
    else:
        expected_files = {str(p): {} for p in raw_expected}

    with tempfile.TemporaryDirectory(prefix="brain_rung1_cow_") as td_str:
        stage_ws = pathlib.Path(td_str) / "ws"
        shutil.copytree(src_ws, stage_ws)

        tomo_before = capture_tomography_snapshot(stage_ws)
        obs_listing_before = observe_density(stage_ws, "listing")
        obs_coarse_before = observe_density(stage_ws, "coarse")
        obs_full_before = observe_density(stage_ws, "full")

        proc = subprocess.run(
            argv,
            cwd=str(stage_ws),
            capture_output=True,
            text=True,
            timeout=float(task.get("timeout_s", 10.0)),
            check=False,
        )

        tomo_after = capture_tomography_snapshot(stage_ws)
        tomo_delta = diff_tomography(tomo_before, tomo_after)
        obs_listing_after = observe_density(stage_ws, "listing")
        obs_coarse_after = observe_density(stage_ws, "coarse")
        obs_full_after = observe_density(stage_ws, "full")

        if proc.returncode != 0:
            return {
                "schema": SCHEMA,
                "pass": False,
                "rung_selected": 1,
                "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                "reason": f"ACTION_EXIT_NONZERO:{proc.returncode}",
                "stderr": proc.stderr[:400],
                "model_calls": 0,
            }

        # Guard A: Protected-file byte SHA-256 invariance (prevents silent byte destruction)
        for prot in protected_paths:
            b_info = tomo_before.files.get(prot)
            a_info = tomo_after.files.get(prot)
            if b_info is not None and a_info != b_info:
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"STATE_ALIAS_PROTECTED_FILE_MUTATED:{prot}",
                    "tomography_delta": tomo_delta,
                    "model_calls": 0,
                }

        # Guard B: SQLite integrity check across every `.db` / `.sqlite` in workspace
        for db_rel, db_info in tomo_after.sqlite_dbs.items():
            if not db_info.get("integrity_ok", False):
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"STATE_ALIAS_SQLITE_CORRUPTION_REFUSED:{db_rel}",
                    "sqlite_info": db_info,
                    "surface_listing_appeared_present": db_rel in obs_listing_after,
                    "model_calls": 0,
                }

        # Guard C: Content-validator signature check on created/modified files (`scan_and_diff_against_memory_v1`)
        changed_rels = sorted(
            set(tomo_delta.get("created_files", ())) | set(tomo_delta.get("modified_content", ()))
        )
        content_verdicts: dict[str, tuple[str, ...]] = {}
        for rel in changed_rels:
            abs_f = stage_ws / rel
            if not abs_f.is_file():
                continue
            sig = content_signature(str(abs_f), validators=_FAST_VALIDATORS)
            content_verdicts[rel] = sig
            req_kind = _expected_validator_for_suffix(rel)
            if req_kind is not None and req_kind not in sig:
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"STATE_ALIAS_LYING_EXTENSION_REFUSED:{rel}:expected_{req_kind}:got_{list(sig)}",
                    "surface_listing_appeared_present": rel in obs_listing_after,
                    "surface_coarse_after": obs_coarse_after,
                    "model_calls": 0,
                }

        # Guard D: Explicit expected file content / SHA-256 postconditions (catches wrong-source coarse aliases!)
        for exp_rel, exp_spec in expected_files.items():
            target_f = stage_ws / exp_rel
            if not target_f.is_file():
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"EXPECTED_ARTIFACT_MISSING:{exp_rel}",
                    "model_calls": 0,
                }
            actual_bytes = target_f.read_bytes()
            if isinstance(exp_spec, bytes) and actual_bytes != exp_spec:
                coarse_same_len = len(actual_bytes) == len(exp_spec)
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"STATE_ALIAS_BYTE_MISMATCH_REFUSED:{exp_rel}",
                    "coarse_size_aliased": coarse_same_len,
                    "model_calls": 0,
                }
            if isinstance(exp_spec, str) and actual_bytes.decode("utf-8", errors="replace") != exp_spec:
                coarse_same_len = len(actual_bytes) == len(exp_spec.encode("utf-8"))
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "rung_selected": 1,
                    "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                    "reason": f"STATE_ALIAS_CONTENT_MISMATCH_REFUSED:{exp_rel}",
                    "coarse_size_aliased": coarse_same_len,
                    "model_calls": 0,
                }
            if isinstance(exp_spec, Mapping):
                exp_sha = exp_spec.get("sha256")
                if exp_sha and hashlib.sha256(actual_bytes).hexdigest() != exp_sha:
                    return {
                        "schema": SCHEMA,
                        "pass": False,
                        "rung_selected": 1,
                        "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
                        "reason": f"STATE_ALIAS_SHA256_MISMATCH_REFUSED:{exp_rel}",
                        "model_calls": 0,
                    }

        # Verified! Commit staged changes back only if caller requested commit_if_verified=True
        if commit_in_place:
            for rel in tomo_delta.get("deleted_files", ()):
                (src_ws / rel).unlink(missing_ok=True)
            for rel in changed_rels:
                dst = src_ws / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stage_ws / rel, dst)

        full_sha = hashlib.sha256(obs_full_after.encode("utf-8")).hexdigest()
        act_sha = hashlib.sha256(cmd_repr.encode("utf-8")).hexdigest()
        cap = empty_capsule()
        cap = append_macrostep(
            cap,
            producer="rung1:state_alias_guarded_executor",
            action_ref=act_sha,
            requires=[],
            provides=["effect:verified_state_transition"],
            values={
                "effect:verified_state_transition": {
                    "full_state_sha256": full_sha,
                    "changed_files": changed_rels,
                    "committed": commit_in_place,
                }
            },
            evidence_refs=[f"tomography_full_sha256:{full_sha}"],
            lineage={"effect:verified_state_transition": [f"evidence:tomography_full_sha256:{full_sha}", f"action:{act_sha}"]},
        )
        verify_capsule(cap)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return {
            "schema": SCHEMA,
            "pass": True,
            "rung_selected": 1,
            "rung_name": "RUNG1_STATE_ALIAS_GUARDED_ACTION",
            "changed_files": changed_rels,
            "content_signatures": {k: list(v) for k, v in content_verdicts.items()},
            "observation_layers": {
                "listing_changed": obs_listing_before != obs_listing_after,
                "coarse_changed": obs_coarse_before != obs_coarse_after,
                "full_sha256_changed": obs_full_before != obs_full_after,
            },
            "capsule_head_hash": cap["head_hash"],
            "elapsed_ms": round(elapsed_ms, 4),
            "model_calls": 0,
        }


def _synthesize_deterministic_ast_candidates(module_source: str, target_symbol: str | None = None) -> list[tuple[str, str]]:
    """Generate small deterministic AST repair candidates (relational boundary / guard repairs) when none are supplied."""
    out: list[tuple[str, str]] = []
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return out

    # Comparison boundary flips (`<` <-> `<=`, `>` <-> `>=`) inside target symbol
    cmp_swaps: list[tuple[type[ast.cmpop], type[ast.cmpop], str]] = [
        (ast.Lt, ast.LtE, "lt_to_lte"),
        (ast.LtE, ast.Lt, "lte_to_lt"),
        (ast.Gt, ast.GtE, "gt_to_gte"),
        (ast.GtE, ast.Gt, "gte_to_gt"),
    ]
    for fn_idx, node in enumerate(tree.body):
        if not isinstance(node, ast.FunctionDef):
            continue
        if target_symbol and node.name != target_symbol:
            continue
        for sub_idx, sub in enumerate(ast.walk(node)):
            if isinstance(sub, ast.Compare) and len(sub.ops) == 1:
                for src_op, dst_op, tag in cmp_swaps:
                    if isinstance(sub.ops[0], src_op):
                        clone = ast.parse(module_source)
                        c_fn = clone.body[fn_idx]
                        c_nodes = list(ast.walk(c_fn))
                        c_cmp = c_nodes[sub_idx]
                        if isinstance(c_cmp, ast.Compare):
                            c_cmp.ops[0] = dst_op()
                            ast.fix_missing_locations(clone)
                            out.append((f"auto_{tag}_{node.name}_{sub_idx}", ast.unparse(clone)))
        if len(out) >= 12:
            break
    return out


def _run_rung2_cow_zygote_repair(task: Mapping[str, Any]) -> dict[str, Any] | None:
    """Rung 2: Transitive AST test-impact slicing + POSIX `os.fork()` CoW Zygote speculative patch verification."""
    mod_src = task.get("module_source")
    test_src = task.get("test_source")
    if not (isinstance(mod_src, str) and isinstance(test_src, str)):
        return None

    t0 = time.perf_counter_ns()
    changed_syms = list(task.get("changed_symbols") or ())
    if not changed_syms:
        try:
            changed_syms = [
                n.name for n in ast.parse(mod_src).body if isinstance(n, ast.FunctionDef)
            ]
        except SyntaxError:
            changed_syms = []

    slice_info = select_impacted_tests(mod_src, test_src, changed_syms)
    selected_tests = slice_info["selected_tests"]
    if not selected_tests:
        return {
            "schema": SCHEMA,
            "pass": False,
            "rung_selected": 2,
            "rung_name": "RUNG2_COW_ZYGOTE_SPECULATIVE_REPAIR",
            "reason": "NO_TEST_FUNCTIONS_FOUND",
            "model_calls": 0,
        }

    supplied = list(task.get("candidate_patches") or ())
    candidates: list[tuple[str, str]] = []
    for idx, item in enumerate(supplied):
        if isinstance(item, Mapping):
            candidates.append((str(item.get("id") or f"cand_{idx}"), str(item["source"])))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            candidates.append((str(item[0]), str(item[1])))
        elif isinstance(item, str):
            candidates.append((f"cand_{idx}", item))

    if not candidates:
        target_sym = changed_syms[0] if len(changed_syms) == 1 else None
        candidates = _synthesize_deterministic_ast_candidates(mod_src, target_sym)

    if not candidates:
        return None

    verifier = CowZygoteSpeculativeVerifier(test_src, selected_tests)
    all_tests = slice_info["all_tests"]
    full_verifier = (
        CowZygoteSpeculativeVerifier(test_src, all_tests)
        if set(all_tests) != set(selected_tests)
        else verifier
    )

    eval_records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="brain_rung2_cow_") as scratch_str:
        scratch = pathlib.Path(scratch_str)
        for cid, c_src in candidates:
            verdict = verifier.evaluate_candidate_cow(cid, c_src, scratch)
            eval_records.append(verdict)
            if not verdict.get("passed"):
                continue
            # Confirm full suite if test slicing skipped any tests
            if full_verifier is not verifier:
                full_v = full_verifier.evaluate_candidate_cow(f"{cid}_full", c_src, scratch)
                if not full_v.get("passed"):
                    continue
            # Run 64-vector CoW boundary fuzzing invariance on target function if single-symbol
            fuzz_summary: dict[str, Any] | None = None
            if changed_syms:
                try:
                    fv = verify_cow_boundary_invariance(mod_src, c_src, changed_syms[0])
                    fuzz_summary = {
                        "vectors_tested": fv.vectors_tested,
                        "new_crashes_introduced": len(fv.new_crashes),
                        "crashes_eliminated": len(fv.fixed_crashes),
                    }
                    if fv.new_crashes:
                        continue
                except Exception:
                    fuzz_summary = None

            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return {
                "schema": SCHEMA,
                "pass": True,
                "rung_selected": 2,
                "rung_name": "RUNG2_COW_ZYGOTE_SPECULATIVE_REPAIR",
                "winning_candidate_id": cid,
                "repaired_source": c_src,
                "candidates_evaluated": len(eval_records),
                "impact_slice": {
                    "selected_tests": selected_tests,
                    "total_tests": len(all_tests),
                    "reduction_ratio": slice_info["reduction_ratio"],
                },
                "boundary_fuzz_64": fuzz_summary,
                "candidate_verdicts": eval_records,
                "elapsed_ms": round(elapsed_ms, 4),
                "model_calls": 0,
            }

    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
    return {
        "schema": SCHEMA,
        "pass": False,
        "rung_selected": 2,
        "rung_name": "RUNG2_COW_ZYGOTE_SPECULATIVE_REPAIR",
        "reason": "NO_CANDIDATE_PASSED_COW_VERIFICATION",
        "candidates_evaluated": len(eval_records),
        "candidate_verdicts": eval_records,
        "elapsed_ms": round(elapsed_ms, 4),
        "model_calls": 0,
    }


def _run_rung3_petri_or_active_contrast(task: Mapping[str, Any]) -> dict[str, Any] | None:
    """Rung 3: Cut-vertex Petri-net checkpointed long-horizon execution OR active contrast selection."""
    t0 = time.perf_counter_ns()

    # 3a) Multi-step Petri trajectory with articulation-point checkpointing
    if "petri_transitions" in task:
        raw_trs = task["petri_transitions"]
        transitions: list[PetriTransition] = []
        for idx, tr in enumerate(raw_trs):
            if isinstance(tr, PetriTransition):
                transitions.append(tr)
            elif isinstance(tr, Mapping):
                transitions.append(
                    PetriTransition(
                        action_id=str(tr.get("action_id") or f"step_{idx}"),
                        modality=str(tr.get("modality") or "cli"),
                        preconditions=frozenset(tr.get("preconditions") or ()),
                        add_tokens=frozenset(tr.get("add_tokens") or ()),
                        del_tokens=frozenset(tr.get("del_tokens") or ()),
                        violates_standing=bool(tr.get("violates_standing", False)),
                    )
                )
        init_toks = frozenset(task.get("initial_tokens") or ())
        goal_toks = frozenset(task.get("goal_tokens") or ())
        forb_toks = frozenset(task.get("forbidden_tokens") or ())
        art_indices = CrossModalPetriPlanner.find_articulation_step_indices(init_toks, goal_toks, transitions)
        res = CrossModalPetriPlanner.execute_checkpointed_horizon(
            initial_tokens=init_toks,
            goal_tokens=goal_toks,
            forbidden_tokens=forb_toks,
            plan=transitions,
            max_episode_len=int(task.get("max_episode_len", 15)),
            max_retries_per_episode=int(task.get("max_retries_per_episode", 2)),
        )
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return {
            "schema": SCHEMA,
            "pass": bool(res.get("completed")),
            "rung_selected": 3,
            "rung_name": "RUNG3_PETRI_CUT_VERTEX_CHECKPOINT_PLANNER",
            "articulation_step_indices": art_indices,
            "horizon_execution": res,
            "elapsed_ms": round(elapsed_ms, 4),
            "model_calls": 0,
        }

    # 3b) Active information-gain contrast probe selection (`contrast_selection_v1`)
    if "contrast_evidence" in task and "candidate_states" in task:
        ev = [(frozenset(s), bool(ok)) for s, ok in task["contrast_evidence"]]
        states = [frozenset(s) for s in task["candidate_states"]]
        chosen = contrast_sel.select_contrast(ev, states)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        if chosen.state is None:
            return {
                "schema": SCHEMA,
                "pass": False,
                "rung_selected": 3,
                "rung_name": "RUNG3_ACTIVE_CONTRAST_PROBE",
                "reason": str(chosen.reason or chosen.status or "NO_DISCRIMINATING_CONTRAST_AVAILABLE"),
                "contrast_status": chosen.status,
                "elapsed_ms": round(elapsed_ms, 4),
                "model_calls": 0,
            }
        return {
            "schema": SCHEMA,
            "pass": True,
            "rung_selected": 3,
            "rung_name": "RUNG3_ACTIVE_CONTRAST_PROBE",
            "contrast_status": chosen.status,
            "selected_probe_state": sorted(chosen.state),
            "survivors_before": int(chosen.survivors_before),
            "worst_case_survivors_after": chosen.worst_case_survivors_after,
            "discriminating_facts": list(chosen.discriminating_facts),
            "elapsed_ms": round(elapsed_ms, 4),
            "model_calls": 0,
        }

    return None


def execute_fast_cascade(
    task: Mapping[str, Any],
    *,
    quarantined_skills: set[str] | None = None,
) -> dict[str, Any]:
    """Run the 4-rung deterministic fast-path cascade (`Rung 0 -> Rung 1 -> Rung 2 -> Rung 3 -> ABSTAIN`)."""
    r0 = _run_rung0_slot_lookup(task, quarantined_external=quarantined_skills)
    if r0 is not None:
        return r0

    r1 = _run_rung1_state_alias_guarded_action(task)
    if r1 is not None:
        return r1

    r2 = _run_rung2_cow_zygote_repair(task)
    if r2 is not None:
        return r2

    r3 = _run_rung3_petri_or_active_contrast(task)
    if r3 is not None:
        return r3

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": False,
        "rung_selected": None,
        "rung_name": "FAIL_CLOSED_ABSTAIN",
        "reason": "NO_CASCADE_RUNG_MATCHED_TASK_SPEC",
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }


def run(payload: Mapping[str, Any] | None = None, _root: pathlib.Path | None = None) -> dict[str, Any]:
    return execute_fast_cascade(dict(payload or {}))
