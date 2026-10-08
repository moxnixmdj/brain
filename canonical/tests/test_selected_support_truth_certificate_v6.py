from canonical.runtime.selected_support_truth_certificate_v6 import evaluate

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence,proofs=None):
    return {"predicate_id":"P3","claim":{"claim_id":"C","text":claim,"required":True},
            "evidence":evidence,"semantic_proofs":proofs or {}}

def test_concrete_p3_launch_paraphrase_closes_without_external_semantic_receipt():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The June launch of the product succeeded.")],
    ))
    assert out["pass"] is True,out
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"]==[{
        "evidence_id":"E","relation":"SUPPORTS",
        "grammar":"SUCCESSFUL_LAUNCH_EVENT_ENTAILMENT_V1"}]
    assert out["semantic_proof_audit"]==[]

def test_planned_launch_stays_unknown():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The June launch of the product was planned.")],
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"

def test_failed_launch_stays_unknown():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The June launch of the product failed.")],
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"

def test_time_mismatch_is_resolved_unrelated_not_support():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The July launch of the product succeeded.")],
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="UNRELATED"

def test_existing_numeric_semantics_still_precede_event_and_proof():
    out=evaluate(p(
        "Revenue growth is at least 10.",
        [ev("E","Report states Revenue growth is 12.")],
        {"E":{"steps":[{"kind":"TRUST_ME","to_text":"Revenue growth is at least 10."}]}},
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"
    assert out["semantic_proof_audit"]==[]

def test_external_proof_fallback_still_works_for_other_unresolved_shape_with_test_fixture():
    from canonical.tests.test_selected_support_truth_certificate_v5 import semantic_fixture_proof
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The product's commercial release occurred in June.")],
        {"E":semantic_fixture_proof()},
    ),allow_test_fixtures=True)
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="PROOF_CARRYING_PROPOSITION_ENTAILMENT_V1"

def test_zero_authority_escalation():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The June launch of the product succeeded.")],
    ))
    assert out["pass"] is True
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
