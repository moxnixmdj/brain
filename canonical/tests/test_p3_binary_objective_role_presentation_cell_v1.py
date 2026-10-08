from canonical.runtime.p3_binary_objective_role_presentation_cell_v1 import evaluate

def constraints(max_items=2,max_chars=2000):
    return {
      "output_format":"BULLETS",
      "citation_mode":"INLINE_SOURCE_IDS",
      "style":"VERBATIM_GROUNDED",
      "required_sections":[],
      "allowed_sections":None,
      "max_items":max_items,
      "max_chars":max_chars,
      "heading_level":2,
      "require_title":False,
    }

def base():
    return {
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
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
      "required_uncertainty_units":[],
      "audience_constraints":constraints(),
    }

def test_positive_binary_role_presentation_cell():
    out=evaluate(base())
    assert out["pass"] is True,out
    assert out["status"]=="PASS__P3_BINARY_OBJECTIVE_ROLE_PRESENTATION_COMMON_POLICY_CELL"
    assert out["selected_claim_ids"]==["left","right"]
    assert out["claim_order"]==["left","right"]
    assert out["organization_policy_complete"] is True
    assert out["relevance_receipt"]["truthful_precommitment_relevance_bits"]=={"left":"RELEVANT","right":"RELEVANT"}
    assert out["rendered_text"]==(
      "- Thermal conductivity of AISI type 304 stainless steel is 16 W/mK. [src:S1@p1]\n"
      "- Thermal conductivity of 6061 aluminum is 167 W/mK. [src:S2@p2]"
    )
    assert out["realizer_audit"]["dropped_item_count"]==0
    assert out["realizer_audit"]["rewritten_material_item_count"]==0
    assert out["realizer_audit"]["new_material_claim_count"]==0
    assert out["p3_contract_cell_authorized"] is True
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_input_claim_order_cannot_override_objective_role_order():
    out=evaluate(base())
    assert out["claim_order"]==["left","right"]
    assert [x["item_id"] for x in out["render_trace"]]==["left","right"]

def test_required_claim_outside_exact_cell_fails():
    p=base()
    p["claims"].append({"claim_id":"r","text":"Use SI units.","required":True})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="REQUIRED_CLAIMS_OUTSIDE_BINARY_OPTIONAL_PRESENTATION_CELL"

def test_three_optionals_fail_closed():
    p=base()
    p["claims"].append({"claim_id":"decoy","text":"Ignition temperature of 6061 aluminum is 650 C.","required":False})
    p["evidence"].append({"evidence_id":"E3","text":"Ignition temperature of 6061 aluminum is 650 C.","verified":True,
                          "provenance":[{"source_id":"S3"}]})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="RELEVANCE_CERTIFICATE_FAILED"

def test_required_uncertainty_must_be_empty():
    p=base()
    p["required_uncertainty_units"]=[{"uncertainty_id":"u","text":"Unknown calibration","provenance":[{"source_id":"S1"}]}]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_CELL"

def test_max_items_infeasible_fails_without_dropping():
    p=base(); p["audience_constraints"]=constraints(max_items=1)
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="GROUNDED_REALIZER_FAIL_CLOSED"
    assert out["detail"]["realizer_result"]["reason"]=="MAX_ITEMS_INFEASIBLE__NO_CONTENT_DROPPED"

def test_max_chars_infeasible_fails_without_truncation():
    p=base(); p["audience_constraints"]=constraints(max_chars=20)
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="GROUNDED_REALIZER_FAIL_CLOSED"
    assert out["detail"]["realizer_result"]["reason"]=="MAX_CHARS_INFEASIBLE__NO_CONTENT_TRUNCATED"

def test_unknown_audience_constraint_fails_closed():
    p=base(); p["audience_constraints"]=constraints(); p["audience_constraints"]["magic"]=True
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="GROUNDED_REALIZER_FAIL_CLOSED"

def test_duplicate_role_evidence_fails_at_relevance_gate():
    p=base()
    p["evidence"].append({"evidence_id":"E3","text":"Thermal conductivity of AISI type 304 stainless steel is 17 W/mK.","verified":True,
                          "provenance":[{"source_id":"S3"}]})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="RELEVANCE_CERTIFICATE_FAILED"
