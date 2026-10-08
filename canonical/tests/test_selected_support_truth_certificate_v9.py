from canonical.runtime.selected_support_truth_certificate_v9 import evaluate

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"P3","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

CHAIN="Launch date means ship date. Ship date means release date. Report states that The launch date is June."

def test_nested_definition_counterexample_closes():
    out=evaluate(p("The release date is June.",[ev("E",CHAIN)]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route_v9"]=="SOURCE_DECLARED_EQUIVALENCE_V2_TRANSITIVE"
    assert out["support_evidence_ids"]==["E"]

def test_nested_denial_conflicts():
    e="Launch date means ship date. Ship date means release date. Report denies that The launch date is June."
    out=evaluate(p("The release date is June.",[ev("E",e)]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["conflict_evidence_ids"]==["E"]

def test_nonatomic_nested_definition_stays_unknown():
    e="Launch date means ship date plus review. Ship date means release date. Report states that The launch date is June."
    out=evaluate(p("The release date is June.",[ev("E",e)]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_v8_transitive_set_closure_precedence():
    out=evaluate(p("alpha is a member of Eligible.",[
        ev("E1","Tier A contains alpha."),
        ev("E2","Tier A is a subset of Eligible."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route_v9"]=="V8_BASE"

def test_v8_numeric_precedence():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_route_v9"]=="V8_BASE"

def test_zero_authority():
    out=evaluate(p("The release date is June.",[ev("E",CHAIN)]))
    assert out["pass"]
    assert not out["source_authorization_verified"]
    assert not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"]
    assert not out["u_subtraction_authority"]
    assert not out["terminal_authority"]
    assert out["terminal_credit_delta"]==0
