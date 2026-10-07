from canonical.runtime.accepted_three_selected_leaf_effect_audit_v1 import evaluate

def test_three_accepted_selected_leaves_are_effect_free():
    out=evaluate()
    assert out["pass"] is True,out
    assert out["route_count"]==3
    assert out["union_material_external_effect_classes"]==[]
    assert {x["family"] for x in out["routes"]}=={
      "SUBAGENT_DELEGATION_AND_COORDINATION",
      "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
      "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    }
    assert all(x["effect_call_hits"]==[] for x in out["routes"])
