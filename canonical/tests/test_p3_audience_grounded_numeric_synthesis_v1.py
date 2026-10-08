"""P3 bounded source-derived support, audience counterfactual, and fail-closed probes."""
import copy
import pytest
from canonical.runtime.p3_audience_grounded_numeric_synthesis_v1 import (
    solve, UnresolvedEvidence,
)
def case(audience="executive"):
    return {
        "contract":"EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "task":{
            "audience":audience,
            "required_claims":["R"],
            "claims":[
                {"claim_id":"R","metric":"revenue","unit":"USD","kind":"trend","relation":"at_least","threshold":"100.00"},
                {"claim_id":"T","metric":"revenue","unit":"USD","kind":"trend","relation":"at_least","threshold":"115.00"},
                {"claim_id":"M","metric":"latency","unit":"ms","kind":"mechanism","relation":"at_most","threshold":"50.00"},
                {"claim_id":"C","metric":"errors","unit":"count","kind":"control","relation":"at_most","threshold":"2"},
                {"claim_id":"X","metric":"revenue","unit":"USD","kind":"risk","relation":"at_least","threshold":"150"},
            ],
            "evidence":[
                {"evidence_id":"s1","metric":"revenue","unit":"USD","value":"130.00","source_id":"ledger-A"},
                {"evidence_id":"s2","metric":"revenue","unit":"USD","value":"110.00","source_id":"ledger-B"},
                {"evidence_id":"s3","metric":"latency","unit":"ms","value":"42.00","source_id":"trace-C"},
                {"evidence_id":"s4","metric":"errors","unit":"count","value":"1","source_id":"audit-D"},
            ],
            "format_constraints":{"max_claims":3,"ordered_required_first":True},
        },
    }

def test_audience_counterfactual_changes_output():
    ex=solve(case("executive"))
    en=solve(case("engineer"))
    au=solve(case("auditor"))
    assert ex["selected_claims"]==["R","T"]
    assert en["selected_claims"]==["R","M"]
    assert au["selected_claims"]==["R","C"]
    assert ex["input_sha256"] != en["input_sha256"]
    assert all(z["terminal_credit_delta"]==0 for z in (ex,en,au))

def test_conflict_exposed_not_erased():
    out=solve(case())
    assert out["uncertainty_claims"]==["T"]
    evidence=out["claim_provenance"]["T"]
    assert {r["comparison_holds"] for r in evidence}=={True,False}
    assert {r["source_id"] for r in evidence}=={"ledger-A","ledger-B"}

def test_unit_mismatch_never_supports_required():
    p=case()
    p["task"]["evidence"][0]["unit"]="EUR"
    p["task"]["evidence"][1]["unit"]="EUR"
    with pytest.raises(UnresolvedEvidence,match="REQUIRED_CLAIM_NOT_PROVABLE"):
        solve(p)

def test_floating_point_and_nan_banned():
    for bad in (130.0, "NaN","Infinity"):
        p=case();p["task"]["evidence"][0]["value"]=bad
        with pytest.raises(UnresolvedEvidence):
            solve(p)

def test_hidden_support_relevance_not_consumed():
    for key in ("support","role","relevance","audience"):
        p=case();p["task"]["evidence"][0][key]="supported"
        with pytest.raises(UnresolvedEvidence,match="UNVERIFIED_EVIDENCE_LABEL_FORBIDDEN"):
            solve(p)

def test_unverified_claim_labels_not_consumed():
    p=case();p["task"]["claims"][0]["support"]="supported"
    with pytest.raises(UnresolvedEvidence,match="UNVERIFIED_CLAIM_LABEL_FORBIDDEN"):
        solve(p)

def test_provenance_bytes_content_bound():
    a=solve(case())
    p=case();p["task"]["evidence"][0]["source_id"]="different"
    b=solve(p)
    assert a["input_sha256"]!=b["input_sha256"]
    assert a["claim_provenance"]["R"]!=b["claim_provenance"]["R"]
    assert not b["source_authorization_verified"]

def test_required_claim_cannot_be_dropped_for_optional():
    p=case();p["task"]["format_constraints"]["max_claims"]=0
    with pytest.raises(UnresolvedEvidence,match="REQUIRED_CLAIMS_EXCEED_CAPACITY"):
        solve(p)

def test_negative_evidence_cannot_fake_support():
    p=case()
    for e in p["task"]["evidence"]:
        if e["metric"]=="revenue":e["value"]="10"
    with pytest.raises(UnresolvedEvidence,match="REQUIRED_CLAIM_NOT_PROVABLE"):
        solve(p)

def test_unsupported_audience_rejected():
    with pytest.raises(UnresolvedEvidence,match="UNSUPPORTED_AUDIENCE"):
        solve(case("unknown"))

def test_no_misleading_global_credit():
    out=solve(case())
    assert not out["semantic_claim_adequacy_verified"]
    assert not out["target_relative_quality_verified"]
    assert not out["u_subtraction_authorized"]
    assert not out["terminal_authority"]
    assert out["terminal_credit_delta"]==0

def test_duplicate_evidence_id_fails():
    p=case();p["task"]["evidence"][1]["evidence_id"]="s1"
    with pytest.raises(UnresolvedEvidence,match="DUPLICATE_EVIDENCE_ID"):
        solve(p)
