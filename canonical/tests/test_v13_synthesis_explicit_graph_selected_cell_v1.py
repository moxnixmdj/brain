from __future__ import annotations
import copy

from canonical.runtime.v13_synthesis_explicit_graph_selected_cell_v1 import (
    INPUT_SCHEMA,
    solve,
)


def base_case():
    return {
      "schema":INPUT_SCHEMA,
      "task":{
        "title":"Decision brief",
        "claims":[
          {"claim_id":"C1","required":True,"decision_relevant":True,"text":"Revenue increased to 12 million.","section":"Findings"},
          {"claim_id":"C2","required":True,"decision_relevant":True,"text":"Two verified sources disagree on unit cost.","section":"Risks"},
        ],
        "evidence":[
          {"evidence_id":"E1","provenance":["LEDGER"]},
          {"evidence_id":"E2","provenance":["LEDGER","FORECAST"]},
        ],
        "support_bindings":[
          {"claim_id":"C1","status":"SUPPORTED","evidence_ids":["E1"]},
          {"claim_id":"C2","status":"CONFLICTED","evidence_ids":["E2"]},
        ],
        "audience_semantics_compiled_into_constraints":True,
        "constraints":{
          "output_format":"SECTIONED_MARKDOWN",
          "citation_mode":"INLINE_SOURCE_IDS",
          "item_order":"INPUT",
          "required_sections":["Findings","Risks"],
          "allowed_sections":["Findings","Risks"],
          "max_items":2,
          "max_chars":2000,
          "heading_level":2,
          "require_title":True,
          "style":"VERBATIM_GROUNDED"
        }
      }
    }


def test_positive_cell_attains_all_five_component_ceilings():
    out=solve(base_case())
    assert out["cell_pass"] is True,out
    assert out["matched_quality"]==1.0
    assert out["unsupported_material_claims"]==0
    assert set(out["components"])=={
      "claim_to_source_fidelity",
      "uncertainty_and_disagreement_preservation",
      "audience_adaptation",
      "format_and_style_constraints",
      "compression_without_decision_relevant_loss",
    }
    assert all(v==1.0 for v in out["components"].values())
    assert out["render_audit"]["dropped_item_count"]==0
    assert out["render_audit"]["new_material_claim_count"]==0
    assert out["render_audit"]["all_items_provenance_bound"] is True
    assert "Conflict:" in out["rendered_text"]
    assert "[src:LEDGER;FORECAST]" in out["rendered_text"]


def test_optional_or_non_decision_relevant_claim_is_outside_cell():
    x=base_case()
    x["task"]["claims"][1]["required"]=False
    out=solve(x)
    assert out["cell_pass"] is False
    assert "CELL_REQUIRES_ALL_CLAIMS_REQUIRED_AND_DECISION_RELEVANT" in out["reason"]


def test_unsupported_required_claim_fails_closed():
    x=base_case()
    x["task"]["support_bindings"][0]={"claim_id":"C1","status":"UNSUPPORTED","evidence_ids":["E1"]}
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="CLAIM_GUARD_NOT_READY"


def test_audience_semantics_must_be_explicitly_precompiled():
    x=base_case()
    x["task"]["audience_semantics_compiled_into_constraints"]=False
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="AUDIENCE_SEMANTICS_MUST_BE_PRECOMPILED"


def test_infeasible_item_budget_fails_without_compression_credit():
    x=base_case()
    x["task"]["constraints"]["max_items"]=1
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="C2_REALIZATION_NOT_PASS"
    assert out["matched_quality"]==0.0


def test_unknown_tone_constraint_stays_outside_bounded_c2_cell():
    x=base_case()
    x["task"]["constraints"]["tone"]="persuasive"
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="C2_REALIZATION_NOT_PASS"


def test_missing_provenance_fails_closed():
    x=base_case()
    x["task"]["evidence"][0]["provenance"]=[]
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="CLAIM_GUARD_NOT_READY"


def test_conflict_cannot_be_silently_downgraded_to_supported():
    x=base_case()
    a=solve(x)
    x["task"]["support_bindings"][1]["status"]="SUPPORTED"
    b=solve(x)
    assert a["cell_pass"] is True and b["cell_pass"] is True
    assert "C2" in a["uncertainty_claim_ids"]
    assert "C2" not in b["uncertainty_claim_ids"]
    assert "Conflict:" in a["rendered_text"]
    assert "Conflict:" not in b["rendered_text"]


def test_bad_schema_fails_closed():
    x=base_case(); x["schema"]="WRONG"
    assert solve(x)["cell_pass"] is False
