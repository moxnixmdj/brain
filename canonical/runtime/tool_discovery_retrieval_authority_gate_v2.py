#!/usr/bin/env python3
"""Tool Discovery Retrieval Authority Gate V2.

V2 preserves the verified V2->V5 retrieval chain enforced by gate V1 and adds
the global Retrieval V6 open-world hardening authority as a mandatory
point-of-use dependency.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as v1

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_V2"
TARGET = v1.TARGET
EXPECTED = {
    "current_authority_path": "canonical/governance/RETRIEVAL_CURRENT_AUTHORITY_V1.json",
    "current_authority_blob": "46b2fc41854b68b0c994504443c9c3d361773c40",
    "v6_activation_path": "canonical/governance/RETRIEVAL_V6_OPEN_WORLD_HARDENING_ACTIVATION_V1.json",
    "v6_activation_blob": "4398fee2d6d0a8a62ca7209852c961bc1fca1c7c",
    "v6_verification_path": "canonical/verification/RETRIEVAL_V6_OPEN_WORLD_HARDENING_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "v6_verification_blob": "5bb0556c0e1c810bb6d7594e039667e03d8309ec",
    "omniretrieval_blob": "959d14f11859467d7d1f010f588e0bad99dd667d",
    "ledger_blob": "c52a269b599d2b2f9e0e018120a3377165629cc7",
    "enumerator_blob": "99b1f20ddd4b8dcceea19cfc57a1c0c5999f4632",
    "novelty_scheduler_blob": "025559f285952fa79f1db3b04f1f40cf6927b77f",
    "torture_universe_blob": "d545a453cedfdd0b8318189c4164232b592addb7",
    "controller_blob": "c205b31ab2f850973aa52cbf709f9e770ee8dacc",
    "tests_blob": "1048843c58631f11e83a8521e2509c1d30f4f6bc",
}
PATHS = {
    "omniretrieval_blob": "canonical/runtime/evidence_omniretrieval_planner_v2.py",
    "ledger_blob": "canonical/runtime/retrieval_monotonic_candidate_ledger_v1.py",
    "enumerator_blob": "canonical/runtime/retrieval_bounded_enumerator_v1.py",
    "novelty_scheduler_blob": "canonical/runtime/retrieval_conditional_novelty_scheduler_v1.py",
    "torture_universe_blob": "canonical/runtime/retrieval_adversarial_universe_v2.py",
    "controller_blob": "canonical/runtime/retrieval_open_world_controller_v6.py",
    "tests_blob": "canonical/tests/test_retrieval_v6_open_world_hardening.py",
}

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False,
        "errors": sorted(set(errors)), "target_predicate": TARGET,
        "execution_authority": False, "promotion_authority": False,
        "acceptance_credit_delta": 0, "family_credit_delta": 0,
    }

def validate(
    base_gate: Mapping[str, Any], current: Mapping[str, Any],
    activation: Mapping[str, Any], verification: Mapping[str, Any],
    actual_blobs: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []
    if base_gate.get("pass") is not True:
        errors.append("BASE_V5_GATE_NOT_PASS")
    if base_gate.get("target_predicate") != TARGET:
        errors.append("BASE_GATE_TARGET_MISMATCH")
    if current.get("schema") != "PROJECT_BRAIN_RETRIEVAL_CURRENT_AUTHORITY_V1":
        errors.append("CURRENT_RETRIEVAL_AUTHORITY_SCHEMA_INVALID")
    if not str(current.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V6"):
        errors.append("CURRENT_RETRIEVAL_AUTHORITY_NOT_ACTIVE_V6")
    authority = current.get("authority") or {}
    independent = current.get("independent_verification") or {}
    if authority.get("git_blob_sha") != EXPECTED["v6_activation_blob"]:
        errors.append("CURRENT_AUTHORITY_V6_ACTIVATION_BINDING_MISMATCH")
    if independent.get("git_blob_sha") != EXPECTED["v6_verification_blob"] or independent.get("conclusion") != "success":
        errors.append("CURRENT_AUTHORITY_V6_VERIFICATION_BINDING_INVALID")

    if activation.get("schema") != "PROJECT_BRAIN_RETRIEVAL_V6_OPEN_WORLD_HARDENING_ACTIVATION_V1":
        errors.append("V6_ACTIVATION_SCHEMA_INVALID")
    invariants = set(activation.get("mandatory_v6_invariants") or [])
    for required in (
        "MONOTONIC_CANDIDATE_RETENTION",
        "QUERYLESS_ENUMERATION_FOR_DECLARED_FINITE_ENUMERABLE_SCOPES",
        "CONDITIONAL_NOVELTY_RANKING_OVER_RAW_POPULARITY",
        "ZERO_YIELD_ROUNDS_NEVER_PROVE_COMPLETENESS",
        "FINITE_FIXTURE_RECALL_1_NEVER_PROMOTES_TO_OPEN_WORLD_COMPLETENESS",
        "VERIFIED_SUFFICIENT_DISPOSITION_REQUIRES_INDEPENDENT_RECEIPT",
    ):
        if required not in invariants:
            errors.append("V6_INVARIANT_MISSING:" + required)

    if verification.get("schema") != "PROJECT_BRAIN_RETRIEVAL_V6_OPEN_WORLD_HARDENING_PUBLIC_RUNNER_VERIFICATION_20261003_V1":
        errors.append("V6_VERIFICATION_SCHEMA_INVALID")
    runner = verification.get("independent_runner") or {}
    verified = verification.get("verified") or {}
    if runner.get("conclusion") != "success":
        errors.append("V6_INDEPENDENT_RUNNER_NOT_SUCCESS")
    if verified.get("pairwise_failure_dimension_coverage") is not True:
        errors.append("V6_PAIRWISE_COVERAGE_NOT_VERIFIED")
    if verified.get("v6_recall_on_declared_finite_fixture_universe") != 1.0:
        errors.append("V6_FINITE_FIXTURE_RECALL_NOT_ONE")
    if verified.get("open_world_completeness_claim_authorized") is not False:
        errors.append("V6_OPEN_WORLD_COMPLETENESS_FIREWALL_INVALID")
    if verified.get("zero_yield_rounds_never_prove_completeness") is not True:
        errors.append("V6_ZERO_YIELD_COMPLETENESS_FIREWALL_INVALID")

    for key, expected in EXPECTED.items():
        if key.endswith("_blob") and actual_blobs.get(key) != expected:
            errors.append("ACTUAL_BLOB_MISMATCH:" + key)
    if errors:
        return _fail(*errors)
    return {
        "schema": SCHEMA,
        "status": "PASS__LIVE_TOOL_DISCOVERY_RETRIEVAL_BOUND_TO_VERIFIED_V2_V3_V4_V5_PLUS_GLOBAL_V6_HARDENING",
        "pass": True,
        "target_predicate": TARGET,
        "base_v5_gate_pass": True,
        "global_v6_authority_mandatory": True,
        "monotonic_candidate_retention_mandatory": True,
        "queryless_bounded_enumeration_mandatory": True,
        "conditional_novelty_scheduling_mandatory": True,
        "zero_yield_never_completeness": True,
        "open_world_unknown_preserved": True,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
    }

def evaluate_repository(root: Path) -> dict[str, Any]:
    def raw(rel: str) -> bytes:
        return (root / rel).read_bytes()
    def load(rel: str) -> dict[str, Any]:
        return json.loads(raw(rel).decode("utf-8"))
    base = v1.evaluate_repository(root)
    actual = {
        "current_authority_blob": v1.git_blob_sha(raw(EXPECTED["current_authority_path"])),
        "v6_activation_blob": v1.git_blob_sha(raw(EXPECTED["v6_activation_path"])),
        "v6_verification_blob": v1.git_blob_sha(raw(EXPECTED["v6_verification_path"])),
    }
    for key, path in PATHS.items():
        actual[key] = v1.git_blob_sha(raw(path))
    return validate(base, load(EXPECTED["current_authority_path"]), load(EXPECTED["v6_activation_path"]), load(EXPECTED["v6_verification_path"]), actual)

def main() -> int:
    root=Path(__file__).resolve().parents[2]
    out=evaluate_repository(root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__=="__main__":
    raise SystemExit(main())
