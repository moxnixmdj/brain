from canonical.runtime import unknown_domain_direct_v3_universal_proof_v2 as proof


def test_exact_bindings_and_zero_reality_universal_status():
    out = proof.prove()
    assert out["status"] == "PASS__UNIVERSAL_OVER_COLLISION_TOTAL_V3_GENERATOR_DOMAIN"
    assert out["scope"]["production_population_cases"] == 27
    assert out["scope"]["terminal_or_production_cases_generated"] == 0
    assert out["fresh_reality_required_for_this_frozen_generator_claim"] is False
    assert out["production_execution_information_gain"] == 0
    assert out["exact_subject_blobs"] == proof.EXPECTED_BLOBS


def test_identifier_proof_does_not_assume_hmac_collision_freedom():
    out = proof.prove()["identifier_proof"]
    assert out["opaque_id_injectivity"] is True
    assert out["independent_of_truncated_hmac_collision_freedom"] is True
    assert out["ordinary_noncollision_v2_spelling_preserved"] is True


def test_transfer_proof_covers_all_six_families_with_probe_budget_margin():
    out = proof.prove()["transfer_proof"]
    assert out["all_six_families_universal"] is True
    assert len(out["per_family_probe_bound"]) == 6
    assert out["max_transfer_probes"] == 2
    assert out["full_rediscovery_probe_floor"] == 3
    assert out["affine_min_wrong_support_output_gap"] >= 2.85
    assert out["complement_min_wrong_support_output_gap"] >= 4.75
    assert out["sat_mono_conservative_min_wrong_support_output_gap"] > out["sat_mono_max_candidate_close_tolerance"]
    assert out["sign_min_shifted_distractor_value_on_negative_probe"] > 0
    assert out["step_second_probe_wrong_side_margin"] >= 2.8
    assert out["add2_min_wrong_support_first_probe_gap"] >= 1.5


def test_abstention_partition_is_complete():
    out = proof.prove()["abstention_proof"]
    assert out["all_three_classes_universal"] is True
    assert out["cases_per_class"] == 5


def test_no_credit_or_open_world_overclaim():
    out = proof.prove()
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert out["accounting"]["capability_credit_delta"] == 0
    assert out["accounting"]["ownership_credit_delta"] == 0
    assert any("OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])
