from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items=4):
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":max_items,"max_chars":5000,"heading_level":2,"require_title":False}

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def req(i,text):
    return {"claim_id":i,"text":text,"required":True}

def payload(claims,evidence):
    return {"v3_input":{"schema":INPUT_SCHEMA,"task":{
      "claims":claims,"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}}

def test_numeric_at_least_realized_end_to_end():
    out=evaluate(payload([req("C1","Revenue growth is at least 10.")],[
      ev("E1","Report states Revenue growth is 12.","REPORT")
    ]))
    assert out["pass"],out
    assert out["rendered_text"]=="- Revenue growth is at least 10. [src:REPORT@p1]"
    receipt=out["support_receipts"][0]["receipt"]
    assert receipt["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_numeric_between_decimal_realized_end_to_end():
    out=evaluate(payload([req("C1","Revenue growth is between 10 and 15.")],[
      ev("E1","Report states Revenue growth is 12.5.","REPORT")
    ]))
    assert out["pass"],out
    assert "Revenue growth is between 10 and 15. [src:REPORT@p1]" in out["rendered_text"]

def test_numeric_false_fails_not_asserted():
    out=evaluate(payload([req("C1","Revenue growth is at least 10.")],[
      ev("E1","Report states Revenue growth is 9.")
    ]))
    assert not out["pass"]
    assert out["reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_numeric_nonnumeric_evidence_unknown():
    out=evaluate(payload([req("C1","Revenue growth is at least 10.")],[
      ev("E1","Report states Revenue growth is strong.")
    ]))
    assert not out["pass"]
    assert out["reason"]=="REQUIRED_CLAIM_SUPPORT_UNKNOWN"

def test_exact_attestation_regression():
    out=evaluate(payload([req("C1","The product launched in June.")],[
      ev("E1","Report states that The product launched in June.","REPORT")
    ]))
    assert out["pass"],out
    assert out["rendered_text"]=="- The product launched in June. [src:REPORT@p1]"

def test_source_declared_equivalence_regression():
    out=evaluate(payload([req("C1","The release date is June.")],[
      ev("E1","Launch date means release date. Report states that The launch date is June.","REPORT")
    ]))
    assert out["pass"],out

def test_zero_support_required_claim_fails_explicitly():
    out=evaluate(payload([req("C1","The product launched in June.")],[
      ev("E1","Report states that The product launched in July.")
    ]))
    assert not out["pass"] and out["reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_irrelevant_parseable_evidence_not_cited():
    out=evaluate(payload([req("C1","Revenue growth is at least 10.")],[
      ev("E1","Report states Revenue growth is 12.","REPORT"),
      ev("E2","Other states Margin rate is 8.","OTHER")
    ]))
    assert out["pass"],out
    assert "REPORT@p1" in out["rendered_text"] and "OTHER@p1" not in out["rendered_text"]

def test_optional_claim_still_rejected():
    c=req("C1","Revenue growth is at least 10.");c["required"]=False
    out=evaluate(payload([c],[ev("E1","Report states Revenue growth is 12.")]))
    assert not out["pass"] and out["reason"]=="OPTIONAL_CLAIM_OUTSIDE_REQUIRED_ONLY_CELL"

def test_authority_boundaries_zero():
    out=evaluate(payload([req("C1","Revenue growth is at least 10.")],[ev("E1","Report states Revenue growth is 12.")]))
    assert out["pass"]
    assert out["p3_contract_cell_authorized"] is True
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0


def test_transitive_categorical_membership_realized_end_to_end():
    out=evaluate(payload([req("C1","Tweety is a member of Animal.")],[
      ev("E1","Report states that Tweety is a member of Canary.","REPORT"),
      ev("E2","Taxonomy states that Canary is a subclass of Bird.","TAX"),
      ev("E3","Taxonomy states that Bird is a subclass of Animal.","TAX"),
    ]))
    assert out["pass"],out
    assert out["rendered_text"]=="- Tweety is a member of Animal. [src:REPORT@p1;TAX@p1]"
    receipt=out["support_receipts"][0]["receipt"]
    assert receipt["categorical_receipt"]["support_proof_paths"]==[["E1","E2","E3"]]


def test_fails_closed_on_wrong_v3_schema_and_unmodeled_contract_fields():
    from copy import deepcopy
    source=payload([req("C1","Revenue growth is at least 10.")],[
        ev("E1","Report states Revenue growth is 12.")
    ])
    variants=[
        ("wrong_schema","V3_INPUT_SCHEMA_INVALID",lambda p:p["v3_input"].update({"schema":"FORGED"})),
        ("unknown_input","UNMODELED_V3_INPUT_FIELDS",lambda p:p["v3_input"].update({"hidden_audience_constraints":{"language":"German"}})),
        ("unknown_task","UNMODELED_TASK_REQUIREMENTS",lambda p:p["v3_input"]["task"].update({"mandatory_semantic_requirement":"Translate to German"})),
        ("unknown_claim","UNMODELED_CLAIM_REQUIREMENTS",lambda p:p["v3_input"]["task"]["claims"][0].update({"forbid_output":True})),
    ]
    for name, reason, mutate in variants:
        attack=deepcopy(source)
        mutate(attack)
        out=evaluate(attack)
        assert out["pass"] is False,(name,out)
        assert out["reason"]==reason,(name,out)
        assert out["p3_contract_cell_authorized"] is False
        assert out["db_admission_authority"] is False
        assert out["terminal_authority"] is False
