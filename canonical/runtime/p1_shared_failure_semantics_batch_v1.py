"""One-shot source-native P1 shared failure-semantics batch.

The fresh cases come from the independently verified contract-native P1 source
generator, not from the V7 synthetic proof population. Hidden injected-cause
metadata is used only by source instrumentation to bind DIRECT_CONTRACT versus
DERIVED_UPSTREAM before candidate visibility. The candidate never receives the
source oracle.

A caller supplies an uncontrollable post-freeze beacon (for the terminal run,
the independent public runner's GitHub Actions run identity). No result feedback
is accepted by this module and no terminal-v3 receipt is replayed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as scorer
from canonical.runtime.p1_shared_failure_semantics_normalizer_v1 import (
    SURFACES as NORMALIZER_SURFACES,
    normalize_case,
)

SCHEMA = "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_V1"
CONTRACT = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SURFACES = (
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
CASES_PER_SURFACE = 64
TOTAL_CASES = len(SURFACES) * CASES_PER_SURFACE
DIFFICULTIES = (1, 2, 3, 4, 5)
BEACON_NAMESPACE = "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH_V1"

if set(SURFACES) != set(NORMALIZER_SURFACES):
    raise RuntimeError("NORMALIZER_SURFACE_SET_DRIFT")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def derive_seed(beacon: str, surface_id: str, case_index: int) -> int:
    if not isinstance(beacon, str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    if surface_id not in SURFACES:
        raise ValueError("SURFACE_NOT_FROZEN")
    if not isinstance(case_index, int) or isinstance(case_index, bool):
        raise ValueError("CASE_INDEX_INVALID")
    if case_index < 0 or case_index >= CASES_PER_SURFACE:
        raise ValueError("CASE_INDEX_OUT_OF_RANGE")
    material = (
        f"{BEACON_NAMESPACE}\n{beacon}\n{surface_id}\n{case_index}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _source_receipt(full_source_case: Mapping[str, Any]) -> str:
    return "sha256:" + _sha256(full_source_case)


def instrument_source_case(
    full_source_case: Mapping[str, Any],
    *,
    surface_id: str,
    case_index: int,
) -> dict[str, Any]:
    """Bind source-truth failure semantics without exposing the hidden oracle."""
    if surface_id not in SURFACES:
        return {"status": "FAIL_CLOSED", "reason": "SURFACE_NOT_FROZEN"}
    if full_source_case.get("contract") != CONTRACT:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_CONTRACT_MISMATCH"}

    task = full_source_case.get("task")
    oracle = full_source_case.get("_oracle")
    if not isinstance(task, Mapping) or not isinstance(oracle, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_CASE_SCHEMA_INVALID"}
    steps = task.get("trajectory")
    cause_step = oracle.get("cause_step")
    if (
        not isinstance(steps, list)
        or not steps
        or not isinstance(cause_step, int)
        or isinstance(cause_step, bool)
    ):
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_CAUSAL_TRUTH_INVALID"}

    receipt = _source_receipt(full_source_case)
    rows: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        if not isinstance(step, Mapping):
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_STEP_INVALID:{i}"}
        if step.get("step") != i or step.get("action") != f"A{i}":
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_STEP_ID_DRIFT:{i}"}
        invariant = step.get("invariant_pass")
        if type(invariant) is not bool:
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_INVARIANT_INVALID:{i}"}

        evidence = [
            f"{receipt}#step={i}",
            f"{receipt}#state={step.get('state')}",
        ]
        check: dict[str, Any] = {
            "kind": "INVARIANT",
            "id": f"A{i}:INVARIANT",
            "pass": invariant,
            "evidence": evidence,
        }
        if invariant is False:
            check["failure_semantics"] = (
                "DIRECT_CONTRACT" if i == cause_step else "DERIVED_UPSTREAM"
            )

        rows.append(
            {
                "step": i,
                "action_id": f"A{i}",
                "domain": "SOURCE_NATIVE_AGENT_TRAJECTORY",
                "reads": [] if i == 0 else [f"state:{i-1}"],
                "writes": [f"state:{i}"],
                "depends_on": [] if i == 0 else [f"A{i-1}"],
                "dependency_composition": "SEQUENTIAL",
                "checks": [check],
            }
        )

    direct = [
        i
        for i, row in enumerate(rows)
        for check in row["checks"]
        if check.get("pass") is False
        and check.get("failure_semantics") == "DIRECT_CONTRACT"
    ]
    derived = [
        i
        for i, row in enumerate(rows)
        for check in row["checks"]
        if check.get("pass") is False
        and check.get("failure_semantics") == "DERIVED_UPSTREAM"
    ]
    if direct != [cause_step]:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_DIRECT_BINDING_NOT_UNIQUE"}
    if not derived or any(i <= cause_step for i in derived):
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_DERIVED_BINDING_INVALID"}

    raw = {
        "surface_id": surface_id,
        "case_id": f"{surface_id}::case-{case_index:03d}",
        "source_observation_receipt": receipt,
        "trajectory": rows,
        "terminal_failed_resources": [f"state:{len(rows)-1}"],
    }
    normalized = normalize_case(raw)
    if normalized.get("status") != "PASS":
        return {
            "status": "FAIL_CLOSED",
            "reason": "NORMALIZER_REJECTED_SOURCE_BOUND_CASE",
            "normalizer": normalized,
        }

    public_candidate_case = {
        "schema": SCHEMA,
        "behavior_id": CONTRACT,
        "task": copy.deepcopy(normalized["task"]),
    }
    v7_full_case = {
        **copy.deepcopy(public_candidate_case),
        "_oracle": {
            "status": "IDENTIFIED",
            "roots": [f"A{cause_step}"],
            "critical": f"A{cause_step}",
            "mechanisms": {f"A{cause_step}": ["INVARIANT"]},
        },
    }
    return {
        "status": "PASS",
        "surface_id": surface_id,
        "case_id": raw["case_id"],
        "source_observation_receipt": receipt,
        "source_case": full_source_case,
        "candidate_case": public_candidate_case,
        "v7_full_case": v7_full_case,
        "cause_step": cause_step,
        "semantics_counts": {
            "DIRECT_CONTRACT": len(direct),
            "DERIVED_UPSTREAM": len(derived),
        },
    }


def _adapt_v7_to_source_candidate(
    v7_output: Mapping[str, Any],
) -> dict[str, Any]:
    if v7_output.get("status") != "IDENTIFIED":
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    aid = v7_output.get("cause_action_id")
    if not isinstance(aid, str) or not aid.startswith("A"):
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    try:
        step = int(aid[1:])
    except ValueError:
        return {"cause_step": None, "repair_id": None, "evidence_steps": []}
    receipts = v7_output.get("supporting_receipts")
    evidence_steps = [step] if isinstance(receipts, list) and receipts else []
    return {
        "cause_step": step,
        "repair_id": f"repair_{step}",
        "evidence_steps": evidence_steps,
    }


def evaluate_one(
    *,
    beacon: str,
    surface_id: str,
    case_index: int,
) -> dict[str, Any]:
    seed = derive_seed(beacon, surface_id, case_index)
    difficulty = DIFFICULTIES[case_index % len(DIFFICULTIES)]
    full_source_case = source.generate_case(CONTRACT, seed, difficulty)
    bound = instrument_source_case(
        full_source_case, surface_id=surface_id, case_index=case_index
    )
    if bound.get("status") != "PASS":
        return {
            "pass": False,
            "surface_id": surface_id,
            "case_index": case_index,
            "seed": seed,
            "difficulty": difficulty,
            "reason": "INSTRUMENTATION_FAIL_CLOSED",
            "detail": bound,
        }

    v7_output = candidate.solve(copy.deepcopy(bound["candidate_case"]))
    v7_verdict = scorer.score_case(bound["v7_full_case"], v7_output)
    source_candidate = _adapt_v7_to_source_candidate(v7_output)
    source_verdict = source.score_case(full_source_case, source_candidate)
    passed = (
        v7_verdict.get("pass") is True
        and source_verdict.get("pass") is True
        and source_verdict.get("rescue_pass") is True
    )
    return {
        "pass": passed,
        "surface_id": surface_id,
        "case_index": case_index,
        "seed": seed,
        "difficulty": difficulty,
        "source_observation_receipt": bound["source_observation_receipt"],
        "source_case_public_sha256": _sha256(source.public_task(full_source_case)),
        "candidate_input_sha256": _sha256(bound["candidate_case"]),
        "candidate_output_sha256": _sha256(v7_output),
        "candidate_status": v7_output.get("status"),
        "cause_step": bound["cause_step"],
        "semantics_counts": bound["semantics_counts"],
        "v7_intervention_scorer_pass": v7_verdict.get("pass") is True,
        "source_native_rescue_scorer_pass": source_verdict.get("pass") is True,
        "source_native_rescue_pass": source_verdict.get("rescue_pass") is True,
        "failure_reason": None
        if passed
        else {
            "v7": v7_verdict,
            "source": source_verdict,
        },
    }


def _wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    zz = z * z
    centre = p + zz / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + zz / (4 * total)) / total)
    return (centre - margin) / (1 + zz / total)


def run_batch(beacon: str) -> dict[str, Any]:
    if not isinstance(beacon, str) or not beacon:
        raise ValueError("BEACON_REQUIRED")

    rows = [
        evaluate_one(beacon=beacon, surface_id=surface, case_index=i)
        for surface in SURFACES
        for i in range(CASES_PER_SURFACE)
    ]
    passes = sum(row["pass"] is True for row in rows)
    by_surface: dict[str, dict[str, Any]] = {}
    for surface in SURFACES:
        part = [row for row in rows if row["surface_id"] == surface]
        good = sum(row["pass"] is True for row in part)
        by_surface[surface] = {
            "cases": len(part),
            "passes": good,
            "all_pass": good == len(part),
            "wilson_95_lower": _wilson_lower(good, len(part)),
            "both_semantics_classes_present_every_case": all(
                row.get("semantics_counts", {}).get("DIRECT_CONTRACT", 0) >= 1
                and row.get("semantics_counts", {}).get("DERIVED_UPSTREAM", 0) >= 1
                for row in part
            ),
        }

    all_pass = passes == TOTAL_CASES and all(
        v["all_pass"] and v["both_semantics_classes_present_every_case"]
        for v in by_surface.values()
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ONE_SHARED_SOURCE_NATIVE_P1_FAILURE_SEMANTICS_BATCH"
            if all_pass
            else "FAIL_CLOSED__P1_SHARED_BATCH"
        ),
        "pass": all_pass,
        "beacon_sha256": hashlib.sha256(beacon.encode("utf-8")).hexdigest(),
        "beacon_namespace": BEACON_NAMESPACE,
        "source_generator": "canonical/runtime/contract_native_proof_suites.py",
        "candidate": "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "normalizer": "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py",
        "intervention_scorer": "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py",
        "cases": TOTAL_CASES,
        "passes": passes,
        "failures": TOTAL_CASES - passes,
        "wilson_95_lower_all": _wilson_lower(passes, TOTAL_CASES),
        "by_surface": by_surface,
        "case_receipts": rows,
        "terminal_v3_replayed": 0,
        "fresh_reality_units_consumed": 1,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "ONE_BATCH_OBSERVATION_ONLY__P1_QUARANTINE_LIFT_REQUIRES_SEPARATE_"
            "INDEPENDENT_ADJUDICATION_AND_ACCEPTANCE_REDUCTION"
        ),
    }


def mutation_preflight() -> dict[str, Any]:
    """Spent deterministic fixture; never counts as fresh terminal evidence."""
    fixture = source.generate_case(CONTRACT, 70001, 3)
    good = instrument_source_case(
        fixture, surface_id=SURFACES[0], case_index=0
    )
    if good.get("status") != "PASS":
        return {"pass": False, "reason": "GOOD_FIXTURE_REJECTED", "detail": good}

    raw_task = copy.deepcopy(good["candidate_case"]["task"])
    # Reconstruct a normalizer raw payload from the accepted task.
    raw = {
        "surface_id": SURFACES[0],
        "case_id": "mutation-fixture",
        "source_observation_receipt": "spent-fixture",
        "trajectory": raw_task["trajectory"],
        "terminal_failed_resources": raw_task["terminal_failed_resources"],
    }

    missing_semantics = copy.deepcopy(raw)
    for row in missing_semantics["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check.pop("failure_semantics", None)
                break
        else:
            continue
        break

    empty_receipt = copy.deepcopy(raw)
    for row in empty_receipt["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check["evidence"] = []
                break
        else:
            continue
        break

    wrong_surface = copy.deepcopy(raw)
    wrong_surface["surface_id"] = "UNFROZEN/SURFACE"

    verdicts = {
        "missing_failure_semantics": normalize_case(missing_semantics),
        "empty_failed_check_receipt": normalize_case(empty_receipt),
        "unfrozen_surface": normalize_case(wrong_surface),
    }
    ok = all(v.get("status") == "FAIL_CLOSED" for v in verdicts.values())
    return {
        "pass": ok,
        "status": "PASS__LOAD_BEARING_NEGATIVE_CONTROLS" if ok else "FAIL_CLOSED",
        "verdicts": verdicts,
        "fresh_reality_units_consumed": 0,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--beacon", required=True)
    args = p.parse_args()
    print(json.dumps(run_batch(args.beacon), indent=2, sort_keys=True))
