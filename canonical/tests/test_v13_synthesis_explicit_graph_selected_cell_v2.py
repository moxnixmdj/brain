from canonical.runtime.v13_synthesis_explicit_graph_selected_cell_v1 import INPUT_SCHEMA, solve


def base_case():
    return {
        "schema": INPUT_SCHEMA,
        "task": {
            "title": "Decision brief",
            "claims": [
                {"claim_id":"C1","required":True,"decision_relevant":True,"text":"Revenue increased to 12 million.","section":"Findings"},
                {"claim_id":"C2","required":True,"decision_relevant":True,"text":"Two verified sources disagree on unit cost.","section":"Risks"},
            ],
            "evidence": [
                {"evidence_id":"E1","provenance":["LEDGER"]},
                {"evidence_id":"E2","provenance":["LEDGER","FORECAST"]},
            ],
            "support_bindings": [
                {"claim_id":"C1","status":"SUPPORTED","evidence_ids":["E1"]},
                {"claim_id":"C2","status":"CONFLICTED","evidence_ids":["E2"]},
            ],
            "audience_requirements": [
                {"constraint_key":"output_format","required_value":"SECTIONED_MARKDOWN"},
                {"constraint_key":"require_title","required_value":True},
            ],
            "constraints": {
                "output_format":"SECTIONED_MARKDOWN",
                "citation_mode":"INLINE_SOURCE_IDS",
                "item_order":"INPUT",
                "required_sections":["Findings","Risks"],
                "allowed_sections":["Findings","Risks"],
                "max_items":2,
                "max_chars":2000,
                "heading_level":2,
                "require_title":True,
                "style":"VERBATIM_GROUNDED",
            },
        },
    }


def test_positive_cell_hits_all_ceilings():
    out=solve(base_case())
    assert out["cell_pass"] is True, out
    assert out["matched_quality"]==1.0
    assert out["unsupported_material_claims"]==0
    assert all(v==1.0 for v in out["components"].values())
    assert out["render_audit"]["dropped_item_count"]==0
    assert out["render_audit"]["new_material_claim_count"]==0
    assert out["render_audit"]["all_items_provenance_bound"] is True
    assert "Conflict:" in out["rendered_text"]


def test_optional_claim_is_outside_cell():
    x=base_case(); x["task"]["claims"][1]["required"]=False
    assert solve(x)["cell_pass"] is False


def test_unsupported_required_claim_fails():
    x=base_case(); x["task"]["support_bindings"][0]={"claim_id":"C1","status":"UNSUPPORTED","evidence_ids":["E1"]}
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="CLAIM_GUARD_NOT_READY"


def test_audience_requirement_mismatch_fails():
    x=base_case(); x["task"]["audience_requirements"][0]["required_value"]="BULLETS"
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="AUDIENCE_REQUIREMENT_NOT_COMPILED_INTO_CONSTRAINT"


def test_missing_audience_requirements_fail():
    x=base_case(); del x["task"]["audience_requirements"]
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["reason"]=="EXPLICIT_AUDIENCE_REQUIREMENTS_REQUIRED"


def test_infeasible_budget_fails_without_compression_credit():
    x=base_case(); x["task"]["constraints"]["max_items"]=1
    out=solve(x)
    assert out["cell_pass"] is False
    assert out["matched_quality"]==0.0


def test_unknown_constraint_fails():
    x=base_case(); x["task"]["constraints"]["tone"]="persuasive"
    assert solve(x)["cell_pass"] is False


def test_missing_provenance_fails():
    x=base_case(); x["task"]["evidence"][0]["provenance"]=[]
    assert solve(x)["cell_pass"] is False


def test_conflict_marker_tracks_explicit_binding():
    a=solve(base_case())
    x=base_case(); x["task"]["support_bindings"][1]["status"]="SUPPORTED"
    b=solve(x)
    assert "C2" in a["uncertainty_claim_ids"]
    assert "C2" not in b["uncertainty_claim_ids"]
    assert "Conflict:" in a["rendered_text"]
    assert "Conflict:" not in b["rendered_text"]
