from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA,solve

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

def base(required_uncertainty_units=None):
    if required_uncertainty_units is None:
        required_uncertainty_units=[]
    return {
        "schema":INPUT_SCHEMA,
        "task":{
            "claims":[
                {"claim_id":"C1","text":"Revenue growth is 12.","required":True},
            ],
            "evidence":[
                {
                    "evidence_id":"E1",
                    "text":"Report states Revenue growth is 12.",
                    "verified":True,
                    "provenance":[{"source_id":"REPORT","locator":"p1"}],
                },
            ],
            "audience_profile":{
                "profile_id":"EXPLICIT",
                "constraints":constraints(),
            },
            "required_uncertainty_units":required_uncertainty_units,
        },
    }

def test_missing_uncertainty_binding_fails_closed():
    x=base()
    del x["task"]["required_uncertainty_units"]
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="REQUIRED_UNCERTAINTY_BINDING_MISSING"

def test_explicit_zero_uncertainty_passes():
    out=solve(base([]))
    assert out["status"]=="PASS",out
    assert out["uncertainty_audit"]["required_uncertainty_count"]==0
    assert out["uncertainty_audit"]["all_required_uncertainty_preserved"] is True

def test_required_uncertainty_is_rendered_with_provenance():
    x=base([{
        "uncertainty_id":"U1",
        "text":"The forecast interval remains unresolved.",
        "provenance":[{"source_id":"MODEL_CARD","locator":"sec2"}],
    }])
    out=solve(x)
    assert out["status"]=="PASS",out
    assert out["uncertainty_audit"]["required_uncertainty_count"]==1
    assert out["uncertainty_audit"]["preserved_uncertainty_count"]==1
    assert "Uncertainty: The forecast interval remains unresolved." in out["rendered_text"]
    assert "[src:MODEL_CARD@sec2]" in out["rendered_text"]

def test_required_uncertainty_without_provenance_fails_closed():
    x=base([{"uncertainty_id":"U1","text":"Open uncertainty."}])
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="PROVENANCE_REQUIRED"

def test_item_budget_cannot_drop_uncertainty():
    x=base([{
        "uncertainty_id":"U1",
        "text":"The forecast interval remains unresolved.",
        "provenance":[{"source_id":"MODEL_CARD","locator":"sec2"}],
    }])
    x["task"]["audience_profile"]["constraints"]["max_items"]=1
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="UNCERTAINTY_PRESERVATION_REALIZATION_FAILED"
    assert out["details"]["reason"]=="MAX_ITEMS_INFEASIBLE__NO_CONTENT_DROPPED"

def test_multiple_uncertainties_preserve_explicit_input_order():
    x=base([
        {"uncertainty_id":"U2","text":"Second unresolved issue.","provenance":[{"source_id":"S","locator":"2"}]},
        {"uncertainty_id":"U1","text":"First unresolved issue.","provenance":[{"source_id":"S","locator":"1"}]},
    ])
    out=solve(x)
    assert out["status"]=="PASS",out
    ids=[r["item_id"] for r in out["render_trace"]]
    assert ids==["CLAIM_C1","UNCERTAINTY_U2","UNCERTAINTY_U1"]

def test_unresolved_claim_evidence_relation_still_fails_closed():
    x=base([])
    x["task"]["evidence"].append({
        "evidence_id":"E2",
        "text":"Revenue increased materially after launch.",
        "verified":True,
        "provenance":[{"source_id":"NEWS","locator":"p2"}],
    })
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="V2_BASE_POLICY_FAIL_CLOSED"
    assert out["details"]["reason"]=="OUTSIDE_CELL_UNRESOLVED_CLAIM_EVIDENCE_RELATION"
