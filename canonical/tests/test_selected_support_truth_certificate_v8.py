from canonical.runtime.selected_support_truth_certificate_v8 import evaluate

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"P3","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_transitive_membership_closure_supports():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","Tier A contains alpha."),
        ev("E2","Tier A is a subset of Approved."),
        ev("E3","Approved is a subset of Eligible."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route"]=="FINITE_SET_INCLUSION_MEMBERSHIP_CLOSURE_V1"
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["set_membership_closure"]["proof"]["set_path"]==["tier a","approved","eligible"]

def test_complete_target_absence_is_false():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","The complete members of Eligible are {beta, gamma}.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"

def test_inconsistent_path_and_complete_absence_is_unknown():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","Tier A contains alpha."),
        ev("E2","Tier A is a subset of Eligible."),
        ev("E3","The complete members of Eligible are {beta, gamma}."),
    ]))
    assert not out["pass"]
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["set_membership_closure"]["status"]=="UNRESOLVED__EVIDENCE_INCONSISTENT"

def test_unparsed_row_prevents_graph_proof():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","Tier A contains alpha."),
        ev("E2","Tier A is a subset of Eligible."),
        ev("E3","Someone vaguely disputes this."),
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_v7_numeric_result_has_precedence():
    out=evaluate(p("Revenue growth is at least 10.",[
        ev("E","Report states Revenue growth is 12.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route"]=="V7_SINGLE_EVIDENCE_PORTFOLIO"

def test_v7_direct_membership_has_precedence():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E","Eligible contains alpha.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route"]=="V7_SINGLE_EVIDENCE_PORTFOLIO"

def test_zero_authority():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","Tier A contains alpha."),
        ev("E2","Tier A is a subset of Eligible."),
    ]))
    assert out["pass"]
    assert not out["source_authorization_verified"]
    assert not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"]
    assert not out["u_subtraction_authority"]
    assert not out["terminal_authority"]
    assert out["terminal_credit_delta"]==0
