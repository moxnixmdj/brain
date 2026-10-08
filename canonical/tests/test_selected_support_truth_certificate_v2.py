from canonical.runtime.selected_support_truth_certificate_v2 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence,alias="X"):
    return {"predicate_id":alias,"claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_freeform_attestation_true():
    out=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_freeform_denial_false():
    out=evaluate(p("The product launched in June.",[ev("E","Report denies that The product launched in June.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE" and out["selected_policy_id"]==FALSE_POLICY
    assert out["conflict_evidence_ids"]==["E"]

def test_unrelated_attestation_is_resolved_but_not_support():
    out=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in July.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"

def test_unwrapped_paraphrase_unknown():
    out=evaluate(p("The product launched in June.",[ev("E","The June launch of the product succeeded.")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_bounded_fact_regression_true():
    out=evaluate(p("Revenue growth is 12.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="ENTITY_FIELD_VALUE_FACT_V1"

def test_bounded_fact_conflict_false():
    out=evaluate(p("Revenue growth is 12.",[ev("E1","Report states Revenue growth is 12."),ev("E2","Other states Revenue growth is 11.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"

def test_mixed_grammars_all_must_resolve():
    out=evaluate(p("The product launched in June.",[
      ev("E1","Report states that The product launched in June."),
      ev("E2","Analyst suggests a June release happened.")
    ]))
    assert not out["pass"] and out["unresolved_evidence_ids"]==["E2"]

def test_alias_has_no_authority():
    a=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")],"A"))
    b=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")],"B"))
    assert a["predicate_id"]==b["predicate_id"] and a["requested_predicate_id"]!=b["requested_predicate_id"]

def test_evidence_changes_observation_not_identity():
    a=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")]))
    b=evaluate(p("The product launched in June.",[ev("E","Report denies that The product launched in June.")]))
    assert a["predicate_id"]==b["predicate_id"]
    assert a["evidence_set_sha256"]!=b["evidence_set_sha256"]
    assert a["predicate_truth"]!=b["predicate_truth"]

def test_authority_zero():
    out=evaluate(p("The product launched in June.",[ev("E","Report states that The product launched in June.")]))
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"] and not out["terminal_authority"]
    assert out["terminal_credit_delta"]==0
