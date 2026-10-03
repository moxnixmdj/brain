from canonical.runtime.verify_terminal_scheduling_v13_candidate_v1 import evaluate

def test_v13_exact_current_world_and_v5_binding():
    x = evaluate()
    assert x["pass"] is True, x
    assert x["active_zero_reality_requirements"] == 17
    assert x["active_nondominated_certificates"] == 14
    assert x["primitive_zero_reality_work_units"] == 31
    assert x["tool_discovery_retrieval_authority"] == "V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
    assert x["opus55_acceptance"] == "4/19_PASS__15/19_OPEN"
    assert x["proved_predicates"] == 11
    assert x["unresolved_predicates"] == 27
    assert x["fresh_reality_authority"] is False
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False
    assert x["acceptance_credit_delta"] == 0
    assert x["family_credit_delta"] == 0
    assert x["ownership_credit_delta"] == 0
    assert x["incremental_spend_usd"] == 0


if __name__ == "__main__":
    test_v13_exact_current_world_and_v5_binding()
    print("V13 candidate assertions passed")
