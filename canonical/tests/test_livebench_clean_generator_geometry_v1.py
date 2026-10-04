from canonical.runtime.livebench_clean_generator_geometry_v1 import (
    EXPECTED_COUNTS_BY_CARDINALITY,
    EXPECTED_TOTAL,
    SOURCE_FAMILIES,
    conflict_free,
    conservative_family_sets,
    verify,
)


def test_source_geometry_exact_counts():
    out = verify()
    assert out["status"] == "PASS__CLEAN_SOURCE_ONLY_GENERATOR_GEOMETRY"
    assert out["source_family_count"] == 24
    assert out["conflict_free_superset_count"] == EXPECTED_TOTAL == 13750
    assert out["counts_by_cardinality"] == EXPECTED_COUNTS_BY_CARDINALITY


def test_language_not_in_historical_generator():
    assert "language:response_language" not in SOURCE_FAMILIES


def test_superset_is_unique_and_conflict_free():
    sets = conservative_family_sets()
    assert len(sets) == len(set(sets))
    assert all(1 <= len(x) <= 5 for x in sets)
    assert all(conflict_free(x) for x in sets)


def test_known_conflicts_and_allowed_sets():
    assert not conflict_free(("detectable_format:constrained_response", "detectable_format:title"))
    assert not conflict_free(("detectable_format:json_format", "detectable_format:title"))
    assert conflict_free(("detectable_format:json_format", "keywords:existence"))
    assert conflict_free(("combination:repeat_prompt", "keywords:existence", "punctuation:no_comma"))
