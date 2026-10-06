from canonical.runtime import terminal_frontier_factorizer_v1 as v1
from canonical.runtime.terminal_frontier_factorizer_v2 import (
    DELETED_NON_NECESSARY,
    factorize,
)


def test_exact_lossless_contraction_is_v1_minus_one_dependency_predicate():
    out = factorize()
    assert out["truth_obligation_count"] == 31
    assert out["historical_v1_truth_obligation_count"] == 32
    assert out["open_atomic_count"] == 23
    assert out["meta_count"] == 8
    assert out["truth_obligations_deleted"] == 1
    assert out["truth_obligations_closed"] == 0
    assert out["deleted_non_necessary_obligations"] == [DELETED_NON_NECESSARY]
    assert set(out["obligation_interfaces"]) == (
        set(v1.ATOMIC) | set(v1.META)
    ) - {DELETED_NON_NECESSARY}


def test_deleted_predicate_is_historical_dependency_proof_not_score_or_behavior_atom():
    out = factorize()
    pre = out["preconditions"]
    assert pre["historical_registry_predicate_preserved"] is True
    assert pre["historical_kind"] == "DEPENDENCY_PROOF"
    assert pre["historical_family"] == "MULTI_CAPABILITY_COMPOSITION"
    assert pre["deleted_from_terminal_necessity_only"] is True


def test_composition_behavioral_and_invariant_obligations_remain():
    out = factorize()
    req = out["obligation_interfaces"]
    for item in (
        "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    ):
        assert item in req
        assert "UNIVERSAL_SCOPE_AND_COMPOSITION" in req[item]
    assert DELETED_NON_NECESSARY not in req


def test_all_other_v1_obligations_and_four_interfaces_are_preserved():
    old = v1.factorize()
    new = factorize()
    assert set(new["interfaces"]) == set(old["interfaces"])
    for name in new["interfaces"]:
        expected = set(old["interfaces"][name]) - {DELETED_NON_NECESSARY}
        assert set(new["interfaces"][name]) == expected
