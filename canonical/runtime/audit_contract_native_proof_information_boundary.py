"""Fail-closed audit of candidate-visible information and score coverage in contract-native proof suites.

This audit does not evaluate Brain capability. It falsifies proof routes whose
candidate-visible payload exposes oracle-bearing labels or whose scorer ignores
a load-bearing output dimension from the frozen behavioral contract.
"""
from __future__ import annotations

from canonical.runtime.contract_native_proof_suites import (
    generate_case,
    oracle_candidate,
    public_task,
    score_case,
)

P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

EXPECTED_FINDINGS = {
    "P1_VISIBLE_FAULT_IDENTITY",
    "P2_VISIBLE_GOLD_EDIT_EFFECTS",
    "P3_EXPRESSION_NOT_LOAD_BEARING",
}


def audit() -> dict:
    findings: list[dict] = []

    p1_confirmed = True
    p1_examples = []
    for seed in range(10):
        case = generate_case(P1, seed, 1 + seed % 5)
        visible = public_task(case)
        cause = case["_oracle"]["cause_step"]
        step = visible["task"]["trajectory"][cause]
        leaked = step.get("state") == "FAULT_INJECTED"
        p1_confirmed &= leaked
        if leaked and len(p1_examples) < 3:
            p1_examples.append({"seed": seed, "cause_step": cause, "candidate_visible_state": step.get("state")})
    if p1_confirmed:
        findings.append({
            "id": "P1_VISIBLE_FAULT_IDENTITY",
            "behavior_id": P1,
            "effect": "DIRECT_TRAJECTORY_ROUTE_NOT_INFORMATION_SAFE_AS_WHOLE_CONTRACT_PROOF",
            "examples": p1_examples,
        })

    p2_case = generate_case(P2, 404, 5)
    p2_visible = public_task(p2_case)
    edits = p2_visible["task"]["edit_candidates"]
    if edits and all(
        all(k in row for k in ("scores", "supported", "hard_violation"))
        for row in edits
    ):
        findings.append({
            "id": "P2_VISIBLE_GOLD_EDIT_EFFECTS",
            "behavior_id": P2,
            "effect": "GENERIC_CONTRACT_NATIVE_P2_ROUTE_MUST_NOT_STAND_IN_FOR_INFORMATION_SAFE_P2_TERMINAL_ROUTE",
            "candidate_visible_gold_fields": ["scores", "supported", "hard_violation"],
        })

    p3_case = generate_case(P3, 303, 5)
    p3_candidate = oracle_candidate(p3_case)
    baseline = score_case(p3_case, p3_candidate)
    mutated = dict(p3_candidate)
    mutated["rendered_synthesis"] = (
        "UNSUPPORTED CONTRADICTORY GIBBERISH THAT VIOLATES THE EXPRESSED SYNTHESIS "
        "WHILE PRESERVING ONLY THE CLAIM-ID SELECTION FIELDS"
    )
    mutated_score = score_case(p3_case, mutated)
    if baseline.get("pass") is True and mutated_score.get("pass") is True:
        findings.append({
            "id": "P3_EXPRESSION_NOT_LOAD_BEARING",
            "behavior_id": P3,
            "effect": "DIRECT_SYNTHESIS_ROUTE_DOES_NOT_SCORE_WHOLE_SELECT_ORGANIZE_EXPRESS_CONTRACT",
            "baseline_pass": True,
            "expression_corruption_pass": True,
        })

    ids = {x["id"] for x in findings}
    exact = ids == EXPECTED_FINDINGS
    return {
        "schema": "PROJECT_BRAIN_CONTRACT_NATIVE_PROOF_INFORMATION_BOUNDARY_AUDIT_V1",
        "status": "FALSIFICATION_CONFIRMED" if exact else "FAIL_CLOSED_UNEXPECTED_AUDIT_RESULT",
        "expected_findings": sorted(EXPECTED_FINDINGS),
        "observed_findings": sorted(ids),
        "findings": findings,
        "p0_structured_method_disposition": "NO_FINDING_FROM_THIS_AUDIT",
        "p2_current_active_route_disposition": (
            "CURRENT_P2_T1_INFORMATION_SAFE_ROUTE_IS_SEPARATE_AND_NOT_INVALIDATED_BY_THIS_GENERIC_P2_FINDING"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    out = audit()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["status"] == "FALSIFICATION_CONFIRMED" else 1)
