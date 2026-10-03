from canonical.runtime.tool_discovery_acceptance_promotion_integrator_v1 import evaluate
def test_current_tool_discovery_promotion_delta():
    out=evaluate()
    assert out["pass"] is True, out
    assert out["before"]=={"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15}
    assert out["after"]=={"proved_atomic":12,"unresolved_atomic":26,"accepted_families":5,"open_families":14}
    assert out["newly_proved_predicates"]==["TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"]
    assert out["newly_closed_families"]==["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]
    assert out["ownership_credit_delta"]==0
    assert out["promotion_authority"] is False
