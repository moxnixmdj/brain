from fractions import Fraction
from itertools import combinations

from canonical.runtime.livebench_pointwise_optimality_certificate_v1 import (
    exact_score,
    frozen_bound,
    minimum_unsat_core_cover,
    required_next_cardinality_subsets,
    verify_pointwise_optimality_structure,
)


def test_exact_score_matches_frozen_public_formula():
    assert exact_score(5, 5) == Fraction(1, 1)
    assert exact_score(5, 4) == Fraction(2, 5)
    assert exact_score(2, 1) == Fraction(1, 4)


def test_full_score_is_trivially_pointwise_optimal():
    result = verify_pointwise_optimality_structure([True, True, True], [])
    assert result["status"] == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    assert result["required_unsat_subset_count"] == 0


def test_next_cardinality_cover_is_sufficient_structurally():
    required = required_next_cardinality_subsets(5, 2)
    assert len(required) == 10
    result = verify_pointwise_optimality_structure(
        [True, True, False, False, False],
        required,
    )
    assert result["status"] == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    assert result[
        "pointwise_optimality_follows_if_supplied_unsat_proofs_are_semantically_valid"
    ]


def test_missing_one_unsat_subset_fails_closed():
    required = list(required_next_cardinality_subsets(5, 2))
    result = verify_pointwise_optimality_structure(
        [True, True, False, False, False],
        required[:-1],
    )
    assert result["status"].startswith("FAIL_CLOSED")
    assert len(result["missing_unsat_subsets"]) == 1


def test_no_larger_satisfiable_set_can_exist_if_all_g_plus_1_subsets_unsat():
    # Exhaustive finite-set theorem check for k <= 5: every subset with size > g
    # contains at least one (g+1)-subset.
    for k in range(1, 6):
        universe = range(k)
        for g in range(k):
            cut = set(required_next_cardinality_subsets(k, g))
            for size in range(g + 1, k + 1):
                for larger in combinations(universe, size):
                    assert any(set(small) <= set(larger) for small in cut)


def test_frozen_certificate_fanout_is_at_most_ten():
    bound = frozen_bound()
    assert bound["max_checkers_per_case"] == 5
    assert bound["max_required_unsat_subsets"] == 10


def test_verified_smaller_unsat_cores_cover_many_next_cardinality_subsets():
    result = verify_pointwise_optimality_structure(
        [True, True, True, False, False],
        [(0, 3), (1, 4)],
    )
    assert result["status"] == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    assert result["required_unsat_subset_count"] == 5
    assert result["supplied_unsat_core_count"] == 2
    assert result["minimum_unsat_core_cover_count"] == 2
    assert result["minimum_unsat_core_cover"] == [[0, 3], [1, 4]]


def test_partial_core_cover_fails_closed():
    result = verify_pointwise_optimality_structure(
        [True, True, True, False, False],
        [(0, 3)],
    )
    assert result["status"].startswith("FAIL_CLOSED")
    assert result["minimum_unsat_core_cover"] is None
    assert result["missing_unsat_subsets"]


def test_unsat_core_cannot_contradict_observed_candidate_true_results():
    try:
        verify_pointwise_optimality_structure([True, True, False], [(0, 1)])
    except ValueError as exc:
        assert str(exc) == "UNSAT_CORE_CONTRADICTS_CANDIDATE_RESULTS"
    else:
        raise AssertionError("contradictory UNSAT core must fail closed")


def test_minimum_unsat_core_cover_preserves_exact_subset_certificates():
    required = required_next_cardinality_subsets(5, 2)
    cover = minimum_unsat_core_cover(5, 2, required)
    assert cover is not None
    assert len(cover) == 10
