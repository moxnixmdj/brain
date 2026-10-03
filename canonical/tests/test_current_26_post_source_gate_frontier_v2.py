from canonical.runtime.current_26_post_source_gate_frontier_v2 import evaluate

def test_current_26_post_source_gate_frontier():
    out = evaluate()
    assert out["pass"] is True, out
    world = out["live_world"]
    assert (world["proved_predicates"], world["unresolved_predicates"]) == (12, 26)
    assert world["opus55_acceptance"] == "5/19_PASS__14/19_OPEN"
    assert world["active_zero_reality_requirements"] == 14
    assert world["active_zero_reality_certificates"] == 11
    assert world["zero_reality_covered_predicates"] == 22
    assert world["primitive_zero_reality_work_units"] == 28
    assert world["matched_priority_child_facts"] == 16
    assert world["direct_reality_eligible_predicates"] == [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]
    assert world["global_fresh_reality_authority"] is False

def test_exact_source_gate_requirements_are_subtracted_only_once():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["discharged_zero_reality_requirements"] == [
        "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
        "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
    ]
    reqs = set(out["active_zero_reality_required_propositions"])
    assert "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS" not in reqs
    assert "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS" not in reqs

def test_direct_predicates_remain_open_and_not_executed():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["direct_reality_execution_eligible"] is True
    assert out["direct_reality_execution_authorized_now"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
