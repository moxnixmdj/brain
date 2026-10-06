from canonical.runtime.terminal_relevance_preorder_factorization_v1 import (
    exhaustive_monotone_dominates,
    hidden_evaluator_counterexample,
    upper_set_dominates,
    upper_sets,
)


def test_hidden_evaluator_counterexample_kills_unproved_finite_list_completeness():
    out = hidden_evaluator_counterexample()
    assert out["declared_finite_evaluator_passes"] is True
    assert out["upper_set_basis_passes"] is False
    assert out["hidden_terminal_gap_detected"] is True


def test_upper_sets_for_three_level_chain():
    items = ("bad", "ok", "good")
    geq = {
        ("bad", "bad"), ("ok", "ok"), ("good", "good"),
        ("ok", "bad"), ("good", "ok"), ("good", "bad"),
    }
    got = set(upper_sets(items, geq))
    assert got == {
        frozenset(),
        frozenset({"good"}),
        frozenset({"ok", "good"}),
        frozenset({"bad", "ok", "good"}),
    }


def test_upper_set_and_exhaustive_monotone_checks_agree_on_finite_chain_examples():
    items = ("bad", "ok", "good")
    geq = {
        ("bad", "bad"), ("ok", "ok"), ("good", "good"),
        ("ok", "bad"), ("good", "ok"), ("good", "bad"),
    }
    examples = [
        ({"bad": 0.0, "ok": 0.0, "good": 1.0}, {"bad": 0.0, "ok": 1.0, "good": 0.0}),
        ({"bad": 0.0, "ok": 1.0, "good": 0.0}, {"bad": 1.0, "ok": 0.0, "good": 0.0}),
        ({"bad": 0.5, "ok": 0.0, "good": 0.5}, {"bad": 0.0, "ok": 1.0, "good": 0.0}),
        ({"bad": 1.0, "ok": 0.0, "good": 0.0}, {"bad": 0.0, "ok": 0.0, "good": 1.0}),
    ]
    for brain, opus in examples:
        assert upper_set_dominates(brain, opus, items=items, geq=geq) == exhaustive_monotone_dominates(
            brain, opus, items=items, geq=geq
        )
