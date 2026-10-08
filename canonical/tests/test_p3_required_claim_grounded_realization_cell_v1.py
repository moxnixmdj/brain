from canonical.runtime.p3_required_claim_grounded_realization_cell_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items=4):
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":max_items,"max_chars":5000,"heading_level":2,"require_title":False}

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def payload(claims,evidence):
    return {"v3_input":{"schema":INPUT_SCHEMA,"task":{
      "claims":claims,"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}}

def req(i,text):
    return {"claim_id":i,"text":text,"required":True}

def test_exact_attested_required_claim_is_realized_with_support_provenance():
    out=evaluate(payload([req("C1","The product launched in June.")],[
      ev("E1","Report states that The product launched in June.","REPORT")
    ]))
    assert out["pass"],out
    assert out["rendered_text"]=="- The product launched in June. [src:REPORT@p1]"
    assert out["render_trace"][0]["provenance"]==[{"source_id":"REPORT","locator":"p1"}]

def test_source_declared_equivalence_is_realized():
    out=evaluate(payload([req("C1","The release date is June.")],[
      ev("E1","Launch date means release date. Report states that The launch date is June.","REPORT")
    ]))
    assert out["pass"],out
    assert "The release date is June. [src:REPORT@p1]" in out["rendered_text"]

def test_zero_support_required_claim_fails_explicitly():
    out=evaluate(payload([req("C1","The product launched in June.")],[
      ev("E1","Report states that The product launched in July.")
    ]))
    assert not out["pass"]
    assert out["reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_unchecked_paraphrase_fails_unknown_not_silent_omit():
    out=evaluate(payload([req("C1","The product launched in June.")],[
      ev("E1","The June launch of the product succeeded.")
    ]))
    assert not out["pass"]
    assert out["reason"]=="REQUIRED_CLAIM_SUPPORT_UNKNOWN"

def test_conflict_fails_instead_of_asserting():
    out=evaluate(payload([req("C1","Revenue growth is 12.")],[
      ev("E1","Report states Revenue growth is 12."),
      ev("E2","Other states Revenue growth is 11.")
    ]))
    assert not out["pass"]
    assert out["reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_optional_claim_rejected():
    c=req("C1","Revenue growth is 12.");c["required"]=False
    out=evaluate(payload([c],[ev("E1","Report states Revenue growth is 12.")]))
    assert not out["pass"] and out["reason"]=="OPTIONAL_CLAIM_OUTSIDE_REQUIRED_ONLY_CELL"

def test_irrelevant_parseable_evidence_not_cited():
    out=evaluate(payload([req("C1","Revenue growth is 12.")],[
      ev("E1","Report states Revenue growth is 12.","REPORT"),
      ev("E2","Other states Margin rate is 8.","OTHER")
    ]))
    assert out["pass"],out
    assert "REPORT@p1" in out["rendered_text"]
    assert "OTHER@p1" not in out["rendered_text"]

def test_item_budget_fails_without_dropping_required_claim():
    p=payload([req("C1","Revenue growth is 12."),req("C2","Margin rate is 8.")],[
      ev("E1","Report states Revenue growth is 12."),
      ev("E2","Report states Margin rate is 8.")
    ])
    p["v3_input"]["task"]["audience_profile"]["constraints"]["max_items"]=1
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="GROUNDED_REALIZER_FAIL_CLOSED"
    assert out["detail"]["realizer_result"]["reason"]=="MAX_ITEMS_INFEASIBLE__NO_CONTENT_DROPPED"

def test_sectioned_markdown_fails_until_item_sections_are_explicit():
    p=payload([req("C1","Revenue growth is 12.")],[ev("E1","Report states Revenue growth is 12.")])
    p["v3_input"]["task"]["audience_profile"]["constraints"]["output_format"]="SECTIONED_MARKDOWN"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="SECTIONED_MARKDOWN_OUTSIDE_V1_WITHOUT_EXPLICIT_ITEM_SECTIONS"

def test_authority_boundaries_zero():
    out=evaluate(payload([req("C1","Revenue growth is 12.")],[ev("E1","Report states Revenue growth is 12.")]))
    assert out["pass"]
    assert out["p3_contract_cell_authorized"] is True
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
