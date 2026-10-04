from canonical.runtime import livebench_union25_archetypes_v1 as u


def test_union25_exact_registry_structure_counts():
    out = u.verify()
    assert out["nonself_conflict_pair_count"] == 97
    assert out["compatible_by_cardinality"] == {
        1: 25,
        2: 203,
        3: 1055,
        4: 3750,
        5: 9526,
    }
    assert out["compatible_total"] == 14559
    assert out["embedded_active15_total"] == 928
    assert out["extra_bearing_total"] == 13631


def test_union25_extra_signature_and_route_reduction():
    out = u.verify()
    assert out["distinct_extra10_signatures"] == 156
    assert out["route_counts_extra_bearing"] == {
        "GENERAL": 13614,
        "TWO_RESPONSES": 12,
        "REPEAT_PROMPT": 4,
        "CONSTRAINED_SINGLETON": 1,
    }
    assert out["extra_instruction_count_histogram"] == {
        1: 4317,
        2: 5892,
        3: 2906,
        4: 495,
        5: 21,
    }


def test_special_route_compatibility_examples():
    assert u.compatible((u.REPEAT, u.NO_COMMA))
    assert u.compatible((u.TWO, u.LANGUAGE, u.NO_COMMA))
    assert not u.compatible((u.REPEAT, u.LANGUAGE))
    assert not u.compatible((u.CONSTRAINED, u.NO_COMMA))
    assert not u.compatible((u.LANGUAGE, u.SECTIONS))
