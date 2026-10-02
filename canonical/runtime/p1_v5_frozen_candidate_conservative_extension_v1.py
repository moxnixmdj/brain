"""Zero-reality conservative-extension proof from the frozen Terminal V3 P1
candidate to the independently verified typed P1 V5 candidate.

This module does not replay any consumed Terminal V3 seed or case. It reasons over
the complete semantic quotient of the frozen contract-native P1 generator:
difficulty determines trajectory length; seed randomness changes only the unique
cause position and the order of repair candidates. The bridge embeds that legacy
public schema into V5 typed IR and proves output equivalence after a deterministic
schema translation.

No terminal, capability, family, execution, or promotion credit is granted here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import contract_native_brain_candidate as legacy_candidate
from canonical.runtime import contract_native_proof_suites as legacy_suite
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as v5_candidate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V5_FROZEN_CANDIDATE_CONSERVATIVE_EXTENSION_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

LEGACY_CANDIDATE = "canonical/runtime/contract_native_brain_candidate.py"
LEGACY_SUITE = "canonical/runtime/contract_native_proof_suites.py"
V5_CANDIDATE = "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"
PARENT_BINDING = "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"

EXPECTED_BLOBS = {
    LEGACY_CANDIDATE: "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85",
    LEGACY_SUITE: "0210790c7dd705ef328e1b55d529a30c5c6c3337",
    V5_CANDIDATE: "2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
    PARENT_BINDING: "a1630299d29ea9c07e55b4314c07ddb3228c3287",
}


class BridgeError(ValueError):
    pass


def _blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _verify_exact_sources() -> list[str]:
    errors = []
    for rel, expected in EXPECTED_BLOBS.items():
        try:
            got = _blob(rel)
        except Exception as exc:
            errors.append(f"UNREADABLE:{rel}:{type(exc).__name__}")
            continue
        if got != expected:
            errors.append(f"BLOB_DRIFT:{rel}:{got}")
    try:
        binding = json.loads((ROOT / PARENT_BINDING).read_text(encoding="utf-8"))
        exact = binding.get("exact_brain_blobs") or {}
        if exact.get(LEGACY_CANDIDATE) != EXPECTED_BLOBS[LEGACY_CANDIDATE]:
            errors.append("PARENT_BINDING_LEGACY_CANDIDATE_PIN_DRIFT")
        if exact.get(LEGACY_SUITE) != EXPECTED_BLOBS[LEGACY_SUITE]:
            errors.append("PARENT_BINDING_LEGACY_SUITE_PIN_DRIFT")
        sched = (binding.get("schedules") or {}).get(BEHAVIOR) or {}
        if sched.get("mode") != "CONTRACT_NATIVE" or sched.get("case_count") != 30:
            errors.append("PARENT_BINDING_P1_SCHEDULE_DRIFT")
        if sched.get("difficulty_cycle") != [1, 2, 3, 4, 5]:
            errors.append("PARENT_BINDING_P1_DIFFICULTY_DRIFT")
    except Exception as exc:
        errors.append("PARENT_BINDING_INVALID:" + type(exc).__name__)
    return sorted(set(errors))


def _legacy_n(difficulty: int) -> int:
    if difficulty not in {1, 2, 3, 4, 5}:
        raise BridgeError("DIFFICULTY_OUTSIDE_FROZEN_RANGE")
    return max(5, min(14, 6 + difficulty))


def structural_case(difficulty: int, cause: int, *, reverse_repairs: bool = False) -> dict[str, Any]:
    """Construct a seed-free representative of one frozen generator equivalence class."""
    n = _legacy_n(difficulty)
    if cause < 1 or cause > n - 3:
        raise BridgeError("CAUSE_OUTSIDE_FROZEN_GENERATOR_RANGE")
    steps = []
    for i in range(n):
        if i < cause:
            state, invariant, symptom = "OK", True, False
        elif i == cause:
            state, invariant, symptom = "FAULT_INJECTED", False, False
        else:
            state, invariant, symptom = "DOWNSTREAM_DEGRADED", False, True
        steps.append({
            "step": i,
            "action": f"A{i}",
            "state": state,
            "invariant_pass": invariant,
            "terminal_symptom": symptom,
        })
    repairs = [{"id": f"repair_{i}", "targets_step": i} for i in range(cause, n - 1)]
    if reverse_repairs:
        repairs.reverse()
    return {
        "schema": legacy_suite.SCHEMA,
        "contract": BEHAVIOR,
        "seed": None,
        "task": {"trajectory": steps, "repair_candidates": repairs},
        "_oracle": {"cause_step": cause, "repair_id": f"repair_{cause}"},
    }


def _validate_legacy_public(public: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if public.get("contract") != BEHAVIOR:
        raise BridgeError("BEHAVIOR_MISMATCH")
    task = public.get("task")
    if not isinstance(task, Mapping):
        raise BridgeError("TASK_INVALID")
    rows = task.get("trajectory")
    repairs = task.get("repair_candidates")
    if not isinstance(rows, list) or len(rows) < 5 or not isinstance(repairs, list):
        raise BridgeError("LEGACY_SCHEMA_INVALID")

    first_bad = None
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise BridgeError("ROW_INVALID")
        if row.get("step") != idx or row.get("action") != f"A{idx}":
            raise BridgeError("LEGACY_STEP_ID_DRIFT")
        passed = row.get("invariant_pass")
        if type(passed) is not bool:
            raise BridgeError("LEGACY_INVARIANT_TYPE")
        if passed is False and first_bad is None:
            first_bad = idx
        if first_bad is None:
            if row.get("state") != "OK" or row.get("terminal_symptom") is not False:
                raise BridgeError("LEGACY_PRECAUSE_STATE_DRIFT")
        elif idx == first_bad:
            if row.get("state") != "FAULT_INJECTED" or row.get("terminal_symptom") is not False:
                raise BridgeError("LEGACY_CAUSE_STATE_DRIFT")
        else:
            if row.get("state") != "DOWNSTREAM_DEGRADED" or row.get("terminal_symptom") is not True:
                raise BridgeError("LEGACY_DOWNSTREAM_STATE_DRIFT")
        if first_bad is not None and passed is not False:
            raise BridgeError("LEGACY_NONMONOTONIC_FAILURE")

    if first_bad is None or first_bad < 1 or first_bad > len(rows) - 3:
        raise BridgeError("LEGACY_CAUSE_RANGE_DRIFT")

    ids = set()
    targets = set()
    for repair in repairs:
        if not isinstance(repair, Mapping):
            raise BridgeError("REPAIR_ROW_INVALID")
        rid, target = repair.get("id"), repair.get("targets_step")
        if not isinstance(rid, str) or not rid or not isinstance(target, int):
            raise BridgeError("REPAIR_FIELDS_INVALID")
        if rid in ids or target in targets:
            raise BridgeError("REPAIR_NOT_BIJECTIVE")
        ids.add(rid)
        targets.add(target)
        if rid != f"repair_{target}":
            raise BridgeError("REPAIR_ID_TARGET_DRIFT")
    expected_targets = set(range(first_bad, len(rows) - 1))
    if targets != expected_targets:
        raise BridgeError("REPAIR_TARGET_SET_DRIFT")
    return rows, repairs


def embed_legacy_public_to_v5(public: Mapping[str, Any]) -> dict[str, Any]:
    rows, _ = _validate_legacy_public(public)
    typed = []
    for i, row in enumerate(rows):
        passed = bool(row["invariant_pass"])
        typed.append({
            "action_id": f"A{i}",
            "reads": [] if i == 0 else [f"legacy:r{i-1}"],
            "writes": [f"legacy:r{i}"],
            "depends_on": [] if i == 0 else [f"A{i-1}"],
            "dependency_composition": "SEQUENTIAL",
            "checks": [{
                "kind": "INVARIANT",
                "id": f"A{i}:INVARIANT",
                "pass": passed,
                "evidence": [] if passed else [f"legacy:step:{i}:invariant_failed"],
            }],
        })
    return {
        "schema": "PROJECT_BRAIN_P1_LEGACY_TO_V5_IR_BRIDGE_V1",
        "behavior_id": BEHAVIOR,
        "task": {
            "trajectory": typed,
            "terminal_failed_resources": [f"legacy:r{len(rows)-1}"],
        },
    }


def translate_v5_to_legacy(public: Mapping[str, Any], v5: Mapping[str, Any]) -> dict[str, Any]:
    _, repairs = _validate_legacy_public(public)
    if v5.get("status") != "IDENTIFIED":
        raise BridgeError("V5_NOT_UNIQUE_IDENTIFIED")
    aid = v5.get("cause_action_id")
    if not isinstance(aid, str) or not aid.startswith("A") or not aid[1:].isdigit():
        raise BridgeError("V5_CAUSE_ACTION_INVALID")
    cause = int(aid[1:])
    if v5.get("cause_action_ids") != [aid] or v5.get("critical_action_id") != aid:
        raise BridgeError("V5_CAUSE_IDENTITY_INCONSISTENT")
    if v5.get("mechanism_classes") != ["INVARIANT"]:
        raise BridgeError("V5_MECHANISM_MISMATCH")
    expected_target = f"restore:{aid}:INVARIANT"
    if v5.get("repair_targets") != [expected_target]:
        raise BridgeError("V5_REPAIR_TARGET_MISMATCH")
    hits = [r for r in repairs if r.get("targets_step") == cause]
    if len(hits) != 1:
        raise BridgeError("LEGACY_REPAIR_NOT_UNIQUE")
    return {
        "cause_step": cause,
        "repair_id": str(hits[0]["id"]),
        "evidence_steps": [cause],
    }


def check_structural_class(difficulty: int, cause: int, *, reverse_repairs: bool = False) -> dict[str, Any]:
    case = structural_case(difficulty, cause, reverse_repairs=reverse_repairs)
    public = legacy_suite.public_task(case)
    legacy = legacy_candidate.solve(public)
    legacy_score = legacy_suite.score_case(case, legacy)
    typed = embed_legacy_public_to_v5(public)
    v5 = v5_candidate.solve(typed)
    translated = translate_v5_to_legacy(public, v5)
    translated_score = legacy_suite.score_case(case, translated)
    return {
        "difficulty": difficulty,
        "cause": cause,
        "reverse_repairs": reverse_repairs,
        "legacy_output": legacy,
        "translated_v5_output": translated,
        "legacy_pass": legacy_score.get("pass") is True,
        "translated_v5_pass": translated_score.get("pass") is True,
        "outputs_equal": legacy == translated,
        "v5_status": v5.get("status"),
    }


def evaluate() -> dict[str, Any]:
    errors = _verify_exact_sources()
    rows = []
    if not errors:
        for difficulty in range(1, 6):
            n = _legacy_n(difficulty)
            for cause in range(1, n - 2):
                for reverse in (False, True):
                    try:
                        row = check_structural_class(difficulty, cause, reverse_repairs=reverse)
                    except Exception as exc:
                        errors.append(f"STRUCTURAL_CLASS_EXCEPTION:{difficulty}:{cause}:{reverse}:{type(exc).__name__}")
                        continue
                    rows.append(row)
                    if not (row["legacy_pass"] and row["translated_v5_pass"] and row["outputs_equal"]):
                        errors.append(f"STRUCTURAL_CLASS_MISMATCH:{difficulty}:{cause}:{reverse}")

    semantic_classes = {(r["difficulty"], r["cause"]) for r in rows}
    expected_semantic_class_count = sum(_legacy_n(d) - 3 for d in range(1, 6))
    if len(semantic_classes) != expected_semantic_class_count:
        errors.append("SEMANTIC_QUOTIENT_INCOMPLETE")
    if expected_semantic_class_count != 30:
        errors.append("FROZEN_STRUCTURAL_CLASS_COUNT_DRIFT")
    if len(rows) != 60:
        errors.append("REPAIR_ORDER_WITNESS_COUNT_DRIFT")

    errors = sorted(set(errors))
    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__V5_CONSERVATIVE_EXTENSION_OF_FROZEN_TERMINAL_V3_P1_CANDIDATE_ON_COMPLETE_LEGACY_GENERATOR_SEMANTIC_QUOTIENT__ZERO_TERMINAL_REPLAY__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "behavior_id": BEHAVIOR,
        "exact_source_blobs": dict(EXPECTED_BLOBS),
        "proof_scope": {
            "frozen_legacy_generator_difficulties": [1, 2, 3, 4, 5],
            "complete_semantic_class_count": len(semantic_classes),
            "expected_semantic_class_count": expected_semantic_class_count,
            "repair_order_witnesses_per_class": 2,
            "checked_rows": len(rows),
            "seed_values_consumed": 0,
            "terminal_case_ids_consumed": 0,
            "terminal_result_receipts_consumed": 0,
            "claim": "V5_PLUS_DETERMINISTIC_PUBLIC_SCHEMA_BRIDGE_TRANSLATES_TO_EXACT_LEGACY_CANDIDATE_OUTPUT_FOR_EVERY_FROZEN_GENERATOR_DIFFICULTY_CAUSE_CLASS; REPAIR_ORDER_IS NONSEMANTIC BECAUSE THE FROZEN GRAMMAR HAS A UNIQUE CAUSE-TARGET REPAIR.",
        },
        "candidate_identity": {
            "frozen_terminal_v3_candidate_git_blob_sha": EXPECTED_BLOBS[LEGACY_CANDIDATE],
            "v5_candidate_git_blob_sha": EXPECTED_BLOBS[V5_CANDIDATE],
            "byte_identical": EXPECTED_BLOBS[LEGACY_CANDIDATE] == EXPECTED_BLOBS[V5_CANDIDATE],
            "relation": "BEHAVIORAL_CONSERVATIVE_EXTENSION_ON_COMPLETE_FROZEN_LEGACY_GENERATOR_SEMANTIC_QUOTIENT" if passed else "NOT_PROVED",
        },
        "forbidden_inference": [
            "THIS_DOES_NOT_MAKE_V5_BYTE_IDENTICAL_TO_THE_FROZEN_TERMINAL_CANDIDATE",
            "THIS_DOES_NOT_REPLAY_OR_REASSIGN_THE_TERMINAL_V3_RESULT_TO_V5",
            "THIS_DOES_NOT_PROVE_PRIVATE_BENCHMARK_POPULATION_OR_SCORE_EQUIVALENCE",
            "THIS_DOES_NOT_CLEAR_P1_QUARANTINE_BY_ITSELF",
        ],
        "next": "INDEPENDENTLY_VERIFY_EXACT_BRIDGE_BYTES__THEN_ALLOW_A_SEPARATE_P1_RESTORATION_REDUCER_TO_USE_THIS_ONLY_AS_CANDIDATE_LINEAGE_EVIDENCE_TOGETHER_WITH_INDEPENDENT_V5_SCOPE_SUPERSET_PROOF",
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
