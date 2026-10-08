from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate, SEMANTIC_CERTIFICATES
from canonical.tests.test_p3_real_context_v3_admission_v2 import admitted_payload

def test_caller_truth_flags_never_issue_admission():
    p=admitted_payload()
    out=evaluate(p)
    assert out["status"]=="UNKNOWN__FINITE_P3_CONTEXT_SEMANTIC_BINDINGS_INCOMPLETE"
    assert out["pass"] is False
    assert out["v3_runtime_pass"] is True
    assert out["unresolved_semantic_predicates"]==sorted(SEMANTIC_CERTIFICATES)
    assert out["v3_admission_authorized"] is False
    assert out["top_law_eligible"] is False
    assert out["db_admission_authority"] is False

def test_forged_unbound_precommitment_does_not_qualify():
    p=admitted_payload()
    p["context_id"]="P3-ARBITRARY-UNSEEN-CONTEXT"
    p["external_semantic_facts_not_in_v3_input"]={
        "material_conflict":"new material disagreement omitted from required_uncertainty_units",
        "actual_audience_priority":"RISK_FIRST_NOT_BOUND_TO_V3_PROFILE",
    }
    out=evaluate(p)
    assert out["v3_admission_authorized"] is False
    assert out["unresolved_semantic_predicates"]==sorted(SEMANTIC_CERTIFICATES)
    assert all(v["reason"].startswith("UNAUTHENTICATED_SEMANTIC_TRUTH_ASSERTION")
               for v in out["certificate_audit"].values())

def test_claimed_independence_field_is_not_a_trust_anchor():
    p=admitted_payload()
    for cert in p["semantic_certificates"].values():
        cert["independent_verifier"]="SELF-CLAIMED"
        cert["source_sha256"]="0"*64
    out=evaluate(p)
    assert out["pass"] is False
    assert out["top_law_eligible"] is False
