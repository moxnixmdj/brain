from canonical.runtime.selected_support_truth_certificate_v3 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}
def p(claim,evidence,alias="X"):
    return {"predicate_id":alias,"claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_numeric_true():
    o=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert o["pass"] and o["predicate_truth"]=="TRUE" and o["selected_policy_id"]==TRUE_POLICY
    assert o["relation_audit"][0]["grammars"]==["NUMERIC_COMPARISON_V1"]
def test_numeric_false():
    o=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 8.")]))
    assert o["pass"] and o["predicate_truth"]=="FALSE" and o["selected_policy_id"]==FALSE_POLICY
def test_numeric_mixed_support_and_conflict_false():
    o=evaluate(p("Revenue growth is at least 10.",[
      ev("E1","Report states Revenue growth is 12."),
      ev("E2","Other states Revenue growth is 8.")]))
    assert o["pass"] and o["predicate_truth"]=="FALSE"
    assert o["support_evidence_ids"]==["E1"] and o["conflict_evidence_ids"]==["E2"]
def test_numeric_exact_attestation_of_predicate_supports():
    o=evaluate(p("Revenue growth is at least 10.",[
      ev("E","Report states that Revenue growth is at least 10.")]))
    assert o["pass"] and o["predicate_truth"]=="TRUE"
    assert "EXACT_ATTESTATION_V1" in o["relation_audit"][0]["grammars"]
def test_numeric_fact_inside_attestation_frame_can_still_compare():
    o=evaluate(p("Revenue growth is at least 10.",[
      ev("E","Report reports that Revenue growth is 12.")]))
    assert o["pass"] and o["predicate_truth"]=="TRUE"
    assert "NUMERIC_COMPARISON_V1" in o["relation_audit"][0]["grammars"]
def test_exact_fact_regression():
    o=evaluate(p("Revenue growth is 12.",[ev("E","Report states Revenue growth is 12.")]))
    assert o["pass"] and o["predicate_truth"]=="TRUE"
    assert "ENTITY_FIELD_VALUE_FACT_V1" in o["relation_audit"][0]["grammars"]
def test_attestation_regression():
    o=evaluate(p("The product launched in June.",[
      ev("E","Report states that The product launched in June.")]))
    assert o["pass"] and o["predicate_truth"]=="TRUE"
    assert "EXACT_ATTESTATION_V1" in o["relation_audit"][0]["grammars"]
def test_paraphrase_still_unknown():
    o=evaluate(p("The product launched in June.",[
      ev("E","The June launch of the product succeeded.")]))
    assert not o["pass"] and o["predicate_truth"]=="UNKNOWN"
def test_numeric_nonnumeric_evidence_unknown():
    o=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is high.")]))
    assert not o["pass"] and o["predicate_truth"]=="UNKNOWN"
def test_alias_no_authority():
    a=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")],"A"))
    b=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")],"B"))
    assert a["predicate_id"]==b["predicate_id"] and a["requested_predicate_id"]!=b["requested_predicate_id"]
def test_optional_rejected():
    q=p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]);q["claim"]["required"]=False
    assert evaluate(q)["reason"]=="CLAIM_NOT_STRUCTURALLY_REQUIRED"
def test_authority_zero():
    o=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert not o["source_authorization_verified"] and not o["policy_adequacy_authority"]
    assert not o["db_admission_authority"] and not o["u_subtraction_authority"] and not o["terminal_authority"]
    assert o["terminal_credit_delta"]==0
