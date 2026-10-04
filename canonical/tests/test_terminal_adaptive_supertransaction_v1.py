from canonical.runtime.terminal_adaptive_supertransaction_v1 import evaluate


def test_current_26_state_compiles_to_at_most_two_causal_phases():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["terminal_state"] == {
        "accepted_families": 5,
        "open_families": 14,
        "proved_predicates": 12,
        "unresolved_predicates": 26,
        "root1_positive_gaps": 0,
        "root2_touching_predicates": 19,
        "root3_touching_predicates": 10,
    }, out
    assert out["causal_phase_lower_bound"] == 1
    assert out["causal_phase_upper_bound"] == 2
    assert [x["id"] for x in out["phases"]] == ["Z", "R"]


def test_finality_is_not_a_third_manual_phase():
    out = evaluate()
    assert out["automatic_finality"]["separate_manual_phase_required"] is False
    assert "FINALITY_IS_AUTOMATIC_BACKPROP_NOT_A_SEPARATE_MANUAL_ACTION" in out["hard_rules"]


def test_known_zero_probability_routes_are_deleted():
    out = evaluate()
    rows = {x["route"]: x for x in out["zero_probability_deleted_routes"]}
    assert rows["TB4_FROZEN_CURRENT_NO_REPLAY_THRESHOLD_ROUTE"]["probability_upper"] == 0.0
    assert rows["TB4_CIRCLECI_FREE_XLARGE_GEN2"]["probability_upper"] == 0.0
    assert rows["CURSORBENCH_OWNER_ACCESS_SEARCH"]["probability_upper"] == 0.0
    assert rows["AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH"]["probability_upper"] == 0.0
    assert "180" in rows["TB4_FROZEN_CURRENT_NO_REPLAY_THRESHOLD_ROUTE"]["basis"]
    assert "220" in rows["TB4_FROZEN_CURRENT_NO_REPLAY_THRESHOLD_ROUTE"]["basis"]


def test_retrieval_v19_and_finance_shortcut_are_bound():
    out = evaluate()
    assert out["search_policy"]["current_authority"] == "GLOBAL_RETRIEVAL_ENTRYPOINT_V4"
    assert out["search_policy"]["single_search_engine"] == "REJECTED_AS_STRUCTURALLY_INSUFFICIENT"
    f = out["finance_direct_threshold_delta"]
    assert f["state"] == "VERIFIED_THEOREM_CANDIDATE_REQUIRES_CURRENT_AUTHORITY_BINDING"
    assert f["separate_index_run_required"] is False


def test_fresh_reality_remains_fail_closed():
    out = evaluate()
    assert out["phases"][0]["fresh_reality_allowed"] is False
    assert out["phases"][1]["conditional"] is True
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False


def test_no_credit_from_compilation():
    out = evaluate()
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["new_reality_units_consumed"] == 0
    assert out["incremental_spend_usd"] == 0
