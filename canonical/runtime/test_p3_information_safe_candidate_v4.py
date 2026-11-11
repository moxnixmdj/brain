from canonical.runtime.p3_information_safe_candidate_v4 import solve
from canonical.runtime.p3_information_safe_proof_suite_v3 import (
    generate_case,
    public_task,
    score_case,
)

def _unresolved(out):
    return {x["claim_id"]: x["reason"] for x in out["unresolved_required_claims"]}

def test_v4_preserves_v3_synthetic_behavior_for_256_cases():
    for seed in range(256):
        case = generate_case(seed, 3)
        out = solve(public_task(case))
        verdict = score_case(case, out)
        assert verdict["pass"], (seed, verdict, out)

def test_required_claim_with_no_matching_evidence_fails_closed():
    case = generate_case(101, 3)
    req = case["task"]["required_claims"][0]
    metric = next(c["metric"] for c in case["task"]["claims"] if c["claim_id"] == req)
    case["task"]["evidence"] = [e for e in case["task"]["evidence"] if e["metric"] != metric]
    out = solve(public_task(case))
    assert _unresolved(out)[req] == "NO_MATCHING_EVIDENCE"
    assert req not in out["selected_claims"]

def test_required_claim_with_contradicting_evidence_fails_closed():
    case = generate_case(102, 3)
    req = case["task"]["required_claims"][0]
    claim = next(c for c in case["task"]["claims"] if c["claim_id"] == req)
    threshold = float(claim["threshold"])
    for e in case["task"]["evidence"]:
        if e["metric"] == claim["metric"]:
            e["value"] = threshold - 100 if claim["relation"] == "at_least" else threshold + 100
    out = solve(public_task(case))
    assert _unresolved(out)[req] == "INSUFFICIENT_SUPPORT"
    assert req not in out["selected_claims"]

def test_mixed_units_are_not_collapsed_into_scalar_votes():
    case = generate_case(103, 3)
    req = case["task"]["required_claims"][0]
    metric = next(c["metric"] for c in case["task"]["claims"] if c["claim_id"] == req)
    for e in case["task"]["evidence"]:
        if e["metric"] == metric:
            e["unit"] = "percent"
            break
    out = solve(public_task(case))
    assert _unresolved(out)[req] == "MIXED_UNITS"
    assert req not in out["selected_claims"]

def test_selected_claim_receipts_preserve_evidence_identity_provenance_and_unit():
    case = generate_case(104, 3)
    out = solve(public_task(case))
    assert out["selected_claims"]
    for cid in out["selected_claims"]:
        rows = out["claim_evidence"][cid]
        assert rows
        assert all("evidence_id" in e and "provenance" in e and "unit" in e for e in rows)

def test_output_budget_cannot_silently_drop_required_claim():
    case = generate_case(105, 3)
    case["task"]["max_claims"] = 1
    out = solve(public_task(case))
    assert any(
        x["reason"] == "OUTPUT_BUDGET_EXCLUDES_REQUIRED_CLAIM"
        for x in out["unresolved_required_claims"]
    )
