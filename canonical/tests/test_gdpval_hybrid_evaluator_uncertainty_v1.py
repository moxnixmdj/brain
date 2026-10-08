from canonical.runtime.gdpval_hybrid_evaluator_uncertainty_v1 import verify

H = "a" * 40


def receipt():
    return {
        "verified": True,
        "independent": True,
        "source_path": "canonical/verification/example.json",
        "source_sha": H,
    }


def base():
    return {
        "decomposition_proof": {
            "sound_complete_outer_approximation": True,
            "proof_class": "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
            "receipt": receipt(),
        },
        "difference_vector": ["1/2", "-1/2"],
        "nominal_owner_direction": ["1", "0"],
        "known_cone_generators": [["1", "0"]],
        "bounded_uncertainty_vertices": [["-1/2", "0"], ["0", "0"]],
        "lineality_basis": [],
    }


def test_hybrid_certificate_passes_with_positive_robust_margin():
    out = verify(base())
    assert out["pass"] is True, out
    assert out["robust_margin"] == "1/4"
    assert out["promotion_authority"] is False
    assert out["gdpval_credit_delta"] == 0


def test_decomposition_must_be_semantically_proved():
    m = base()
    m["decomposition_proof"]["sound_complete_outer_approximation"] = False
    out = verify(m)
    assert out["reason"] == "DECOMPOSITION_NOT_PROVED_SOUND_COMPLETE"


def test_public_rubric_only_is_firewalled():
    m = base()
    m["decomposition_proof"]["proof_class"] = "PUBLIC_RUBRIC_ONLY"
    out = verify(m)
    assert out["reason"] == "FORBIDDEN_SEMANTIC_PROOF_CLASS"


def test_receipt_must_be_independent():
    m = base()
    m["decomposition_proof"]["receipt"]["independent"] = False
    out = verify(m)
    assert out["reason"] == "DECOMPOSITION_RECEIPT_INVALID"


def test_difference_vector_must_have_zero_probability_mass():
    m = base()
    m["difference_vector"] = ["1/2", "0"]
    out = verify(m)
    assert out["reason"] == "DIFFERENCE_VECTOR_NOT_ZERO_MASS"


def test_known_cone_negative_direction_fails():
    m = base()
    m["known_cone_generators"] = [["-1", "0"]]
    out = verify(m)
    assert out["reason"] == "KNOWN_CONE_DUAL_MEMBERSHIP_FAIL"


def test_nonorthogonal_lineality_fails_even_with_large_nominal_margin():
    m = base()
    m["nominal_owner_direction"] = ["100", "0"]
    m["lineality_basis"] = [["1", "0"]]
    out = verify(m)
    assert out["reason"] == "NONORTHOGONAL_ARBITRARY_LINEALITY"


def test_bounded_uncertainty_can_be_absorbed_by_margin():
    m = base()
    m["bounded_uncertainty_vertices"] = [["-3/4", "0"], ["0", "0"]]
    out = verify(m)
    assert out["pass"] is True, out
    assert out["robust_margin"] == "1/8"


def test_bounded_uncertainty_can_defeat_margin():
    m = base()
    m["bounded_uncertainty_vertices"] = [["-3", "0"], ["0", "0"]]
    out = verify(m)
    assert out["pass"] is False
    assert out["reason"] == "ROBUST_MARGIN_NEGATIVE"


def test_empty_bounded_uncertainty_means_zero_adjustment():
    m = base()
    m["bounded_uncertainty_vertices"] = []
    out = verify(m)
    assert out["pass"] is True, out
    assert out["worst_bounded_adjustment"] == "0"
    assert out["robust_margin"] == "1/2"


def test_dimension_mismatch_fails_closed():
    m = base()
    m["lineality_basis"] = [["1", "0", "0"]]
    out = verify(m)
    assert out["reason"] == "LINEALITY_BASIS_VECTOR_INVALID"
