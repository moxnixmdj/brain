from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as eval_required_v3
from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as eval_v6
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items=3):
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":max_items,"max_chars":5000,"heading_level":2,"require_title":False}

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def req(i,text):
    return {"claim_id":i,"text":text,"required":True}

def base(claims,evidence):
    return {"schema":INPUT_SCHEMA,"task":{"claims":claims,"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}

def test_required_v3_membership_realized():
    out=eval_required_v3({"v3_input":base([req("A","Asset category is in {equity, bond}.")],[
      ev("E","Report states Asset category is equity.","REPORT")
    ])})
    assert out["pass"],out
    assert out["rendered_text"]=="- Asset category is in {equity, bond}. [src:REPORT@p1]"
    receipt=out["support_receipts"][0]["receipt"]
    assert receipt["relation_audit"][0]["grammar"]=="SET_MEMBERSHIP_V1"

def test_required_v3_nonmembership_realized():
    out=eval_required_v3({"v3_input":base([req("A","Asset category is not in {cash, commodity}.")],[
      ev("E","Report states Asset category is equity.","REPORT")
    ])})
    assert out["pass"],out

def test_required_v3_membership_conflict_fails():
    out=eval_required_v3({"v3_input":base([req("A","Asset category is in {equity, bond}.")],[
      ev("E","Report states Asset category is cash.")
    ])})
    assert not out["pass"] and out["reason"]=="REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED"

def test_v6_membership_new_fast_path():
    out=eval_v6({"context_id":"x","v3_input":base([req("A","Asset category is in {equity, bond}.")],[
      ev("E","Report states Asset category is bond.","REPORT")
    ])})
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"
    assert out["v5_preserved_positive_route"] is False
    assert out["p3_contract_cell_authorized"] is True
    assert out["terminal_authority"] is False

def test_v6_preserves_existing_numeric_v5_route():
    out=eval_v6({"context_id":"x","v3_input":base([req("A","Revenue growth is at least 10.")],[
      ev("E","Report states Revenue growth is 12.","REPORT")
    ])})
    assert out["pass"],out
    assert out["v5_preserved_positive_route"] is True
    assert out["route"]=="REQUIRED_SUPPORT_V4_REALIZATION_CELL_V2"

def test_v6_preserves_structural_route():
    out=eval_v6({"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[
      ev("E","Report states Revenue growth is 12.")
    ])})
    assert out["pass"],out
    assert out["v5_preserved_positive_route"] is True
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"

def test_v6_uncheckable_membership_stays_closed():
    out=eval_v6({"context_id":"x","v3_input":base([req("A","Asset category is in {equity, bond}.")],[
      ev("E","The asset appears defensive.")
    ])})
    assert not out["pass"]
    assert out["terminal_authority"] is False

def test_v6_authority_zero():
    out=eval_v6({"context_id":"x","v3_input":base([req("A","Asset category is in {equity, bond}.")],[
      ev("E","Report states Asset category is equity.")
    ])})
    assert out["pass"]
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
