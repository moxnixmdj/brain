from canonical.runtime import livebench_historical24_composition_space_v1 as space


def test_historical24_exact_conservative_structural_space():
    out = space.verify()
    assert out["status"] == "PASS__13750_CONSERVATIVE_HISTORICAL24_STRUCTURAL_SETS"
    assert out["compatible_structural_set_count"] == 13750
    assert out["counts_by_size"] == {1: 24, 2: 189, 3: 980, 4: 3514, 5: 9043}
    assert out["counts_by_route"] == {
        "CONSTRAINED_RESPONSE": 1,
        "GENERAL": 13721,
        "JSON": 4,
        "REPEAT_PROMPT": 8,
        "TWO_RESPONSES": 16,
    }
    assert out["active15_structural_set_count"] == 928
    assert out["sets_containing_at_least_one_extra9_family"] == 12822
    assert 14.8 < out["structural_expansion_factor_vs_active15"] < 14.9


def test_special_routes_are_tiny_and_exact():
    sets = space.enumerate_compatible_sets()
    special = [x for x in sets if space.route(x) != "GENERAL"]
    assert len(special) == 29
    assert sum(space.CONSTRAINED in x for x in special) == 1
    assert sum(space.JSON_ID in x for x in special) == 4
    assert sum(space.REPEAT in x for x in special) == 8
    assert sum(space.TWO in x for x in special) == 16
