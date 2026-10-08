from canonical.runtime.selected_support_truth_certificate_v7 import evaluate

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence,proofs=None):
    return {"predicate_id":"P3","claim":{"claim_id":"C","text":claim,"required":True},
            "evidence":evidence,"semantic_proofs":proofs or {}}

def test_complete_set_membership_supports():
    out=evaluate(p(
        "beta is a member of Approved products.",
        [ev("E","The complete members of Approved products are {alpha, beta, gamma}.")],
    ))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_SET_MEMBERSHIP_V1"

def test_complete_set_nonmembership_conflicts():
    out=evaluate(p(
        "delta is a member of Approved products.",
        [ev("E","The complete members of Approved products are {alpha, beta, gamma}.")],
    ))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="CONFLICTS"

def test_positive_membership_does_not_invent_closed_world_absence():
    out=evaluate(p(
        "beta is a member of Approved products.",
        [ev("E","Approved products contains alpha.")],
    ))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="UNRELATED"

def test_launch_event_regression():
    out=evaluate(p(
        "The product launched in June.",
        [ev("E","The June launch of the product succeeded.")],
    ))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="SUCCESSFUL_LAUNCH_EVENT_ENTAILMENT_V1"

def test_uncontrolled_membership_language_remains_unknown():
    out=evaluate(p(
        "beta is a member of Approved products.",
        [ev("E","Beta is usually considered approved.")],
    ))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_numeric_precedence_regression():
    out=evaluate(p(
        "Revenue growth is at least 10.",
        [ev("E","Report states Revenue growth is 12.")],
    ))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_zero_authority():
    out=evaluate(p(
        "beta is a member of Approved products.",
        [ev("E","Approved products contains beta.")],
    ))
    assert out["pass"]
    assert not out["source_authorization_verified"]
    assert not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"]
    assert not out["u_subtraction_authority"]
    assert not out["terminal_authority"]
    assert out["terminal_credit_delta"]==0
