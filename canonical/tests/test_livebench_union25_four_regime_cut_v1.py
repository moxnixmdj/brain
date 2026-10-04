from canonical.runtime import livebench_union25_four_regime_cut_v1 as r


def test_four_regimes_exactly_cover_twenty_hard_kernels():
    out = r.verify()
    assert out["upstream_hard_kernel_count"] == 20
    assert out["solver_regime_count"] == 4
    assert out["structural_solver_path_reduction_factor"] == 5.0
    assert out["regime_kernel_counts"] == {
        "COUNT_ONLY": 8,
        "LANGUAGE": 4,
        "ENGLISH_CAPITAL": 4,
        "ENGLISH_LOWERCASE": 4,
    }
    assert out["exact_cover"] is True
    assert out["pairwise_disjoint"] is True


def test_every_upstream_kernel_classifies_once():
    upstream = r.k.verify()
    seen = set()
    for row in upstream["hard_signatures"]:
        ids = tuple(row["ids"])
        cls = r.classify(ids)
        assert cls["regime"] in r.REGIME_AXES
        seen.add(ids)
    assert len(seen) == 20


def test_regime_conflict_geometry_is_exact():
    assert not r.u.compatible((r.u.LANGUAGE, r.u.KEYWORD_FREQUENCY))
    assert r.u.compatible((r.u.LANGUAGE, r.u.LETTER_FREQUENCY))
    assert r.u.compatible((r.u.LANGUAGE, r.u.CAPITAL_FREQUENCY))
    for mode in (r.u.ENGLISH_CAPITAL, r.u.ENGLISH_LOWERCASE):
        assert not r.u.compatible((mode, r.u.CAPITAL_FREQUENCY))
        assert r.u.compatible((mode, r.u.KEYWORD_FREQUENCY))
        assert r.u.compatible((mode, r.u.LETTER_FREQUENCY))
