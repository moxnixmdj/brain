from canonical.runtime.selected_support_truth_certificate_v5 import evaluate,TRUE_POLICY,FALSE_POLICY

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


def test_direct_categorical_membership():
    out=evaluate(p("Tweety is a member of Bird.",[
      ev("E1","Report states that Tweety is a member of Bird.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="CATEGORICAL_RELATION_V1"

def test_transitive_categorical_membership_uses_full_proof():
    out=evaluate(p("Tweety is a member of Animal.",[
      ev("E1","Report states that Tweety is a member of Canary."),
      ev("E2","Taxonomy states that Canary is a subclass of Bird."),
      ev("E3","Taxonomy states that Bird is a subclass of Animal."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["categorical_receipt"]["support_proof_paths"]==[["E1","E2","E3"]]

def test_categorical_conflict_blocks_positive_support():
    out=evaluate(p("Tweety is a member of Canary.",[
      ev("E1","A states that Tweety is a member of Canary."),
      ev("E2","B states that Tweety is not a member of Animal."),
      ev("E3","T states that Canary is a subclass of Animal."),
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["support_evidence_ids"]==["E1"]
    assert out["conflict_evidence_ids"]==["E2","E3"]

def test_unchecked_extra_evidence_keeps_categorical_claim_unknown():
    out=evaluate(p("Tweety is a member of Bird.",[
      ev("E1","Report states that Tweety is a member of Bird."),
      ev("E2","This prose has no checked semantic relation.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"
    assert out["unresolved_evidence_ids"]==["E2"]


def test_categorical_paraphrase_evidence_keeps_claim_unknown():
    out=evaluate(p("Tweety is a member of Bird.",[
      ev("E1","Report states that Tweety is a member of Bird."),
      ev("E2","Report states that Tweety does not belong to Bird.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"
    assert out["unresolved_evidence_ids"]==["E2"]
