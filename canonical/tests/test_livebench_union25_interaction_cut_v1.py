from canonical.runtime import livebench_union25_interaction_cut_v1 as c


def test_union25_extra_partition_is_exact():
    out = c.verify()
    assert out["raw_extra10_signatures"] == 156
    assert out["hard_core_signature_count"] == 20
    assert out["hard_core_reduction_factor"] == 7.8
    assert out["max_hard_core_arity"] == 3
    assert out["hard_core_arity_histogram"] == {0: 1, 1: 6, 2: 9, 3: 4}


def test_only_four_hard_triples_exist():
    out = c.verify()
    assert len(out["hard_triples"]) == 4
    assert sorted(map(tuple, out["hard_triples"])) == sorted([
        (c.u.KEYWORD_FREQUENCY, c.u.LETTER_FREQUENCY, c.u.CAPITAL_FREQUENCY),
        (c.u.KEYWORD_FREQUENCY, c.u.LETTER_FREQUENCY, c.u.ENGLISH_CAPITAL),
        (c.u.KEYWORD_FREQUENCY, c.u.LETTER_FREQUENCY, c.u.ENGLISH_LOWERCASE),
        (c.u.LETTER_FREQUENCY, c.u.LANGUAGE, c.u.CAPITAL_FREQUENCY),
    ])


def test_passive_modifiers_are_pairwise_hard_orthogonal_in_registry_graph():
    for p in c.PASSIVE:
        for h in c.HARD:
            assert c.u.compatible((p, h))


def test_constrained_response_is_exactly_isolated():
    signatures = c._reachable_extra_signatures()
    assert [s for s in signatures if c.u.CONSTRAINED in s] == [
        (c.u.CONSTRAINED,)
    ]
