from canonical.runtime import livebench_union25_extension_cut_v1 as cut


def test_union25_extension_cut_counts():
    out = cut.verify()
    assert out["compatible_set_count"] == 14559
    assert out["compatible_sets_by_cardinality"] == {
        1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526
    }
    assert out["active15_only_set_count"] == 928
    assert out["new_family_containing_set_count"] == 13631
    assert out["raw_new_family_signature_count"] == 157
    assert out["hard_extension_signature_count"] == 21


def test_special_routes_collapse():
    sets = cut.enumerate_compatible_sets()
    assert [x for x in sets if cut.CONSTRAINED in x] == [(cut.CONSTRAINED,)]
    assert not [
        x for x in sets
        if cut.JSON_ID in x and (set(x) & cut.NEW10)
    ]
    assert {
        tuple(sorted(set(x) & cut.NEW10))
        for x in sets if cut.REPEAT in x
    } == {(), (cut.NO_COMMA,)}
    assert {
        tuple(sorted(set(x) & cut.NEW10))
        for x in sets if cut.TWO in x
    } == {
        (),
        (cut.LANGUAGE,),
        (cut.NO_COMMA,),
        tuple(sorted((cut.LANGUAGE, cut.NO_COMMA))),
    }


def test_union25_word_ceiling_stays_below_public_minimum():
    out = cut.verify()
    assert out["word_channel"]["conservative_unpadded_global_ceiling_over_WORDS_sets"] == 63
    assert out["word_channel"]["public_minimum_less_than_threshold"] == 100
    assert out["word_channel"]["margin_words"] == 37


def test_hard_signature_basis_is_exactly_21():
    sets = cut.enumerate_compatible_sets()
    actual = {cut.hard_extension_signature(x) for x in sets}
    assert actual == set(cut.EXPECTED_HARD_SIGNATURES)
