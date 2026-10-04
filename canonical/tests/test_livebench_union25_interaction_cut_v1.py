from canonical.runtime import livebench_union25_interaction_cut_v1 as u


def test_exact_registry25_structural_counts():
    out = u.verify()
    assert out["compatible_structural_set_total"] == 14559
    assert out["compatible_structural_sets_by_cardinality"] == {
        1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526,
    }


def test_union25_factors_to_157_new10_signatures_plus_active15_residual():
    out = u.verify()
    assert out["new10_reachable_interaction_signature_count"] == 157
    assert out["active15_only_structural_sets"] == 928
    assert out["union25_extension_structural_sets"] == 13631
    assert out["sets_by_new_family_count"] == {
        0: 928, 1: 4317, 2: 5892, 3: 2906, 4: 495, 5: 21,
    }


def test_every_residual_is_active15_compatible_and_factorization_is_total():
    rows = u.enumerate_compatible_sets()
    assert len(rows) == 14559
    for row in rows:
        new, old = u.factor(row)
        assert set(new) <= set(u.NEW10)
        assert set(old) <= set(u.ACTIVE15)
        assert u.compatible(old)
        assert len(new) + len(old) == len(row)


def test_constrained_response_is_structurally_isolated():
    rows = [
        row for row in u.enumerate_compatible_sets()
        if "detectable_format:constrained_response" in row
    ]
    assert rows == [("detectable_format:constrained_response",)]


def test_per_new_family_census_is_frozen():
    out = u.verify()
    assert out["per_new_family_structural_set_count"] == {
        "keywords:frequency": 3690,
        "keywords:letter_frequency": 3938,
        "language:response_language": 809,
        "detectable_content:number_placeholders": 3938,
        "detectable_format:constrained_response": 1,
        "detectable_format:number_highlighted_sections": 2858,
        "change_case:capital_word_frequency": 2738,
        "change_case:english_capital": 2490,
        "change_case:english_lowercase": 2490,
        "punctuation:no_comma": 3952,
    }
