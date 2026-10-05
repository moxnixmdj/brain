from canonical.runtime import livebench_release_unconditional_schema_envelope_v1 as e


def test_unconditional_release_envelope_removes_paper_assumption():
    out = e.verify()
    assert out["compatible_total"] == 3108
    assert out["compatible_by_cardinality"] == {1: 19, 2: 108, 3: 391, 4: 958, 5: 1632}
    assert len(out["extra_signatures"]) == 7
    assert out["proof_obligation_reduction"]["paper_15_vs_16_faithfulness_assumption_required"] is False
    assert out["proof_obligation_reduction"]["response_language_required"] is False
    assert out["terminal_rows_read"] == 0
    assert out["acceptance_credit"] is False


def test_only_six_nonactive_extension_classes_remain():
    out = e.verify()
    assert out["remaining_pointwise_extension_classes"] == [
        "CONSTRAINED_SINGLETON",
        "ENGLISH_CAPITAL",
        "ENGLISH_LOWERCASE",
        "NO_COMMA",
        "ENGLISH_CAPITAL_PLUS_NO_COMMA",
        "ENGLISH_LOWERCASE_PLUS_NO_COMMA",
    ]
