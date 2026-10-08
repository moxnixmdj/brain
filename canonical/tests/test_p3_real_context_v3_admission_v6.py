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
    assert out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"
    assert out["rendered_text"]=="- Revenue growth is at least 10. [src:REPORT@p1]"
    assert out["v3_admission_authorized"] is False
    assert out["p3_contract_cell_authorized"] is True
    assert out["top_law_eligible"] is False

def test_source_defined_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","The release date is June.")],[
      ev("E","Launch date means release date. Report states that The launch date is June.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"

def test_exact_attestation_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","The product launched in June.")],[
      ev("E","Report states that The product launched in June.","REPORT")
    ])}
    out=evaluate(p)
    assert out["pass"] and out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"

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


def test_categorical_required_realization_fast_path():
    p={"context_id":"x","v3_input":base([req("A","Tweety is a member of Animal.")],[
      ev("E1","Report states that Tweety is a member of Canary.","REPORT"),
      ev("E2","Taxonomy states that Canary is a subclass of Bird.","TAX"),
      ev("E3","Taxonomy states that Bird is a subclass of Animal.","TAX"),
    ])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"
    assert out["p3_contract_cell_authorized"] is True
    assert out["top_law_eligible"] is False
    assert out["terminal_authority"] is False


def test_common_contract_guard_blocks_field_projection_on_every_route():
    from copy import deepcopy
    # Numeric semantic route bypassed the legacy V3 fact grammar in V6.
    source={"context_id":"x","v3_input":base([
        req("A","Revenue growth is at least 10.")
    ],[ev("E","Report states Revenue growth is 12.")])}
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
        assert out["terminal_credit_delta"]==0


def test_unmodeled_top_level_requirement_fails_closed():
    source={"context_id":"x","v3_input":base([
        req("A","Revenue growth is at least 10.")
    ],[ev("E","Report states Revenue growth is 12.")])}
    source["external_semantic_requirement"]="Translate output to German"
    out=evaluate(source)
    assert out["pass"] is False,out
    assert out["reason"]=="UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"
    assert out["p3_contract_cell_authorized"] is False
    assert out["terminal_authority"] is False


def test_explicit_weights_override_structural_common_policy():
    p={"context_id":"x","v3_input":base([
        req("A","Revenue growth is 12."),
        req("B","Margin rate is 8."),
    ],[
        ev("E1","Report states Revenue growth is 12."),
        ev("E2","Report states Margin rate is 8."),
    ]),"objective_weights":{"A":1,"B":100}}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1",out
    assert out["selected_claim_ids"]==["A","B"]
    assert out["claim_order"]==["B","A"],out
    assert out["terminal_credit_delta"]==0


def test_invalid_explicit_objective_weights_never_fall_through():
    p={"context_id":"x","v3_input":base([
        req("A","Revenue growth is 12."),
        req("B","Margin rate is 8."),
    ],[
        ev("E1","Report states Revenue growth is 12."),
        ev("E2","Report states Margin rate is 8."),
    ])}
    for bad in (None, [], {"A":1}, {"A":1,"B":"not an integer"}):
        out=evaluate({**p,"objective_weights":bad})
        assert not out["pass"],(bad,out)
        assert out["reason"] in {"OBJECTIVE_WEIGHTS_INVALID","OBJECTIVE_WEIGHTS_UNSATISFIED"}
        assert out["v3_admission_authorized"] is False
        assert out["p3_contract_cell_authorized"] is False
        assert out["terminal_authority"] is False
