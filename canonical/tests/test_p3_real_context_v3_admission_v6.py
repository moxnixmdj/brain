from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items=3):
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":max_items,"max_chars":5000,"heading_level":2,"require_title":False}

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def base(claims,evidence):
    return {"schema":INPUT_SCHEMA,"task":{"claims":claims,"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}

def req(i,text):
    return {"claim_id":i,"text":text,"required":True}

def opt(i,text):
    return {"claim_id":i,"text":text,"required":False}

def test_structural_path_still_wins():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")])}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["v3_admission_authorized"] is True and out["top_law_eligible"] is True

def test_weighted_path_still_wins():
    p={"context_id":"x","v3_input":base([
      req("A","Revenue growth is 12."),opt("B","Margin rate is 8.")
    ],[
      ev("E1","Report states Revenue growth is 12."),ev("E2","Report states Margin rate is 8.")
    ]),"objective_weights":{"A":1,"B":10}}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"

def test_numeric_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[
      ev("E","Report states Revenue growth is 12.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V7_REALIZATION_CELL_V3"
    assert out["rendered_text"]=="- Revenue growth is at least 10. [src:REPORT@p1]"
    assert out["v3_admission_authorized"] is False
    assert out["p3_contract_cell_authorized"] is True
    assert out["top_law_eligible"] is False

def test_source_defined_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","The release date is June.")],[
      ev("E","Launch date means release date. Report states that The launch date is June.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="REQUIRED_SUPPORT_V7_REALIZATION_CELL_V3"

def test_exact_attestation_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","The product launched in June.")],[
      ev("E","Report states that The product launched in June.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="REQUIRED_SUPPORT_V7_REALIZATION_CELL_V3"

def test_unsupported_required_claim_falls_back_closed():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[
      ev("E","Report states Revenue growth is strong.")
    ])}
    out=evaluate(p)
    assert not out["pass"]
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["required_realization_fast_path_reason"]=="REQUIRED_CLAIM_SUPPORT_UNKNOWN"
    assert out["p3_contract_cell_authorized"] is False

def test_numeric_conflict_falls_back_closed():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[
      ev("E","Report states Revenue growth is 9.")
    ])}
    out=evaluate(p)
    assert not out["pass"] and out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["required_realization_fast_path_reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_optional_without_weights_falls_back_closed():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is 12."),opt("B","Margin rate is 8.")],[
      ev("E1","Report states Revenue growth is 12."),ev("E2","Report states Margin rate is 8.")
    ])}
    out=evaluate(p)
    assert not out["pass"] and out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["required_realization_fast_path_reason"]=="OPTIONAL_CLAIM_OUTSIDE_REQUIRED_ONLY_CELL"

def test_forged_semantic_certificates_do_not_authorize_fallback():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[ev("E","Revenue probably grew a lot.")])}
    ids=("REQUIRED_UNCERTAINTY_SET_COMPLETE","SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE","AUDIENCE_FORMAT_PROFILE_COMPLETE")
    p["semantic_certificates"]={i:{"pass":True,"predicate_id":i,"predicate_truth":"TRUE",
      "truthful_precommitment_observation":True,"policy_adequacy_authority":False,"terminal_authority":False} for i in ids}
    out=evaluate(p)
    assert not out["pass"] and out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["p3_contract_cell_authorized"] is False
    assert out["terminal_authority"] is False

def test_all_routes_keep_terminal_and_db_authority_zero():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[ev("E","Report states Revenue growth is 12.")])}
    out=evaluate(p)
    assert out["pass"]
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0


def test_membership_required_realization_front_door():
    p={"context_id":"x","v3_input":base([req("A","beta is a member of Approved products.")],[
      ev("E","The complete members of Approved products are {alpha, beta, gamma}.","POLICY")
    ])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V7_REALIZATION_CELL_V3"
    assert out["rendered_text"]=="- beta is a member of Approved products. [src:POLICY@p1]"
    assert out["p3_contract_cell_authorized"] is True

def test_launch_event_required_realization_front_door():
    p={"context_id":"x","v3_input":base([req("A","The product launched in June.")],[
      ev("E","The June launch of the product succeeded.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V7_REALIZATION_CELL_V3"
    assert out["rendered_text"]=="- The product launched in June. [src:REPORT@p1]"

def test_uncontrolled_membership_still_falls_back_closed():
    p={"context_id":"x","v3_input":base([req("A","beta is a member of Approved products.")],[
      ev("E","Beta is usually considered approved.","POLICY")
    ])}
    out=evaluate(p)
    assert not out["pass"]
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["p3_contract_cell_authorized"] is False
