from canonical.runtime.verify_terminal_scheduling_v12_candidate_v1 import evaluate

def test_v12_exact_current_world():
    x = evaluate()
    assert x["pass"] is True, x
    assert x["active_zero_reality_requirements"] == 17
    assert x["active_nondominated_certificates"] == 14
    assert x["zero_reality_covered_predicates"] == 25
    assert x["primitive_zero_reality_work_units"] == 31
    assert x["direct_reality_blocked_predicates"] == [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]
    assert x["tool_discovery_retrieval_authority"] == "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
    assert x["opus55_acceptance"] == "4/19_PASS__15/19_OPEN"
    assert x["fresh_reality_authority"] is False
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False
    assert x["acceptance_credit_delta"] == 0
    assert x["family_credit_delta"] == 0
    assert x["ownership_credit_delta"] == 0
    assert x["incremental_spend_usd"] == 0
