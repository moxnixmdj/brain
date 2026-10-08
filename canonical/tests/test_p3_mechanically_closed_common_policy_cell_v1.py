from canonical.runtime.p3_mechanically_closed_common_policy_cell_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints():
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,"max_items":8,"max_chars":4000,"heading_level":2,"require_title":False}

def payload():
    return {"v3_input":{"schema":INPUT_SCHEMA,"task":{
      "claims":[{"claim_id":"A","text":"Revenue growth is 12.","required":True},{"claim_id":"B","text":"Margin rate is 8.","required":True}],
      "evidence":[{"evidence_id":"E1","text":"Report states Revenue growth is 12.","verified":True,"provenance":[{"source_id":"REPORT","locator":"p1"}]},{"evidence_id":"E2","text":"Report states Margin rate is 8.","verified":True,"provenance":[{"source_id":"REPORT","locator":"p2"}]}],
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},"required_uncertainty_units":[]}}}

def test_positive_cell():
    out=evaluate(payload())
    assert out["pass"] is True
    assert out["v3_admission_authorized"] is True
    assert out["terminal_credit_delta"] == 0

def test_optional_claim_rejected():
    p=payload(); p["v3_input"]["task"]["claims"][1]["required"]=False; p["v3_input"]["task"]["claims"][1]["include"]=True
    assert evaluate(p)["reason"]=="OPTIONAL_CLAIM_REQUIRES_RELEVANCE_JUDGMENT"

def test_reordering_rejected():
    p=payload(); p["v3_input"]["task"]["claim_order"]=["B","A"]
    assert evaluate(p)["reason"]=="EXPLICIT_SEMANTIC_REORDERING_OUTSIDE_ZERO_RESIDUAL_CELL"

def test_uncertainty_rejected():
    p=payload(); p["v3_input"]["task"]["required_uncertainty_units"]=[{"uncertainty_id":"U","text":"Uncertainty remains.","provenance":[{"source_id":"R","locator":"p3"}]}]
    assert evaluate(p)["reason"]=="NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_ZERO_RESIDUAL_CELL"

def test_conflict_rejected():
    p=payload(); p["v3_input"]["task"]["evidence"].append({"evidence_id":"E3","text":"Other states Revenue growth is 11.","verified":True,"provenance":[{"source_id":"OTHER","locator":"p1"}]})
    assert evaluate(p)["reason"]=="CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"

def test_missing_format_field_rejected():
    p=payload(); del p["v3_input"]["task"]["audience_profile"]["constraints"]["max_chars"]
    assert evaluate(p)["reason"]=="AUDIENCE_FORMAT_CONTRACT_NOT_EXPLICITLY_COMPLETE"

def test_unmodeled_audience_field_rejected():
    p=payload(); p["v3_input"]["task"]["audience_profile"]["persona"]="executive"
    assert evaluate(p)["reason"]=="UNMODELED_AUDIENCE_PROFILE_FIELDS"
