from canonical.runtime.selected_support_truth_certificate_v5 import evaluate

def payload(claim,evidence):
    return {
        "predicate_id":"P3_REQUIRED_SUPPORT:C1",
        "claim":{"claim_id":"C1","text":claim,"required":True},
        "evidence":[{"evidence_id":"E1","text":evidence,"verified":True,
                     "provenance":[{"source_id":"S1","locator":"L1"}]}],
    }

def test_active_passive_support_now_closes():
    out=evaluate(payload("Alice must verify report","report must be verified by Alice"))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="PREDICATE_ARGUMENT_SUPPORT_V1"

def test_active_passive_conflict_now_closes_false():
    out=evaluate(payload("Alice must verify report","report must not be verified by Alice"))
    assert out["pass"] is True
    assert out["predicate_truth"]=="FALSE"
    assert out["conflict_evidence_ids"]==["E1"]

def test_coordination_stays_unknown():
    out=evaluate(payload("Alice must verify report","Alice must verify report and archive invoice"))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"

def test_definition_precedence_preserved():
    out=evaluate(payload("Alice must verify report","Report means invoice"))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"

def test_exact_attestation_still_works():
    out=evaluate(payload("Alice must verify report","Source states that Alice must verify report"))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_no_authority_smuggling():
    out=evaluate(payload("Alice must verify report","report must be verified by Alice"))
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
