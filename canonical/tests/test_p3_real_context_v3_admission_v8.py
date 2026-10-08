from canonical.runtime.p3_real_context_v3_admission_v8 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items=2,max_chars=2000):
    return {
      "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
      "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
      "max_items":max_items,"max_chars":max_chars,"heading_level":2,"require_title":False,
    }

def presentation_case():
    return {
      "context_id":"binary-comparison",
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "v3_input":{
        "schema":INPUT_SCHEMA,
        "task":{
          "claims":[
            {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
            {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
          ],
          "evidence":[
            {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,
             "provenance":[{"source_id":"S1","locator":"p1"}]},
            {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,
             "provenance":[{"source_id":"S2","locator":"p2"}]},
          ],
          "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
          "required_uncertainty_units":[],
        },
      },
    }

def membership_case():
    return {
      "context_id":"membership",
      "v3_input":{
        "schema":INPUT_SCHEMA,
        "task":{
          "claims":[{"claim_id":"A","text":"Asset category is in {equity, bond}.","required":True}],
          "evidence":[{"evidence_id":"E","text":"Report states Asset category is equity.","verified":True,
                       "provenance":[{"source_id":"E","locator":"p1"}]}],
          "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
          "required_uncertainty_units":[],
        },
      },
    }

def test_binary_presentation_fallback_integrated():
    out=evaluate(presentation_case())
    assert out["pass"] is True,out
    assert out["route"]=="BINARY_OBJECTIVE_ROLE_PRESENTATION_COMMON_POLICY_CELL_V1"
    assert out["selected_claim_ids"]==["left","right"]
    assert out["claim_order"]==["left","right"]
    assert out["organization_policy_complete"] is True
    assert out["v7_preserved_positive_route"] is False
    assert out["p3_contract_cell_authorized"] is True
    assert out["terminal_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_v7_positive_route_preserved_first():
    out=evaluate(membership_case())
    assert out["pass"] is True,out
    assert out["v7_preserved_positive_route"] is True
    assert out["route"]!="BINARY_OBJECTIVE_ROLE_PRESENTATION_COMMON_POLICY_CELL_V1"

def test_missing_objective_does_not_invent_presentation_pass():
    p=presentation_case(); p.pop("objective")
    out=evaluate(p)
    assert out["pass"] is False
    assert out["binary_presentation_fast_path_pass"] is False

def test_nonempty_uncertainty_does_not_enter_presentation_cell():
    p=presentation_case()
    p["v3_input"]["task"]["required_uncertainty_units"]=[
      {"uncertainty_id":"u","text":"Calibration unknown","provenance":[{"source_id":"S1"}]}
    ]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["binary_presentation_fast_path_pass"] is False

def test_authority_boundary_on_presentation_pass():
    out=evaluate(presentation_case())
    assert out["pass"] is True
    for key in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
        assert out[key] is False
    assert out["terminal_credit_delta"]==0
