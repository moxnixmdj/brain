from canonical.runtime import unknown_domain_direct_v2_universal_proof_v2 as proof


def test_exact_truth_repaired_bindings_and_zero_case_universal_status():
    out = proof.prove()
    assert out["status"] == (
        "PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_TRUTH_REPAIRED_NUMERIC_SCORER"
    )
    assert out["scope"]["production_population_cases"] == 27
    assert out["scope"]["terminal_or_production_cases_generated"] == 0
    assert out["fresh_reality_required_for_THIS_frozen_generator_claim"] is False
    assert out["production_execution_information_gain"] == 0
    assert out["exact_subject_blobs"] == proof.EXPECTED_BLOBS


def test_add2_role_order_binary64_divergence_is_inside_semantic_tolerance():
    out = proof.prove()["transfer_proof"]
    assert out["add2_wrong_support_min_gap"] >= 1.5
    assert out["add2_role_order_divergence_bound"] < out["scorer_numeric_abs_tol"]
    assert out["scorer_numeric_abs_tol"] == 1e-12
    assert out["add2_true_support_role_swap_safe_under_v2_numeric_semantics"] is True


def test_all_six_transfer_families_and_abstention_partition_remain_closed():
    out = proof.prove()
    transfer = out["transfer_proof"]
    abstention = out["abstention_proof"]
    assert transfer["all_six_families_universal"] is True
    assert transfer["sat_mono_min_output_gap"] > transfer["sat_mono_max_close_tolerance"]
    assert transfer["sign_negative_probe_distractor_min"] > 0
    assert transfer["step_wrong_side_margin"] > 2.54
    assert abstention["all_three_classes_universal"] is True
    assert abstention["cases_per_class"] == 5


def test_no_credit_or_open_world_overclaim():
    out = proof.prove()
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert out["accounting"]["capability_credit_delta"] == 0
    assert out["accounting"]["ownership_credit_delta"] == 0
    assert any("OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])
