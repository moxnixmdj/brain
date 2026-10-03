from canonical.runtime.post_universal_learning_zero_reality_frontier_v1 import (
    EMPIRICAL,
    PRED,
    evaluate,
)


def test_current_frontier_reduces_exactly_one_zero_reality_requirement():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["live_world"]["proved_predicates"] == 11
    assert out["live_world"]["unresolved_predicates"] == 27
    assert out["live_world"]["opus55_acceptance"] == "4/19_PASS__15/19_OPEN"
    assert out["zero_reality_frontier"]["active_zero_reality_requirement_count"] == 16
    assert out["zero_reality_frontier"]["active_nondominated_certificate_count"] == 13
    assert out["zero_reality_frontier"]["zero_reality_covered_predicate_count"] == 24
    assert out["zero_reality_frontier"]["primitive_zero_reality_work_units"] == 30
    assert out["zero_reality_frontier"]["matched_priority_child_facts"] == 16


def test_tool_discovery_moves_to_empirical_reality_residual_without_acceptance_credit():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["transition"]["transitioned_predicate"] == PRED
    assert out["transition"]["remaining_residual"] == EMPIRICAL
    assert set(out["transition"]["direct_reality_blocked_predicates"]) == {
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    }
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0


def test_fresh_reality_and_promotion_remain_forbidden():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["fresh_reality_authority"] is False
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["new_reality_units_consumed"] == 0
    assert out["terminal_results_replayed"] == 0
