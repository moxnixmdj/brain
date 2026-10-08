from canonical.runtime.selected_support_truth_certificate_v6 import evaluate

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"X",
            "claim":{"claim_id":"C","text":claim,"required":True},
            "evidence":evidence}

def test_predicate_argument_active_passive_support():
    out=evaluate(p("Alice must verify report",[ev("E","report must be verified by Alice")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="PREDICATE_ARGUMENT_SUPPORT_V1"

def test_predicate_argument_active_passive_conflict():
    out=evaluate(p("Alice must verify report",[ev("E","report must not be verified by Alice")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["grammar"]=="PREDICATE_ARGUMENT_SUPPORT_V1"

def test_predicate_argument_coordination_stays_unknown():
    out=evaluate(p("Alice must verify report",[ev("E","Alice must verify report and archive invoice")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_definition_precedence_stays_strict():
    out=evaluate(p("Alice must verify report",[ev("E","Report means invoice")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_membership_v5_regression():
    out=evaluate(p("Asset category is in {equity, bond}.",[ev("E","Report states Asset category is bond.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="SET_MEMBERSHIP_V1"

def test_numeric_v5_regression():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_categorical_v5_regression():
    out=evaluate(p("sparrow is a member of animal",[
        ev("E1","Report states sparrow is a member of bird"),
        ev("E2","Report states bird is a subclass of animal"),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert "categorical_support_receipt" in out
    assert {r["grammar"] for r in out["relation_audit"] if r["relation"]=="SUPPORTS"}=={"EXPLICIT_CATEGORICAL_RELATION_V1"}

def test_exact_attestation_regression():
    out=evaluate(p("The product launched in June.",[
        ev("E","Report states that The product launched in June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_authority_zero():
    out=evaluate(p("Alice must verify report",[ev("E","report must be verified by Alice")]))
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
