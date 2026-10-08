from canonical.runtime.selected_support_truth_certificate_v3 import evaluate,TRUE_POLICY,FALSE_POLICY

def ev(i,text):
    return {"evidence_id":i,"text":text,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}

def p(claim,evidence,alias="X"):
    return {"predicate_id":alias,"claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def test_source_declared_alias_supports_claim():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE" and out["selected_policy_id"]==TRUE_POLICY
    assert out["relation_audit"][0]["grammar"]=="SOURCE_DECLARED_EQUIVALENCE_V1"

def test_source_declared_alias_works_reverse_surface():
    out=evaluate(p("The launch date is June.",[
        ev("E","Launch date means release date. Report states that The release date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"

def test_source_declared_denial_conflicts():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report denies that The launch date is June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="FALSE" and out["selected_policy_id"]==FALSE_POLICY

def test_ordinary_paraphrase_without_definition_unknown():
    out=evaluate(p("The product launched in June.",[
        ev("E","The June launch of the product succeeded.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_conflicting_definitions_unknown():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Launch date means shipment date. Report states that The launch date is June.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_nested_definition_unknown_v1():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means ship date. Ship date means release date. Report states that The launch date is June.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_unparsed_extra_sentence_unknown():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. The schedule is complicated. Report states that The launch date is June.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_mixed_polarity_same_canonical_proposition_unknown():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June. Other denies that The release date is June.")
    ]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_exact_attestation_regression():
    out=evaluate(p("The product launched in June.",[
        ev("E","Report states that The product launched in June.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="EXACT_ATTESTATION_V1"

def test_fact_regression():
    out=evaluate(p("Revenue growth is 12.",[
        ev("E","Report states Revenue growth is 12.")
    ]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="ENTITY_FIELD_VALUE_FACT_V1"

def test_definition_change_changes_observation_not_predicate_identity():
    a=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    b=evaluate(p("The release date is June.",[
        ev("E","Launch date means shipment date. Report states that The launch date is June.")
    ]))
    assert a["predicate_id"]==b["predicate_id"]
    assert a["evidence_set_sha256"]!=b["evidence_set_sha256"]
    assert a["predicate_truth"]=="TRUE"
    assert b["predicate_truth"]=="FALSE"

def test_alias_label_has_no_authority():
    a=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ],"A"))
    b=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ],"B"))
    assert a["predicate_id"]==b["predicate_id"]
    assert a["requested_predicate_id"]!=b["requested_predicate_id"]
    assert not a["requested_predicate_id_authority"]

def test_authority_boundaries_zero():
    out=evaluate(p("The release date is June.",[
        ev("E","Launch date means release date. Report states that The launch date is June.")
    ]))
    assert not out["source_authorization_verified"] and not out["policy_adequacy_authority"]
    assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    assert not out["terminal_authority"] and out["terminal_credit_delta"]==0
