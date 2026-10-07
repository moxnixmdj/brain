import json
from unittest.mock import patch

from canonical.runtime.p2_explicit_contract_membership_v1 import P2
from canonical.runtime.professional_positive_adequacy_escape_router_v1 import route

def structural(parsed=True):
    return {
        "sources":[{"source_id":"task","required":True,"parsed":parsed,"content_sha256":"abc","parser_receipt":"receipt","authority_rank":0}],
        "required_dimension_ids":["deliverable"],
        "dimensions":[{"dimension_id":"deliverable","source_ids":["task"],"coverage_receipt":"coverage"}],
        "required_convention_ids":[],
        "conventions":[],
    }

def p2_source():
    return json.dumps({"contract":P2,"task":{"audience":"executive","required_topics":["T1"],"evidence":[{"fact_id":"F1"}],"edit_candidates":[{"id":"E1","analysis_kind":"quantify","topic":"T1","claims":["F1"],"intended_audience":"executive","cost":1}],"edit_budget":1}})

def test_structural_omission_blocks_before_semantic_routes():
    out=route("Prepare the workbook.",source_id="task",structural_manifest=structural(parsed=False))
    assert out["pass"] is False
    assert out["status"]=="BLOCKED__DECLARED_STRUCTURAL_OMISSION"

def test_exact_p2_membership_short_circuits_positive_adequacy():
    out=route(p2_source(),source_id="task",structural_manifest=structural())
    assert out["pass"] is True
    assert out["selected_route"]=="EXACT_P2_MEMBERSHIP"
    assert out["full_semantic_manifest_required_for_selected_cell"] is False

def test_free_form_source_requests_positive_adequacy_not_full_semantic_manifest():
    out=route("Prepare an executive workbook using all current pricing sources.",source_id="task",structural_manifest=structural())
    assert out["pass"] is False
    assert out["status"]=="UNRESOLVED__TRY_POSITIVE_ADEQUACY_BEFORE_FULL_SEMANTIC_COMPLETION"
    assert out["p2_first_residual_class"]=="RAW_TO_TYPED_P2_SEMANTIC_COMPILATION"
    assert out["full_semantic_manifest_required_for_selected_cell"] is False

def test_positive_adequacy_can_close_selected_cell_without_exact_p2_membership():
    text="Prepare an executive workbook using all current pricing sources."
    payload={"source_text":text,"source_id":"task"}
    with patch("canonical.runtime.professional_positive_adequacy_escape_router_v1.evaluate_positive_adequacy",return_value={"pass":True,"status":"PASS__SOURCE_PROVED_POSITIVE_ADEQUACY_CELL_ADMISSIBLE_TO_D_B","db_admission_authorized":True}):
        out=route(text,source_id="task",structural_manifest=structural(),positive_adequacy_payload=payload)
    assert out["pass"] is True
    assert out["selected_route"]=="SOURCE_POSITIVE_ADEQUACY"
    assert out["full_semantic_manifest_required_for_selected_cell"] is False
    assert out["global_professional_scope_closed"] is False
    assert out["terminal_credit_delta"]==0

def test_positive_adequacy_failure_preserves_smallest_residual():
    text="Prepare an executive workbook using all current pricing sources."
    payload={"source_text":text,"source_id":"task"}
    with patch("canonical.runtime.professional_positive_adequacy_escape_router_v1.evaluate_positive_adequacy",return_value={"pass":False,"status":"UNRESOLVED__POSITIVE_ADEQUACY_NOT_ENTAILED","db_admission_authorized":False}):
        out=route(text,source_id="task",structural_manifest=structural(),positive_adequacy_payload=payload)
    assert out["pass"] is False
    assert out["status"]=="UNRESOLVED__P2_AND_POSITIVE_ADEQUACY_BOTH_OPEN"
    assert out["p2_first_residual_class"]=="RAW_TO_TYPED_P2_SEMANTIC_COMPILATION"
    assert out["positive_adequacy_status"]=="UNRESOLVED__POSITIVE_ADEQUACY_NOT_ENTAILED"

def test_positive_adequacy_must_bind_exact_source():
    text="Prepare an executive workbook."
    out=route(text,source_id="task",structural_manifest=structural(),positive_adequacy_payload={"source_text":"different","source_id":"task"})
    assert out["pass"] is False
    assert out["reason"]=="POSITIVE_ADEQUACY_SOURCE_TEXT_MISMATCH"

def test_router_never_grants_terminal_credit():
    out=route("Prepare an executive workbook.",source_id="task",structural_manifest=structural())
    assert out["terminal_credit_delta"]==0
    assert out["terminal_authority"] is False
