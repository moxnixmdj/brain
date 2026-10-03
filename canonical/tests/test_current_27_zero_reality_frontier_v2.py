from canonical.runtime.current_27_zero_reality_frontier_v2 import evaluate

def test_exact_requirement_subtraction():
    x=evaluate()
    assert x["pass"] is True, x
    assert x["active_requirement_count"]==17
    assert x["active_certificate_count"]==14
    assert x["unresolved_predicates"]==27
    assert x["acceptance_predicate_delta"]==0
    assert x["fresh_reality_authority"] is False
