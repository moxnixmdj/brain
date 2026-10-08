import copy

from canonical.runtime.p3_bound_objective_role_top_law_scope_authenticator_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA


def base():
    return {
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "v2_input":{
        "schema":INPUT_SCHEMA,
        "task":{
          "claims":[
            {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
            {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
          ],
          "evidence":[
            {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,
             "provenance":[{"source_id":"S1","locator":"p1"}]},
            {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,
             "provenance":[{"source_id":"S2","locator":"p2"}]},
          ],
          "audience_profile":{
            "profile_id":"EXPLICIT",
            "constraints":{
              "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
              "required_sections":[],"allowed_sections":None,"max_items":2,"max_chars":2000,
              "heading_level":2,"require_title":False,
            },
          },
        },
      },
    }


def test_exact_closed_cell_authenticates_scope_membership():
    out=evaluate(base())
    assert out["pass"],out
    assert out["explicit_payload_surface_exhaustively_consumed"] is True
    assert out["real_context_top_law_scope_membership_authenticated"] is True
    assert out["no_unmodeled_payload_presentation_channels"] is True
    assert out["presentation_policy_constructed"] is True


def test_trailing_objective_instruction_is_rejected():
    p=base()
    p["objective"] += " Emphasize the left material."
    out=evaluate(p)
    assert not out["pass"]
    assert out["reason"]=="OBJECTIVE_NOT_EXACT_WHOLE_BINARY_NUMERIC_COMPARISON"


def test_extra_task_field_is_rejected():
    p=base()
    p["v2_input"]["task"]["presentation_hint"]="Prefer the left claim"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="TASK_FIELDS_NOT_CLOSED"


def test_extra_profile_field_is_rejected():
    p=base()
    p["v2_input"]["task"]["audience_profile"]["tone"]="executive"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="AUDIENCE_PROFILE_FIELDS_NOT_CLOSED"


def test_claim_section_is_rejected_as_side_channel():
    p=base()
    p["v2_input"]["task"]["claims"][0]["section"]="Most important"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="CLAIM_FIELDS_NOT_CLOSED"


def test_caller_include_is_rejected_as_side_channel():
    p=base()
    p["v2_input"]["task"]["claims"][0]["include"]=True
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="CLAIM_FIELDS_NOT_CLOSED"


def test_caller_order_is_rejected_as_side_channel():
    p=base()
    p["v2_input"]["task"]["claim_order"]=["right","left"]
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="TASK_FIELDS_NOT_CLOSED"


def test_nonnumeric_claim_surface_is_rejected():
    p=base()
    p["v2_input"]["task"]["claims"][0]["text"]="AISI type 304 stainless steel should be emphasized."
    p["v2_input"]["task"]["evidence"][0]["text"]=p["v2_input"]["task"]["claims"][0]["text"]
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="CLAIM_NOT_EXACT_NUMERIC_FACT"


def test_objective_operands_must_equal_claim_subjects():
    p=base()
    p["v2_input"]["task"]["claims"][1]["text"]="Thermal conductivity of a different alloy is 167 W/mK."
    p["v2_input"]["task"]["evidence"][1]["text"]=p["v2_input"]["task"]["claims"][1]["text"]
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="OBJECTIVE_OPERANDS_NOT_EXACT_CLAIM_SUBJECTS"


def test_extra_evidence_is_rejected():
    p=base()
    p["v2_input"]["task"]["evidence"].append({
      "evidence_id":"E3","text":"Density of AISI type 304 stainless steel is 8 g/cm3.","verified":True,
      "provenance":[{"source_id":"S3","locator":"p3"}],
    })
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="EXACTLY_TWO_EVIDENCE_ROWS_REQUIRED"


def test_unverified_evidence_rejected():
    p=base()
    p["v2_input"]["task"]["evidence"][0]["verified"]=False
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="UNVERIFIED_EVIDENCE_UNIT"


def test_reversed_objective_still_authenticates_and_reverses_policy_order():
    p=base()
    p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
    out=evaluate(p)
    assert out["pass"],out
    assert out["presentation_compiler_receipt"]["objective_role_order"]==["right","left"]


def test_unknown_constraint_field_is_rejected():
    p=base()
    p["v2_input"]["task"]["audience_profile"]["constraints"]["emphasis"]="left"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="AUDIENCE_CONSTRAINT_FIELDS_NOT_CLOSED"


def test_title_is_rejected_in_narrow_v1():
    p=base()
    p["v2_input"]["task"]["audience_profile"]["title"]="Comparison"
    out=evaluate(p)
    assert not out["pass"] and out["reason"]=="AUDIENCE_PROFILE_FIELDS_NOT_CLOSED"


def test_authority_boundaries_remain_zero():
    out=evaluate(base())
    assert out["pass"],out
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
