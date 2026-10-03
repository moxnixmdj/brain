from canonical.runtime.post_dual_zero_reality_frontier_v1 import evaluate

def test_post_dual_cut():
    x=evaluate()
    assert x["pass"] is True,x
    assert x["acceptance_frontier"]=={"proved":11,"unresolved":27,"total":38,"family_acceptance":"4/19_PASS__15/19_OPEN"}
    assert x["zero_reality_frontier"]["active_certificate_count"]==14
    assert x["zero_reality_frontier"]["active_requirement_count"]==17
    assert x["zero_reality_frontier"]["active_target_count"]==25
    assert set(x["fresh_reality_ready_but_globally_held_predicates"])=={
        "FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    }
    assert x["global_fresh_reality_authority"] is False
    assert x["acceptance_predicate_delta"]==0
    assert x["new_reality_units_consumed"]==0
