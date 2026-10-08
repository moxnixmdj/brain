from canonical.runtime.selected_support_truth_certificate_v4 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"X","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def check_true(claim,value):
    out=evaluate(p(claim,[ev("E",f"Report states Revenue growth is {value}.")]))
    assert out["pass"],out
    assert out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def check_false(claim,value):
    out=evaluate(p(claim,[ev("E",f"Report states Revenue growth is {value}.")]))
    assert out["pass"],out
    assert out["predicate_truth"]=="FALSE" and out["selected_policy_id"]==FALSE_POLICY
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_at_least():
    check_true("Revenue growth is at least 10.","10")
    check_true("Revenue growth is at least 10.","12")
    check_false("Revenue growth is at least 10.","9")

def test_at_most():
    check_true("Revenue growth is at most 10.","10")
    check_true("Revenue growth is at most 10.","9")
    check_false("Revenue growth is at most 10.","11")

def test_strict_greater_less():
    check_true("Revenue growth is greater than 10.","11")
    check_false("Revenue growth is greater than 10.","10")
    check_true("Revenue growth is less than 10.","9")
    check_false("Revenue growth is less than 10.","10")

def test_between_inclusive():
    check_true("Revenue growth is between 10 and 15.","10")
    check_true("Revenue growth is between 10 and 15.","12.5")
    check_true("Revenue growth is between 10 and 15.","15")
    check_false("Revenue growth is between 10 and 15.","15.1")

def test_unrelated_numeric_fact_is_resolved_unrelated():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Margin rate is 8.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="UNRELATED"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_nonnumeric_evidence_for_numeric_claim_is_unknown_not_false():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is strong.")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_inverted_interval_fails_unknown():
    out=evaluate(p("Revenue growth is between 15 and 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_exact_attestation_of_numeric_proposition_still_supports():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states that Revenue growth is at least 10.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_equality_fact_regression():
    out=evaluate(p("Revenue growth is 12.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="ENTITY_FIELD_VALUE_FACT_V1"

def test_source_defined_equivalence_regression():
    out=evaluate(p("The release date is June.",[
      ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="SOURCE_DECLARED_EQUIVALENCE_V1"

def test_authority_zero():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    assert not out["terminal_authority"] and out["terminal_credit_delta"]==0
