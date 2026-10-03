"""Predeclared P1 shared failure-semantics batch harness.

This module is deliberately unable to bind candidate-visible failure semantics
from hidden oracle data. The binder accepts only the frozen public source case.
Hidden source oracle data is retained exclusively for post-candidate scoring.

Running this module, including a full batch with a spent beacon, never grants or
claims a fresh-reality unit. Reality consumption and promotion are external
adjudication facts that require a separately frozen execution activation and an
independent public-runner receipt.
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

SCHEMA = "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_HARNESS_V2"
CONTRACT = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SURFACES = (
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
CASES_PER_SURFACE = 64
TOTAL_CASES = len(SURFACES) * CASES_PER_SURFACE
DIFFICULTIES = (1, 2, 3, 4, 5)
BEACON_NAMESPACE = "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH_V2"
DIRECT_PUBLIC_STATES = {"FAULT_INJECTED"}
DERIVED_PUBLIC_STATES = {"DOWNSTREAM_DEGRADED"}

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


def bind_public_source_case(
    public_source_case: Mapping[str, Any],
    *,
    surface_id: str,
    case_index: int,
) -> dict[str, Any]:
    """Bind semantics using public source fields only.

    The caller must pass source.public_task(full_case), never the full hidden
    case. Presence of _oracle is an explicit fail-closed violation.
    """
    if not isinstance(public_source_case, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "PUBLIC_SOURCE_NOT_MAPPING"}
    if "_oracle" in public_source_case:
        return {"status": "FAIL_CLOSED", "reason": "HIDDEN_ORACLE_INPUT_FORBIDDEN"}
    if surface_id not in SURFACES:
        return {"status": "FAIL_CLOSED", "reason": "SURFACE_NOT_FROZEN"}
    if public_source_case.get("contract") != CONTRACT:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_CONTRACT_MISMATCH"}

    task = public_source_case.get("task")
    if not isinstance(task, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "PUBLIC_SOURCE_TASK_INVALID"}
    steps = task.get("trajectory")
    if not isinstance(steps, list) or not steps:
        return {"status": "FAIL_CLOSED", "reason": "PUBLIC_SOURCE_TRAJECTORY_INVALID"}

    receipt = "sha256:" + _sha256(public_source_case)
    rows: list[dict[str, Any]] = []
    direct: list[int] = []
    derived: list[int] = []

    for i, step in enumerate(steps):
        if not isinstance(step, Mapping):
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_STEP_INVALID:{i}"}
        if step.get("step") != i or step.get("action") != f"A{i}":
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_STEP_ID_DRIFT:{i}"}
        invariant = step.get("invariant_pass")
        state = step.get("state")
        if type(invariant) is not bool or not isinstance(state, str):
            return {"status": "FAIL_CLOSED", "reason": f"SOURCE_VISIBLE_FIELDS_INVALID:{i}"}

        check: dict[str, Any] = {
            "kind": "INVARIANT",
            "id": f"A{i}:INVARIANT",
            "pass": invariant,
            "evidence": [
                f"{receipt}#step={i}",
                f"{receipt}#public-state={state}",
            ],
        }
        if invariant is False:
            if state in DIRECT_PUBLIC_STATES:
                check["failure_semantics"] = "DIRECT_CONTRACT"
                direct.append(i)
            elif state in DERIVED_PUBLIC_STATES:
                check["failure_semantics"] = "DERIVED_UPSTREAM"
                derived.append(i)
            else:
                return {
                    "status": "FAIL_CLOSED",
                    "reason": f"FAILED_CHECK_PUBLIC_SEMANTICS_UNBOUND:{i}",
                }

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

    if not direct:
        return {"status": "FAIL_CLOSED", "reason": "DIRECT_CONTRACT_NOT_PRESENT"}
    if not derived:
        return {"status": "FAIL_CLOSED", "reason": "DERIVED_UPSTREAM_NOT_PRESENT"}

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

    return {
        "status": "PASS",
        "surface_id": surface_id,
        "case_id": raw["case_id"],
        "source_observation_receipt": receipt,
        "candidate_case": {
            "schema": SCHEMA,
            "behavior_id": CONTRACT,
            "task": copy.deepcopy(normalized["task"]),
        },
        "semantics_counts": {
            "DIRECT_CONTRACT": len(direct),
            "DERIVED_UPSTREAM": len(derived),
        },
        "semantic_binding_basis": (
            "FROZEN_PUBLIC_SOURCE_STATE_AND_INVARIANT_RESULT_ONLY__"
            "HIDDEN_ORACLE_INPUT_FORBIDDEN"
        ),
    }


def _v7_oracle_from_hidden_source(full_source_case: Mapping[str, Any]) -> dict[str, Any]:
    oracle = full_source_case.get("_oracle")
    if not isinstance(oracle, Mapping):
        raise ValueError("HIDDEN_SOURCE_ORACLE_INVALID")
    cause = oracle.get("cause_step")
    if not isinstance(cause, int) or isinstance(cause, bool):
        raise ValueError("HIDDEN_SOURCE_CAUSE_INVALID")
    return {
        "status": "IDENTIFIED",
        "roots": [f"A{cause}"],
        "critical": f"A{cause}",
        "mechanisms": {f"A{cause}": ["INVARIANT"]},
    }


def _adapt_v7_to_source_candidate(v7_output: Mapping[str, Any]) -> dict[str, Any]:
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
    return {
        "cause_step": step,
        "repair_id": f"repair_{step}",
        "evidence_steps": [step] if isinstance(receipts, list) and receipts else [],
    }


def evaluate_one(*, beacon: str, surface_id: str, case_index: int) -> dict[str, Any]:
    seed = derive_seed(beacon, surface_id, case_index)
    difficulty = DIFFICULTIES[case_index % len(DIFFICULTIES)]
    full_source_case = source.generate_case(CONTRACT, seed, difficulty)
    public_source_case = source.public_task(full_source_case)
    bound = bind_public_source_case(
        public_source_case, surface_id=surface_id, case_index=case_index
    )
    if bound.get("status") != "PASS":
        return {
            "pass": False,
            "surface_id": surface_id,
            "case_index": case_index,
            "seed": seed,
            "difficulty": difficulty,
            "reason": "PUBLIC_SOURCE_BINDING_FAIL_CLOSED",
            "detail": bound,
        }

    candidate_case = copy.deepcopy(bound["candidate_case"])
    v7_output = candidate.solve(copy.deepcopy(candidate_case))
    v7_full_case = {
        **copy.deepcopy(candidate_case),
        "_oracle": _v7_oracle_from_hidden_source(full_source_case),
    }
    v7_verdict = scorer.score_case(v7_full_case, v7_output)
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
        "source_case_public_sha256": _sha256(public_source_case),
        "candidate_input_sha256": _sha256(candidate_case),
        "candidate_output_sha256": _sha256(v7_output),
        "candidate_status": v7_output.get("status"),
        "semantics_counts": bound["semantics_counts"],
        "semantic_binding_basis": bound["semantic_binding_basis"],
        "v7_intervention_scorer_pass": v7_verdict.get("pass") is True,
        "source_native_rescue_scorer_pass": source_verdict.get("pass") is True,
        "source_native_rescue_pass": source_verdict.get("rescue_pass") is True,
        "failure_reason": None if passed else {"v7": v7_verdict, "source": source_verdict},
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
    """Evaluate a complete batch shape without granting reality or credit."""
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
        "status": "PASS__BATCH_SHAPE" if all_pass else "FAIL_CLOSED__BATCH_SHAPE",
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
        "fresh_reality_units_consumed": 0,
        "reality_unit_candidate_if_separately_authorized_and_independently_adjudicated": 1,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "RUNTIME_CANNOT_SELF_PROMOTE__ONLY_SEPARATELY_FROZEN_EXECUTION_ACTIVATION_"
            "PLUS_INDEPENDENT_PUBLIC_RUNNER_RECEIPT_MAY_ADJUDICATE_ONE_FRESH_REALITY_UNIT"
        ),
    }


def mutation_preflight() -> dict[str, Any]:
    full = source.generate_case(CONTRACT, 70001, 3)
    public = source.public_task(full)
    good = bind_public_source_case(public, surface_id=SURFACES[0], case_index=0)

    hidden = copy.deepcopy(public)
    hidden["_oracle"] = {"cause_step": 1}
    hidden_verdict = bind_public_source_case(
        hidden, surface_id=SURFACES[0], case_index=0
    )

    bad_state = copy.deepcopy(public)
    for row in bad_state["task"]["trajectory"]:
        if row.get("invariant_pass") is False:
            row["state"] = "UNKNOWN_FAILED_STATE"
            break
    state_verdict = bind_public_source_case(
        bad_state, surface_id=SURFACES[0], case_index=0
    )

    ok = (
        good.get("status") == "PASS"
        and hidden_verdict.get("reason") == "HIDDEN_ORACLE_INPUT_FORBIDDEN"
        and state_verdict.get("status") == "FAIL_CLOSED"
    )
    return {
        "pass": ok,
        "status": "PASS__PUBLIC_ONLY_BINDER_FIREWALL" if ok else "FAIL_CLOSED",
        "hidden_oracle_input": hidden_verdict,
        "unknown_failed_state": state_verdict,
        "fresh_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--beacon", required=True)
    args = p.parse_args()
    print(json.dumps(run_batch(args.beacon), indent=2, sort_keys=True))
