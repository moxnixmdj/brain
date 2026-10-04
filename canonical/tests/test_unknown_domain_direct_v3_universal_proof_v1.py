from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_v3_universal_candidate_is_content_bound_and_zero_reality():
    out = proof.prove()
    assert out["status"] == "PASS_CANDIDATE__UNIVERSAL_OVER_EVERY_SUCCESSFULLY_EMITTED_EXACT_V3_POPULATION"
    assert out["scope"]["every_successfully_emitted_population"] is True
    assert out["scope"]["production_or_terminal_cases_generated_by_proof"] == 0
    assert out["exact_subject_blobs"] == proof.EXPECTED_BLOBS
    assert out["accounting"]["acceptance_credit_delta"] == 0


def test_v3_add2_lemma_repairs_exact_role_and_ieee754_order():
    row = proof.prove()["add2_exact_role_and_float_lemma"]
    assert row["indexes"] == [4, 10]
    assert row["r0_signature"] == [-1, 1, -1]
    assert row["r1_signature"] == [1, -1, 1]
    assert row["first_probe_wrong_support_min_gap"] == 1.5
    assert "IDENTICAL_" in row["exact_float_equality_reason"]


def test_v3_identifier_totality_is_fail_closed_before_emission():
    row = proof.prove()["identifier_totality_lemma"]
    assert row["scope"] == "EVERY_SUCCESSFULLY_EMITTED_V3_POPULATION"
    assert all("FAIL_CLOSED" in value for key, value in row.items() if key != "scope")


def test_revoked_v2_counterexample_passes_under_v3_exactly():
    row = proof.prove()["revoked_v2_counterexample_repaired"]
    assert row["qualification_only"] is True
    assert row["scorer_pass"] is True
    assert row["exact_terminal_equality"] is True
    assert row["probe_count"] == 1
