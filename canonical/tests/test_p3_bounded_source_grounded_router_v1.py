from __future__ import annotations

from canonical.runtime.p3_bounded_source_grounded_router_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA


def constraints(max_items=8):
    return {
        "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
        "max_items":max_items,"max_chars":4000,"heading_level":2,"require_title":False,
    }


def task_record(paths=("sources/a.txt","sources/b.txt")):
    return {
        "task_id":"P3-SOURCE-1",
        "task_md_path":paths[0],
        "scenario_overview_path":paths[1],
        "shared_files":[],
        "week_files":[],
    }


def source_package():
    return {
        "sources/a.txt":"Report states Revenue growth is 12.",
        "sources/b.txt":"Report states Margin rate is 8.",
    }


def closed_payload():
    sources=source_package()
    return {
        "context_id":"P3-SOURCE-1",
        "task_record":task_record(),
        "materialized_sources":sources,
        "v3_input":{"schema":INPUT_SCHEMA,"task":{
            "claims":[
                {"claim_id":"A","text":"Revenue growth is 12.","required":True},
                {"claim_id":"B","text":"Margin rate is 8.","required":True},
            ],
            "evidence":[
                {"evidence_id":"E1","text":sources["sources/a.txt"],"verified":False,
                 "provenance":[{"source_id":"sources/a.txt"}]},
                {"evidence_id":"E2","text":sources["sources/b.txt"],
                 "provenance":[{"source_id":"sources/b.txt"}]},
            ],
            "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
            "required_uncertainty_units":[],
        }},
    }


def test_closed_cell_mints_evidence_verification_from_exact_declared_source_bytes():
    out=evaluate(closed_payload())
    assert out["pass"] is True,out
    assert out["route"]=="GROUNDED_CLOSED_COMMON_POLICY_CELL"
    assert out["bounded_declared_source_set_verified"] is True
    assert out["evidence_exact_source_grounding_verified"] is True
    assert out["external_source_authority_verified"] is False
    assert out["v3_admission_authorized"] is True
    assert out["terminal_authority"] is False


def test_caller_verified_bit_has_no_authority():
    p=closed_payload()
    p["v3_input"]["task"]["evidence"][0]["verified"]=False
    p["v3_input"]["task"]["evidence"][1]["verified"]=False
    out=evaluate(p)
    assert out["pass"] is True
    for row in out["p3_receipt"]["route_receipt"]["v3_result"]["render_trace"]:
        assert row["provenance"]


def test_missing_declared_source_blocks():
    p=closed_payload(); del p["materialized_sources"]["sources/b.txt"]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="MATERIALIZED_SOURCE_SET_MISMATCH"
    assert out["detail"]["missing_sources"]==["sources/b.txt"]


def test_undeclared_extra_source_blocks():
    p=closed_payload(); p["materialized_sources"]["sources/x.txt"]="X value is 1."
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="MATERIALIZED_SOURCE_SET_MISMATCH"
    assert out["detail"]["undeclared_sources"]==["sources/x.txt"]


def test_evidence_must_equal_exact_source_bytes():
    p=closed_payload(); p["v3_input"]["task"]["evidence"][0]["text"]="Report states Revenue growth is 13."
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="EVIDENCE_TEXT_NOT_EXACT_SOURCE_BYTES"


def test_hidden_second_fact_in_source_blocks_one_unit_cell():
    p=closed_payload()
    p["materialized_sources"]["sources/a.txt"] += "\nOther states Revenue growth is 11."
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="DECLARED_SOURCE_MUST_BE_ONE_NORMALIZED_FACT_UNIT"


def test_each_declared_source_must_be_evidenced_once():
    p=closed_payload()
    p["v3_input"]["task"]["evidence"][1]["provenance"]=[{"source_id":"sources/a.txt"}]
    p["v3_input"]["task"]["evidence"][1]["text"]=p["materialized_sources"]["sources/a.txt"]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="DECLARED_SOURCE_EVIDENCED_MORE_THAN_ONCE"


def test_conflicting_declared_sources_do_not_pass_closed_cell():
    p=closed_payload()
    p["materialized_sources"]["sources/b.txt"]="Other states Revenue growth is 11."
    p["v3_input"]["task"]["evidence"][1]["text"]=p["materialized_sources"]["sources/b.txt"]
    p["v3_input"]["task"]["claims"]=[{"claim_id":"A","text":"Revenue growth is 12.","required":True}]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="NO_VERIFIED_P3_POSITIVE_CELL_FOR_GROUNDED_CONTEXT"


def weighted_payload():
    p=closed_payload()
    p["v3_input"]["task"]["claims"]=[
        {"claim_id":"A","text":"Revenue growth is 12.","required":True},
        {"claim_id":"B","text":"Margin rate is 8.","required":False},
    ]
    p["v3_input"]["task"]["audience_profile"]["constraints"]["max_items"]=1
    p["objective_weights"]={"A":10,"B":3}
    return p


def test_explicit_weight_cell_is_reachable_after_same_source_grounding():
    out=evaluate(weighted_payload())
    assert out["pass"] is True,out
    assert out["route"]=="GROUNDED_EXPLICIT_WEIGHT_SALIENCE_CELL"
    assert out["selected_claim_ids"]==["A"]
    assert out["claim_order"]==["A"]
    assert out["evidence_exact_source_grounding_verified"] is True
    assert out["terminal_credit_delta"]==0


def test_optional_context_without_explicit_weights_fails_closed():
    p=weighted_payload(); del p["objective_weights"]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="NO_VERIFIED_P3_POSITIVE_CELL_FOR_GROUNDED_CONTEXT"
    assert out["detail"]["weighted_route_reason"]=="OBJECTIVE_WEIGHTS_NOT_SUPPLIED"
    assert out["bounded_declared_source_set_verified"] is True


def test_external_authority_never_inferred_from_declared_manifest():
    out=evaluate(closed_payload())
    assert out["pass"] is True
    assert out["external_source_authority_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
