from canonical.runtime.current_26_zero_reality_frontier_v1 import evaluate

def test_live_current_26():
    x=evaluate()
    assert x["pass"] is True, x
    w=x["live_world"]
    assert (w["proved_predicates"],w["unresolved_predicates"])==(12,26)
    assert (w["active_zero_reality_requirements"],w["active_nondominated_certificates"])==(16,13)
    assert (w["zero_reality_covered_predicates"],w["primitive_zero_reality_work_units"])==(24,30)
    assert w["matched_priority_child_facts"]==16
    assert w["direct_reality_blocked_predicates"]==[
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]
    assert x["fresh_reality_authority"] is False
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False

def test_tool_discovery_removed_from_frontier():
    x=evaluate()
    assert "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" not in x["active_nondominated_certificate_ids"]
    assert "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL" not in x["active_required_propositions"]
