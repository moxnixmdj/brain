from canonical.runtime.synthesis_zero_required_uncertainty_policy_v1 import INPUT_SCHEMA, solve

def _constraints():
    return {
        "output_format":"BULLETS",
        "citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED",
        "required_sections":[],
        "allowed_sections":None,
        "max_items":12,
        "max_chars":5000,
        "heading_level":2,
        "require_title":False,
    }

def _base():
    return {
        "schema":INPUT_SCHEMA,
        "task":{
            "required_uncertainty_or_disagreement_units":[],
            "claims":[{"claim_id":"C1","text":"Revenue growth is 12.","required":True}],
            "evidence":[{
                "evidence_id":"E1",
                "text":"Report states Revenue growth is 12.",
                "verified":True,
                "provenance":[{"source_id":"REPORT","locator":"p1"}],
            }],
            "audience_profile":{"profile_id":"EXPLICIT","constraints":_constraints()},
        },
    }

def test_explicit_empty_uncertainty_set_passes():
    out=solve(_base())
    assert out["status"]=="PASS",out
    assert out["matched_quality_projection"]["uncertainty_and_disagreement_preservation"]==1
    assert out["matched_quality_projection"]["required_uncertainty_or_disagreement_units_total"]==0

def test_missing_uncertainty_set_fails_closed():
    x=_base()
    del x["task"]["required_uncertainty_or_disagreement_units"]
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="ZERO_REQUIRED_UNCERTAINTY_NOT_CERTIFIED"

def test_nonempty_uncertainty_set_fails_closed():
    x=_base()
    x["task"]["required_uncertainty_or_disagreement_units"]=["U1"]
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="ZERO_REQUIRED_UNCERTAINTY_NOT_CERTIFIED"

def test_base_policy_failure_propagates():
    x=_base()
    x["task"]["claims"][0]["text"]="Revenue growth is 20."
    out=solve(x)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="V2_BASE_POLICY_NOT_CERTIFIED"
