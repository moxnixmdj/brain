from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_v3_proof_candidate_is_exact_blob_bound_and_zero_credit():
    out = proof.prove()
    assert out["status"] == "PASS_CANDIDATE__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN__INDEPENDENT_VERIFICATION_REQUIRED"
    assert out["exact_subject_blobs"] == proof.EXPECTED_BLOBS
    assert out["v2_counterexample_repaired"] is True
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])


def test_v3_add2_role_identity_is_ordered_and_binary64_safe():
    add2 = proof.prove()["transfer_proof"]["add2_role_identity"]
    assert add2["ordered_role_mapping_unique"] is True
    assert add2["binary64_order_defect_removed"] is True
    assert add2["signatures"]["4"]["r0"] == [-1, 1, -1]
    assert add2["signatures"]["4"]["r1"] == [1, -1, 1]
    assert add2["signatures"]["10"]["r0"] == [-1, 1, -1]
    assert add2["signatures"]["10"]["r1"] == [1, -1, 1]


def test_v3_transfer_proof_keeps_strict_wrong_support_margins():
    out = proof.prove()["transfer_proof"]
    assert out["affine_min_output_gap"] > 2.84
    assert out["complement_min_output_gap"] >= 4.75
    assert out["sat_mono_min_output_gap"] > out["sat_mono_max_close_tolerance"]
    assert out["sign_negative_probe_distractor_min"] > 0
    assert out["step_wrong_side_margin"] > 2.54
    assert out["add2_wrong_support_min_gap"] >= 1.5
    assert out["max_transfer_probes"] < out["full_rediscovery_probe_floor"]
