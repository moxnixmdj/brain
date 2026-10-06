from itertools import product

import pytest

from canonical.runtime.matched_exact_finite_success_reducer_v1 import (
    MatchedReducerError,
    compare,
    monotonicity_witness,
    reduce_exact,
)


def rows(bits):
    return [
        {"case_id": f"C{i}", "success": bool(v), "verified": True}
        for i, v in enumerate(bits)
    ]


def test_exact_fraction():
    out = reduce_exact(rows([1, 0, 1, 1]))
    assert out["success_count"] == 3
    assert out["case_count"] == 4
    assert out["success_fraction_numerator"] == 3
    assert out["success_fraction_denominator"] == 4


def test_pointwise_superset_implies_noninferior():
    out = compare(rows([1, 1, 1, 0]), rows([1, 0, 1, 0]))
    assert out["comparator_success_set_subset_of_brain"] is True
    assert out["noninferior_on_declared_finite_scope"] is True
    assert out["pointwise_differential_dominance"] is True


def test_counterexample_is_exposed():
    out = compare(rows([1, 0, 1]), rows([1, 1, 0]))
    assert out["comparator_success_set_subset_of_brain"] is False
    assert out["forbidden_comparator_success_brain_failure_case_ids"] == ["C1"]


def test_case_universe_mismatch_fails_closed():
    with pytest.raises(MatchedReducerError, match="CASE_UNIVERSE_MISMATCH"):
        compare(rows([1, 1]), [{"case_id": "X", "success": True, "verified": True}])


def test_unverified_case_fails_closed():
    with pytest.raises(MatchedReducerError, match="NOT_VERIFIED"):
        reduce_exact([{"case_id": "C", "success": True, "verified": False}])


def test_duplicate_case_fails_closed():
    with pytest.raises(MatchedReducerError, match="CASE_ID_DUPLICATE"):
        reduce_exact([
            {"case_id": "C", "success": True, "verified": True},
            {"case_id": "C", "success": False, "verified": True},
        ])


def test_exhaustive_monotonicity_small_n():
    for n in range(1, 9):
        for k0 in range(n + 1):
            for k1 in range(k0, n + 1):
                assert monotonicity_witness(n, k0, k1)["r1_ge_r0"] is True


def test_exhaustive_pointwise_inclusion_implies_count_order_small_n():
    for n in range(1, 6):
        for b in product([False, True], repeat=n):
            for c in product([False, True], repeat=n):
                subset = all((not c[i]) or b[i] for i in range(n))
                if subset:
                    out = compare(rows(b), rows(c))
                    assert out["noninferior_on_declared_finite_scope"] is True
