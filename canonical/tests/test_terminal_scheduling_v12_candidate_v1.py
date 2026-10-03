from canonical.runtime.verify_terminal_scheduling_v12_candidate_v1 import evaluate

def test_v12_exact_current_world():
    x=evaluate()
    assert x["pass"] is True,x
    assert x["active_zero_reality_requirements"]==17
    assert x["active_nondominated_certificates"]==14
    assert x["proved_predicates"]==11
    assert x["unresolved_predicates"]==27
    assert x["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
    assert "V2_V3_V4" in x["tool_discovery_gate_status"]
    assert x["fresh_reality_authority"] is False
    assert x["acceptance_credit_delta"]==0
    assert x["family_credit_delta"]==0
    assert x["ownership_credit_delta"]==0
