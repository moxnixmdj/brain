from canonical.runtime import unknown_domain_direct_v2_universal_proof_v1 as proof


def test_exact_frozen_bindings_and_zero_case_universal_status():
    out = proof.prove()
    assert out["status"] == "PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN"
    assert out["scope"]["production_population_cases"] == 27
    assert out["scope"]["terminal_or_production_cases_generated"] == 0
    assert out["fresh_reality_required_for_THIS_frozen_generator_claim"] is False
    assert out["production_execution_information_gain"] == 0
    assert out["exact_subject_blobs"] == proof.EXPECTED_BLOBS


def test_transfer_families_have_strict_identification_margin():
    out = proof.prove()["transfer_proof"]
    assert out["all_six_families_universal"] is True
    assert out["max_transfer_probes"] == 2
    assert out["full_rediscovery_probe_floor"] == 3
    assert out["affine_min_output_gap"] > 2.84
    assert out["complement_min_output_gap"] >= 4.75
    assert out["sat_mono_min_output_gap"] > out["sat_mono_max_close_tolerance"]
    assert out["sign_negative_probe_distractor_min"] > 0
    assert out["step_wrong_side_margin"] > 2.54
    assert out["add2_wrong_support_min_gap"] >= 1.5
    assert out["add2_true_support_role_swap_safe"] is True


def test_abstention_partition_is_complete_and_deterministic():
    out = proof.prove()["abstention_proof"]
    assert out["all_three_classes_universal"] is True
    assert out["cases_per_class"] == 5
    assert "CONCLUDES" in out["identifiable"]
    assert "ABSTAINS" in out["nonidentifiable"]
    assert "MINIMUM_COST" in out["underspecified"]


def test_no_credit_or_open_world_overclaim():
    out = proof.prove()
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert out["accounting"]["capability_credit_delta"] == 0
    assert out["accounting"]["ownership_credit_delta"] == 0
    assert any("OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])
