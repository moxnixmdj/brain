from canonical.runtime.bounded_set_membership_support_v1 import parse_set_membership_claim,classify_support
from canonical.runtime.selected_support_truth_certificate_v5 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"X","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_parse_positive_in():
    out=parse_set_membership_claim("Asset category is in {equity, bond}.")
    assert out["status"]=="RESOLVED" and out["operator"]=="IN"
    assert out["members"]==["bond","equity"]

def test_parse_negative_one_of():
    out=parse_set_membership_claim("Asset category is not one of {cash, commodity}.")
    assert out["status"]=="RESOLVED" and out["operator"]=="NOT_IN"

def test_positive_membership_supports():
    out=classify_support("Asset category is in {equity, bond}.","Report states Asset category is equity.",evidence_id="E")
    assert out["relation"]=="SUPPORTS"

def test_positive_membership_conflicts():
    out=classify_support("Asset category is in {equity, bond}.","Report states Asset category is cash.",evidence_id="E")
    assert out["relation"]=="CONFLICTS"

def test_negative_membership_supports():
    out=classify_support("Asset category is not in {cash, commodity}.","Report states Asset category is equity.",evidence_id="E")
    assert out["relation"]=="SUPPORTS"

def test_negative_membership_conflicts():
    out=classify_support("Asset category is not in {cash, commodity}.","Report states Asset category is cash.",evidence_id="E")
    assert out["relation"]=="CONFLICTS"

def test_unrelated_resolved():
    out=classify_support("Asset category is in {equity, bond}.","Report states Region code is EU.",evidence_id="E")
    assert out["status"]=="RESOLVED" and out["relation"]=="UNRELATED"

def test_duplicate_members_fail():
    out=parse_set_membership_claim("Asset category is in {equity, equity}.")
    assert out["status"]=="FAIL_CLOSED"

def test_v5_membership_true():
    out=evaluate(p("Asset category is in {equity, bond}.",[ev("E","Report states Asset category is bond.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="SET_MEMBERSHIP_V1"

def test_v5_membership_false():
    out=evaluate(p("Asset category is in {equity, bond}.",[ev("E","Report states Asset category is cash.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE" and out["selected_policy_id"]==FALSE_POLICY
    assert out["relation_audit"][0]["grammar"]=="SET_MEMBERSHIP_V1"

def test_v5_membership_uncheckable_evidence_unknown():
    out=evaluate(p("Asset category is in {equity, bond}.",[ev("E","The asset appears defensive.")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_v5_numeric_regression():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_v5_fact_regression():
    out=evaluate(p("Asset category is equity.",[ev("E","Report states Asset category is equity.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"

def test_authority_zero():
    out=evaluate(p("Asset category is in {equity, bond}.",[ev("E","Report states Asset category is equity.")]))
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    assert not out["terminal_authority"] and out["terminal_credit_delta"]==0
