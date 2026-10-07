from canonical.runtime.continuity_admin_filesystem_authority_v1 import evaluate

def test_selected_continuity_admin_authority():
    out=evaluate()
    assert out["pass"] is True
    assert out["status"].startswith("PASS__")
    assert set(out["allowed_effect_classes"]) == {
        "file.open_write","file.remove","file.rename","file.directory_mutation"
    }
    assert out["downstream_mission_effects_separate"] is True

def test_authority_preconditions_complete():
    out=evaluate()
    required={
        "CANONICAL_TASK_QUEUE_JSON_ONLY","SAFE_TASK_ID","BOUND_AGENT_ID",
        "ZERO_INCREMENTAL_SPEND","MISSION_SHA_BINDING","PREREQUISITES_SATISFIED",
        "TASK_SHA_BINDING","LEASE_OWNER_BINDING"
    }
    assert required.issubset(set(out["authority_preconditions"]))
