from canonical.runtime.selected_support_truth_certificate_v5 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence):
    return {"predicate_id":"X","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_membership_true_from_exact_complete_set():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states Approved regions are exactly {Egypt, Jordan, Oman}.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="EXACT_SET_MEMBERSHIP_V1"

def test_membership_false_from_exact_complete_set():
    out=evaluate(p("Qatar is in Approved regions.",[
      ev("E","Report states Approved regions are exactly {Egypt, Jordan, Oman}.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE" and out["selected_policy_id"]==FALSE_POLICY

def test_belongs_to_surface():
    out=evaluate(p("Egypt belongs to Approved regions.",[
      ev("E","Report states Approved regions are exactly {Egypt, Jordan, Oman}.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"

def test_different_set_is_unrelated():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states Blocked regions are exactly {Egypt, Jordan}.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="UNRELATED"

def test_non_exact_set_evidence_unknown_not_negative():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states Approved regions include Egypt, Jordan, Oman.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_duplicate_member_enumeration_unknown():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states Approved regions are exactly {Egypt, Egypt}.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_case_and_spacing_normalize():
    out=evaluate(p("egypt is in approved regions.",[
      ev("E","Report states Approved   regions are exactly { EGYPT, Jordan }. ")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"

def test_exact_attestation_of_membership_proposition_still_supports():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states that Egypt is in Approved regions.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_numeric_regression():
    out=evaluate(p("Revenue growth is at least 10.",[ev("E","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_source_defined_regression():
    out=evaluate(p("The release date is June.",[
      ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"

def test_authority_zero():
    out=evaluate(p("Egypt is in Approved regions.",[
      ev("E","Report states Approved regions are exactly {Egypt, Jordan, Oman}.")
    ]))
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    assert not out["terminal_authority"] and out["terminal_credit_delta"]==0
