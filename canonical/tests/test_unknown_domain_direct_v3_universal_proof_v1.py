from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_v3_universal_proof_candidate_closes_both_revoked_v2_holes():
    out = proof.prove()
    assert out["status"] == (
        "PASS__V3_UNIVERSAL_PROOF_CANDIDATE__INDEPENDENT_VERIFICATION_REQUIRED"
    )
    assert out["identifier_totality"]["status"] == (
        "PASS__STRUCTURAL_IDENTIFIER_TOTALITY"
    )
    assert out["identifier_totality"]["hmac_collision_freedom_assumed"] is False
    assert out["add2_exactness"]["status"] == (
        "PASS__ADD2_EXACT_IEEE754_ROLE_ORIENTATION"
    )
    assert out["add2_exactness"]["add2_indexes"] == [4, 10]
    assert set(out["known_v2_revocation_holes_closed"]) == {
        "STRUCTURAL_IDENTIFIER_TOTALITY_WITHOUT_HMAC_COLLISION_ASSUMPTION",
        "EXACT_ADD2_IEEE754_ROLE_ORDER_EQUALITY",
    }


def test_v3_universal_proof_has_strict_non_add2_separation_margins():
    out = proof.prove()["other_transfer_families"]
    assert out["status"] == "PASS__FIVE_NON_ADD2_TRANSFER_FAMILIES"
    assert out["affine_first_probe_min_gap"] > 0
    assert out["complement_first_probe_min_gap"] > 0
    assert out["sat_mono_first_probe_min_gap"] > out[
        "sat_mono_max_close_tolerance"
    ]
    assert out["sign_first_probe_shifted_distractor_min"] > 0
    assert out["step_second_probe_wrong_side_margin"] > 0
    assert out["max_transfer_probes"] == 2


def test_v3_universal_proof_remains_zero_credit_before_independent_verification():
    out = proof.prove()
    assert out["production_or_terminal_cases_consumed"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])
