from canonical.runtime.selected_support_truth_certificate_v5 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"X","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_v4_numeric_regression():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_v4_exact_attestation_regression():
    out=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_v4_source_definition_regression():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="SOURCE_DECLARED_EQUIVALENCE_V1"

def test_direct_membership_support():
    out=evaluate(p("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of Canary.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["selected_policy_id"]==TRUE_POLICY
    assert out["support_evidence_ids"]==["E1"]

def test_transitive_membership_support_uses_whole_proof_path():
    out=evaluate(p("Tweety is a member of Animal.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
        ev("E3","Taxonomy states Bird is a subclass of Animal."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE",out
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["categorical_support_receipt"]["support_proof_paths"]==[["E1","E2","E3"]]

def test_membership_conflict_blocks_assertion():
    out=evaluate(p("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Report states that Tweety is not a member of Bird."),
        ev("E3","Taxonomy states Canary is a subclass of Bird."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["selected_policy_id"]==FALSE_POLICY
    assert out["support_evidence_ids"]==["E1"]
    assert out["conflict_evidence_ids"]==["E2","E3"]

def test_unrelated_category_evidence_means_not_supported():
    out=evaluate(p("Tweety is a member of Canary.",[
        ev("E1","Report states that Robin is a member of Bird.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["support_evidence_ids"]==[]

def test_malformed_category_evidence_is_unknown():
    out=evaluate(p("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of.")
    ]))
    assert not out["pass"]
    assert out["predicate_truth"]=="UNKNOWN"

def test_negative_membership_downward_support():
    out=evaluate(p("Tweety is not a member of Canary.",[
        ev("E1","Report states that Tweety is not a member of Bird."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_evidence_ids"]==["E1","E2"]

def test_no_illegal_negative_upward_support():
    out=evaluate(p("Tweety is not a member of Bird.",[
        ev("E1","Report states that Tweety is not a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"

def test_authority_stays_zero():
    out=evaluate(p("Tweety is a member of Animal.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Animal."),
    ]))
    assert out["pass"]
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    assert not out["terminal_authority"] and out["terminal_credit_delta"]==0
