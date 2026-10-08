from canonical.runtime.p3_real_context_v3_admission_v4 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints():
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":2,"max_chars":4000,"heading_level":2,"require_title":False}

def base(optional=True):
    claims=[
      {"claim_id":"A","text":"Revenue growth is 12.","required":True},
      {"claim_id":"B","text":"Margin rate is 8.","required":not optional},
      {"claim_id":"C","text":"Latency value is 5.","required":False},
    ]
    evidence=[
      {"evidence_id":"E1","text":"Report states Revenue growth is 12.","verified":True,"provenance":[{"source_id":"R","locator":"p1"}]},
      {"evidence_id":"E2","text":"Report states Margin rate is 8.","verified":True,"provenance":[{"source_id":"R","locator":"p2"}]},
      {"evidence_id":"E3","text":"Trace states Latency value is 5.","verified":True,"provenance":[{"source_id":"T","locator":"p1"}]},
    ]
    return {"schema":INPUT_SCHEMA,"task":{"claims":claims,"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}

def test_structural_path_still_wins():
    p={"context_id":"x","v3_input":base(optional=False)}
    p["v3_input"]["task"]["claims"].pop()
    p["v3_input"]["task"]["evidence"].pop()
    out=evaluate(p)
    assert out["pass"] is True
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["terminal_credit_delta"]==0

def test_weighted_path_selects_best_optional():
    p={"context_id":"x","v3_input":base(),"objective_weights":{"A":1,"B":10,"C":5}}
    out=evaluate(p)
    assert out["pass"] is True,out
    assert out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"
    assert out["selected_claim_ids"]==["A","B"]
    assert out["claim_order"]==["B","A"]
    assert out["objective_value"]==11
    assert out["terminal_credit_delta"]==0

def test_weights_are_causal():
    p={"context_id":"x","v3_input":base(),"objective_weights":{"A":1,"B":10,"C":5}}
    a=evaluate(p)
    p["objective_weights"]={"A":1,"B":2,"C":20}
    b=evaluate(p)
    assert a["route"]==b["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"
    assert a["selected_claim_ids"]!=b["selected_claim_ids"]
    assert b["selected_claim_ids"]==["A","C"]

def test_no_weights_falls_back_closed():
    p={"context_id":"x","v3_input":base()}
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["weighted_fast_path_reason"]=="OBJECTIVE_WEIGHTS_NOT_SUPPLIED"

def test_conflict_with_weights_falls_back():
    p={"context_id":"x","v3_input":base(),"objective_weights":{"A":1,"B":10,"C":5}}
    p["v3_input"]["task"]["evidence"].append({"evidence_id":"E4","text":"Other states Margin rate is 7.","verified":True,"provenance":[{"source_id":"O","locator":"p1"}]})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["weighted_fast_path_reason"]=="CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"

def test_caller_include_cannot_force_weighted_selection():
    p={"context_id":"x","v3_input":base(),"objective_weights":{"A":1,"B":10,"C":5}}
    p["v3_input"]["task"]["claims"][1]["include"]=True
    out=evaluate(p)
    assert out["pass"] is False
    assert out["weighted_fast_path_reason"]=="CALLER_INCLUDE_FORBIDDEN"

def test_forged_semantic_flags_still_do_not_authorize_fallback():
    p={"context_id":"x","v3_input":base()}
    ids=("REQUIRED_UNCERTAINTY_SET_COMPLETE","SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE","AUDIENCE_FORMAT_PROFILE_COMPLETE")
    p["semantic_certificates"]={i:{"pass":True,"predicate_id":i,"predicate_truth":"TRUE",
      "truthful_precommitment_observation":True,"policy_adequacy_authority":False,"terminal_authority":False} for i in ids}
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["v3_admission_authorized"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_fast_paths_never_mint_db_or_terminal():
    p={"context_id":"x","v3_input":base(),"objective_weights":{"A":1,"B":10,"C":5}}
    out=evaluate(p)
    assert out["pass"] is True
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
