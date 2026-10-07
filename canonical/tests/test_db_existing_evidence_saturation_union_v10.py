from canonical.runtime.db_existing_evidence_saturation_union_v10_verifier import verify


def test_if_refinement_is_soundly_subtracted_without_new_record():
    out = verify()
    assert out["pass"], out["errors"]
    assert out["sound_record_count"] == 16
    assert out["record_count_delta"] == 0
    assert out["closed_refinement"] == "IF_SCOPE_BOUNDARY_NONINFERIOR"
    assert out["sound_subtraction_from_U"] is True


def test_if_scope_closure_requires_no_opus_query_and_does_not_overclaim():
    out = verify()
    assert out["opus_query_required"] is False
    assert out["U_empty_proved"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
