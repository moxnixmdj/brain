from canonical.runtime import livebench_legacy15_universal_semantic_quotient_v1 as q


def test_universal_semantic_quotient_shape():
    out = q.verify()
    assert out["status"].startswith("CANDIDATE_UNIVERSAL_SCOPE_PROOF")
    assert out["structural_id_set_count"] == 928
    assert out["lexical_signature_count"] == 192
    assert out["word_threshold_raw_states"] == 802
    assert out["sentence_threshold_raw_states"] == 40
    assert out["nth_numeric_state_count"] == 15
    assert out["repeat_target_reduction"]["opaque_repeat_target_classes"] == 1
    assert out["terminal_rows_used"] is False
    assert out["acceptance_credit"] is False


def test_monotone_boundary_maps_are_total_on_public_domains():
    assert {
        q.word_threshold_representative(n, r)
        for r in ("less than", "at least")
        for n in range(100, 501)
    } == {(100, "less than"), (500, "at least")}
    assert {
        q.sentence_threshold_representative(n, r)
        for r in ("less than", "at least")
        for n in range(1, 21)
    } == {(1, "less than"), (2, "less than"), (20, "at least")}


def test_repeat_prompt_active15_cohabitants_exact():
    out = q.verify_repeat_target_quotient()
    assert out["active15_repeat_cohabitants"] == [
        "detectable_format:title",
        "keywords:existence",
    ]
