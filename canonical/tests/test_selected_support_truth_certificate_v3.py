from canonical.runtime.bounded_event_nominalization_support_v1 import classify_support
from canonical.runtime.selected_support_truth_certificate_v3 import evaluate, TRUE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def payload(claim,evidence):
    return {"predicate_id":"P3-LIVE-PARAPHRASE-CELL",
            "claim":{"claim_id":"C","text":claim,"required":True},
            "evidence":evidence}

def test_live_counterexample_is_now_soundly_resolved():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","The June launch of the product succeeded.")]
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="EVENT_NOMINALIZATION_V1"

def test_entity_mismatch_is_unrelated_not_support():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","The June launch of the service succeeded.")]
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="FALSE"

def test_time_mismatch_is_unrelated_not_support():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","The July launch of the product succeeded.")]
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="FALSE"

def test_non_successful_launch_stays_unknown():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","The June launch of the product was planned.")]
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["unresolved_evidence_ids"]==["E1"]

def test_general_paraphrase_stays_unknown():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","Customers first received the product during June.")]
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"

def test_negation_not_accidentally_admitted():
    r=classify_support(
        "The product launched in June.",
        "The June launch of the product did not succeed.",
        evidence_id="E1",
    )
    assert r["status"]=="UNRESOLVED"
    assert r["relation"]=="UNKNOWN"

def test_existing_exact_attestation_regression():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","Report states that The product launched in June.")]
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_existing_fact_regression():
    out=evaluate(payload(
        "Revenue growth is 12.",
        [ev("E1","Report states Revenue growth is 12.")]
    ))
    assert out["pass"] is True
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="ENTITY_FIELD_VALUE_FACT_V1"

def test_authority_stays_zero():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E1","The June launch of the product succeeded.")]
    ))
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
