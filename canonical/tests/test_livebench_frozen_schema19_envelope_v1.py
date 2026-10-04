from canonical.runtime import livebench_frozen_schema19_envelope_v1 as s


def test_assumption_free_schema19_envelope():
    out = s.verify()
    assert out["envelope_family_count"] == 19
    assert out["compatible_by_cardinality"] == {1: 19, 2: 108, 3: 391, 4: 958, 5: 1632}
    assert out["compatible_total"] == 3108
    assert out["embedded_active15_total"] == 928
    assert out["extra_bearing_total"] == 2180
    assert out["distinct_remaining_extra_signatures"] == 6
    assert out["reduction"]["compatible_sets_deleted"] == 11451
    assert out["reduction"]["extra_signatures_deleted"] == 150
    assert out["assumption_boundary"].startswith("NONE_BEYOND_EXACT_FROZEN_PARQUET_SCHEMA")
    assert out["terminal_rows_read"] == 0
    assert out["acceptance_credit"] is False


def test_schema19_remaining_extra_signatures_are_exact():
    out = s.verify()
    got = {tuple(x) for x in out["remaining_extra_signatures"]}
    assert got == {
        ("detectable_format:constrained_response",),
        ("change_case:english_capital",),
        ("change_case:english_lowercase",),
        ("punctuation:no_comma",),
        ("change_case:english_capital", "punctuation:no_comma"),
        ("change_case:english_lowercase", "punctuation:no_comma"),
    }
