from __future__ import annotations

from canonical.runtime.p3_real_context_v3_admission_v3 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA


def constraints():
    return {
        "output_format":"BULLETS",
        "citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED",
        "required_sections":[],
        "allowed_sections":None,
        "max_items":8,
        "max_chars":4000,
        "heading_level":2,
        "require_title":False,
    }


def base_v3():
    return {
        "schema":INPUT_SCHEMA,
        "task":{
            "claims":[
                {"claim_id":"A","text":"Revenue growth is 12.","required":True},
                {"claim_id":"B","text":"Margin rate is 8.","required":True},
            ],
            "evidence":[
                {"evidence_id":"E1","text":"Report states Revenue growth is 12.","verified":True,
                 "provenance":[{"source_id":"REPORT","locator":"p1"}]},
                {"evidence_id":"E2","text":"Report states Margin rate is 8.","verified":True,
                 "provenance":[{"source_id":"REPORT","locator":"p2"}]},
            ],
            "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
            "required_uncertainty_units":[],
        },
    }


def payload():
    return {"context_id":"P3-FAST-1","v3_input":base_v3()}


def fake_cert(predicate):
    return {
        "pass":True,
        "predicate_id":predicate,
        "predicate_truth":"TRUE",
        "truthful_precommitment_observation":True,
        "policy_adequacy_authority":False,
        "terminal_authority":False,
    }


def test_closed_cell_passes_without_semantic_certificates():
    out=evaluate(payload())
    assert out["pass"] is True,out
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["semantic_certificates_required"] is False
    assert out["v3_admission_authorized"] is True
    assert out["top_law_eligible"] is True
    assert out["source_authorization_verified"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0


def test_forged_semantic_certificates_are_irrelevant_on_closed_path():
    p=payload()
    p["semantic_certificates"]={
        x:fake_cert(x) for x in (
            "REQUIRED_UNCERTAINTY_SET_COMPLETE",
            "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE",
            "AUDIENCE_FORMAT_PROFILE_COMPLETE",
        )
    }
    out=evaluate(p)
    assert out["pass"] is True
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["semantic_certificates_required"] is False


def test_optional_claim_exits_fast_path_and_fails_closed_without_certificates():
    p=payload()
    p["v3_input"]["task"]["claims"][1]["required"]=False
    p["v3_input"]["task"]["claims"][1]["include"]=True
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["mechanically_closed_fast_path_reason"]=="OPTIONAL_CLAIM_REQUIRES_RELEVANCE_JUDGMENT"
    assert out["reason"]=="SEMANTIC_CERTIFICATES_REQUIRED"


def test_uncertainty_exits_fast_path():
    p=payload()
    p["v3_input"]["task"]["required_uncertainty_units"]=[
        {"uncertainty_id":"U","text":"Uncertainty remains.",
         "provenance":[{"source_id":"R","locator":"p3"}]}
    ]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["mechanically_closed_fast_path_reason"]=="NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_ZERO_RESIDUAL_CELL"


def test_reordering_exits_fast_path():
    p=payload()
    p["v3_input"]["task"]["claim_order"]=["B","A"]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["mechanically_closed_fast_path_reason"]=="EXPLICIT_SEMANTIC_REORDERING_OUTSIDE_ZERO_RESIDUAL_CELL"


def test_unmodeled_audience_semantics_exit_fast_path():
    p=payload()
    p["v3_input"]["task"]["audience_profile"]["persona"]="executive"
    out=evaluate(p)
    assert out["pass"] is False
    assert out["mechanically_closed_fast_path_reason"]=="UNMODELED_AUDIENCE_PROFILE_FIELDS"


def test_fallback_does_not_promote_synthetic_true_certificates():
    p=payload()
    p["v3_input"]["task"]["claims"][1]["required"]=False
    p["v3_input"]["task"]["claims"][1]["include"]=True
    p["semantic_certificates"]={
        x:fake_cert(x) for x in (
            "REQUIRED_UNCERTAINTY_SET_COMPLETE",
            "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE",
            "AUDIENCE_FORMAT_PROFILE_COMPLETE",
        )
    }
    out=evaluate(p)
    assert out["pass"] is False
    assert out["route"]=="V2_SEMANTIC_FALLBACK"
    assert out["status"]=="UNKNOWN__FINITE_P3_CONTEXT_SEMANTIC_BINDINGS_INCOMPLETE"
    assert len(out["unresolved_semantic_predicates"])==3
    assert out["v3_admission_authorized"] is False


def test_closed_receipt_cannot_mint_terminal_or_db_authority():
    out=evaluate(payload())
    receipt=out["closed_cell_receipt"]
    assert receipt["policy_adequacy_authority"] is False
    assert receipt["db_admission_authority"] is False
    assert receipt["u_subtraction_authority"] is False
    assert receipt["terminal_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
