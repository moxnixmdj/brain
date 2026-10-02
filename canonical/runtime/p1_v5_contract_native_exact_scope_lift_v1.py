"""Exact semantic-quotient lift from the frozen contract-native P1 route to verified V5.

The frozen contract-native trajectory generator has a finite semantic quotient.
For difficulty 1..5, trajectory length is 6+difficulty and the only semantic RNG
choice is the injected cause position in 1..n-3. The remaining RNG operation only
permutes repair_candidates. This adapter ignores top-level seed and maps repairs
by their unique targets_step, so repair ordering is erased exactly.

The theorem therefore checks every one of the 30 (difficulty,cause) quotient
classes across all six V5 domains and verifies order invariance for every possible
repair permutation. It proves route semantics, not private benchmark population or
score equivalence.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as native
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as v5

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V5_CONTRACT_NATIVE_EXACT_SCOPE_LIFT_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
NATIVE_PATH = "canonical/runtime/contract_native_proof_suites.py"
V5_PATH = "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"
EXPECTED_NATIVE_BLOB = "0210790c7dd705ef328e1b55d529a30c5c6c3337"
EXPECTED_V5_BLOB = "2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d"
DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")


def _git_blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _repair_map(public_native: Mapping[str, Any]) -> dict[int, str]:
    task = public_native.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("NATIVE_TASK_INVALID")
    repairs = task.get("repair_candidates")
    if not isinstance(repairs, list) or not repairs:
        raise ValueError("NATIVE_REPAIRS_INVALID")
    out: dict[int, str] = {}
    for row in repairs:
        if not isinstance(row, Mapping):
            raise ValueError("NATIVE_REPAIR_ROW_INVALID")
        step = row.get("targets_step")
        rid = row.get("id")
        if not isinstance(step, int) or isinstance(step, bool) or not isinstance(rid, str) or not rid:
            raise ValueError("NATIVE_REPAIR_FIELDS_INVALID")
        if step in out:
            raise ValueError("NATIVE_REPAIR_TARGET_DUPLICATE")
        out[step] = rid
    return out


def lift_native_public_task(public_native: Mapping[str, Any], *, domain: str) -> dict[str, Any]:
    """Normalize one frozen contract-native P1 task into the V5 typed IR.

    Hidden cause and repair oracle are never read.  The top-level seed and repair
    ordering are intentionally erased.
    """
    if domain not in DOMAINS:
        raise ValueError("DOMAIN_INVALID")
    if public_native.get("contract") != BEHAVIOR:
        raise ValueError("NATIVE_CONTRACT_INVALID")
    task = public_native.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("NATIVE_TASK_INVALID")
    trajectory = task.get("trajectory")
    if not isinstance(trajectory, list) or len(trajectory) < 5:
        raise ValueError("NATIVE_TRAJECTORY_INVALID")

    rows: list[dict[str, Any]] = []
    previous: str | None = None
    for expected_step, row in enumerate(trajectory):
        if not isinstance(row, Mapping):
            raise ValueError("NATIVE_TRAJECTORY_ROW_INVALID")
        step = row.get("step")
        action = row.get("action")
        state = row.get("state")
        invariant = row.get("invariant_pass")
        symptom = row.get("terminal_symptom")
        if step != expected_step or action != f"A{expected_step}":
            raise ValueError("NATIVE_STEP_OR_ACTION_DRIFT")
        if state not in {"OK", "FAULT_INJECTED", "DOWNSTREAM_DEGRADED"}:
            raise ValueError("NATIVE_STATE_DRIFT")
        if type(invariant) is not bool or type(symptom) is not bool:
            raise ValueError("NATIVE_BOOLEAN_FIELDS_INVALID")

        aid = str(action)
        resource = f"native:p1:r{expected_step}"
        checks = [{
            "kind": "INVARIANT",
            "id": f"{aid}:invariant",
            "pass": invariant,
            "evidence": [f"native:{aid}:state:{state}", f"native:{aid}:invariant:{invariant}"],
        }]
        rows.append({
            "action_id": aid,
            "domain": domain,
            "reads": [] if previous is None else [f"native:p1:r{expected_step-1}"],
            "writes": [resource],
            "depends_on": [] if previous is None else [previous],
            "dependency_composition": "SEQUENTIAL",
            "checks": checks,
        })
        previous = aid

    # Validate the public repair set structurally, but do not expose it to V5.
    # This makes the lift exactly invariant to the generator's shuffle.
    _repair_map(public_native)
    return {
        "schema": SCHEMA,
        "behavior_id": BEHAVIOR,
        "task": {
            "domain": domain,
            "trajectory": rows,
            "terminal_failed_resources": [f"native:p1:r{len(rows)-1}"],
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_RESCUING_REPAIR",
        },
    }


def lower_v5_output(public_native: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    """Translate V5's causal answer back into the exact native scorer surface."""
    if output.get("status") != "IDENTIFIED":
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    aid = output.get("cause_action_id")
    if not isinstance(aid, str):
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    m = re.fullmatch(r"A(\d+)", aid)
    if m is None:
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    step = int(m.group(1))
    repair = _repair_map(public_native).get(step)
    return {
        "cause_step": step,
        "repair_id": repair,
        "evidence_steps": [step],
    }


def _find_representatives(difficulty: int) -> dict[int, dict[str, Any]]:
    n = max(5, min(14, 6 + difficulty))
    needed = set(range(1, n - 2))
    found: dict[int, dict[str, Any]] = {}
    # The first RNG semantic choice is randint(1,n-3). A modest deterministic
    # seed scan is only used to materialize each source-code-defined class.
    for seed in range(10000):
        case = native.generate_case(BEHAVIOR, seed, difficulty)
        cause = int(case["_oracle"]["cause_step"])
        if cause in needed and cause not in found:
            found[cause] = case
        if set(found) == needed:
            break
    if set(found) != needed:
        raise AssertionError(f"QUOTIENT_CLASS_NOT_MATERIALIZED:difficulty={difficulty}")
    return found


def _validate_generator_shape(case: Mapping[str, Any], difficulty: int, cause: int) -> None:
    n = 6 + difficulty
    if len(case["task"]["trajectory"]) != n:
        raise AssertionError("NATIVE_LENGTH_DRIFT")
    if case["_oracle"]["cause_step"] != cause:
        raise AssertionError("NATIVE_CAUSE_DRIFT")
    if case["_oracle"]["repair_id"] != f"repair_{cause}":
        raise AssertionError("NATIVE_REPAIR_ORACLE_DRIFT")
    traj = case["task"]["trajectory"]
    for i, row in enumerate(traj):
        expected_state = "OK" if i < cause else ("FAULT_INJECTED" if i == cause else "DOWNSTREAM_DEGRADED")
        expected_invariant = i < cause
        expected_symptom = i > cause
        if row != {
            "step": i,
            "action": f"A{i}",
            "state": expected_state,
            "invariant_pass": expected_invariant,
            "terminal_symptom": expected_symptom,
        }:
            raise AssertionError("NATIVE_TRAJECTORY_SHAPE_DRIFT")
    repairs = case["task"]["repair_candidates"]
    expected = {(f"repair_{i}", i) for i in range(cause, n - 1)}
    actual = {(str(x.get("id")), x.get("targets_step")) for x in repairs}
    if actual != expected or len(actual) != len(repairs):
        raise AssertionError("NATIVE_REPAIR_SET_DRIFT")


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    if _git_blob(NATIVE_PATH) != EXPECTED_NATIVE_BLOB:
        errors.append("NATIVE_GENERATOR_BLOB_DRIFT")
    if _git_blob(V5_PATH) != EXPECTED_V5_BLOB:
        errors.append("V5_CANDIDATE_BLOB_DRIFT")
    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_DRIFT",
            "pass": False,
            "errors": errors,
            "scope_relation": "NOT_PROVED",
            "promotion_authority": False,
        }

    class_rows: list[dict[str, Any]] = []
    permutation_checks = 0
    domain_case_checks = 0
    seen_classes: set[tuple[int, int]] = set()

    for difficulty in range(1, 6):
        reps = _find_representatives(difficulty)
        for cause, case in sorted(reps.items()):
            _validate_generator_shape(case, difficulty, cause)
            seen_classes.add((difficulty, cause))
            public = native.public_task(case)

            canonical_v5_output: dict[str, Any] | None = None
            for domain in DOMAINS:
                lifted = lift_native_public_task(public, domain=domain)
                out = v5.solve(lifted)
                lowered = lower_v5_output(public, out)
                verdict = native.score_case(case, lowered)
                domain_case_checks += 1
                if verdict.get("pass") is not True:
                    errors.append(f"QUOTIENT_CLASS_FAIL:d{difficulty}:c{cause}:{domain}")
                if canonical_v5_output is None:
                    canonical_v5_output = dict(out)
                else:
                    # The V5 solver is domain-parametric on this normalized route.
                    left = {k: v for k, v in canonical_v5_output.items() if k != "supporting_receipts"}
                    right = {k: v for k, v in out.items() if k != "supporting_receipts"}
                    if left != right:
                        errors.append(f"DOMAIN_PARAMETRICITY_FAIL:d{difficulty}:c{cause}:{domain}")

            if canonical_v5_output is None:
                errors.append("V5_OUTPUT_MISSING")
                continue

            # Exhaust the only remaining generator variation exactly: repair order.
            repairs = list(public["task"]["repair_candidates"])
            expected_lowered = lower_v5_output(public, canonical_v5_output)
            for perm in itertools.permutations(repairs):
                p = copy.deepcopy(public)
                p["task"]["repair_candidates"] = list(perm)
                if lift_native_public_task(p, domain="CODE") != lift_native_public_task(public, domain="CODE"):
                    errors.append(f"REPAIR_ORDER_AFFECTS_LIFT:d{difficulty}:c{cause}")
                    break
                lowered = lower_v5_output(p, canonical_v5_output)
                permutation_checks += 1
                if lowered != expected_lowered:
                    errors.append(f"REPAIR_ORDER_AFFECTS_LOWERING:d{difficulty}:c{cause}")
                    break
                if native.score_case(case, lowered).get("pass") is not True:
                    errors.append(f"REPAIR_ORDER_BREAKS_NATIVE_SCORE:d{difficulty}:c{cause}")
                    break

            class_rows.append({
                "difficulty": difficulty,
                "trajectory_length": 6 + difficulty,
                "cause_step": cause,
                "representative_seed": case["seed"],
                "repair_count": len(repairs),
            })

    expected_classes = {
        (difficulty, cause)
        for difficulty in range(1, 6)
        for cause in range(1, (6 + difficulty) - 2)
    }
    if seen_classes != expected_classes:
        errors.append("SEMANTIC_QUOTIENT_INCOMPLETE")
    if len(expected_classes) != 30:
        errors.append("SEMANTIC_QUOTIENT_CARDINALITY_DRIFT")
    if domain_case_checks != 180:
        errors.append("DOMAIN_CROSS_PRODUCT_COUNT_DRIFT")
    if permutation_checks != 462280:
        errors.append("REPAIR_PERMUTATION_EXHAUSTION_COUNT_DRIFT")

    errors = sorted(set(errors))
    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXACT_FROZEN_CONTRACT_NATIVE_P1_SEMANTIC_QUOTIENT_LIFTS_TO_V5"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "behavior_id": BEHAVIOR,
        "scope_relation": "SUPERSET_OF_EXACT_FROZEN_CONTRACT_NATIVE_P1_ROUTE",
        "proof_basis": {
            "frozen_native_generator_blob": EXPECTED_NATIVE_BLOB,
            "frozen_v5_candidate_blob": EXPECTED_V5_BLOB,
            "difficulty_values": [1, 2, 3, 4, 5],
            "semantic_quotient_class_count": len(seen_classes),
            "semantic_quotient_expected_count": 30,
            "domain_parametric_checks": domain_case_checks,
            "repair_order_permutations_exhausted": permutation_checks,
            "top_level_seed_load_bearing_after_quotient": False,
            "private_benchmark_population_equivalence_claimed": False,
        },
        "quotient_classes": class_rows,
        "three_surface_transport_rule": (
            "ANY_DECLARED_SURFACE_BOUND_TO_THE_EXACT_FROZEN_DIRECT_TRAJECTORY_CAUSAL_CONTRACT_SUITE"
            "_INHERITS_THIS_ROUTE_SCOPE_RELATION_ONLY__NO_PRIVATE_SCORE_OR_POPULATION_INHERITANCE"
        ),
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
