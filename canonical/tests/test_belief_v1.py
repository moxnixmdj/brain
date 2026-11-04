"""A model of the world, and the worlds in which it must fail.

The claim these tests defend is small and load-bearing: the system can form an expectation about
something it has never done, the expectation is falsifiable, and it only grows structure when the
structure survives data it did not see. Each test below is paired with the world that breaks the
mechanism it names -- a model that accepts everything and a model that accepts nothing both fail
here.

Measured background (2026-11-04): the first version of this file scored 0.562 on held-out
capabilities while a one-line hand rule scored 0.729, because it tried exactly one candidate
distinction and gave up when the world rejected it. Two sign errors and an unrepresentative
single validation slice were found by these worlds, not by reading the code.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief  # noqa: E402


# --------------------------------------------------------------------------- worlds
def separable(n: int, seed: int, cut: float = 0.55) -> list[dict]:
    """A world with one real rule: above the cut is 'BAD'. Everything else is noise."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        aura = rng.random()
        out.append({"group": f"g{i}", "signals": {"aura": aura, "noise": rng.random()},
                    "verdict": "BAD" if aura > cut else "OK"})
    return out


def pure_noise(n: int, seed: int) -> list[dict]:
    """A world with no rule at all. Any structure found here is a lie."""
    rng = random.Random(seed)
    return [{"group": f"g{i}", "signals": {"a": rng.random(), "b": rng.random()},
             "verdict": rng.choice(["X", "Y"])} for i in range(n)]


# --------------------------------------------------------------------------- the claim
def test_it_learns_a_rule_it_can_see_and_beats_the_base_rate():
    train = separable(70, 1)
    model = belief.blank()
    belief.fit(model, train)
    for example in train:
        belief.observe(model, example["signals"], example["verdict"])

    unseen = separable(300, 3)
    hit, answered = belief.accuracy(model, unseen)
    assert answered == len(unseen), "it declined to answer its own test set"
    assert hit >= 0.9, f"it found the rule only {hit:.3f} of the time"
    assert hit - belief.majority_baseline(unseen) > 0.3, (
        "accuracies mean nothing without the baseline beside them")


def test_it_refuses_to_find_structure_in_a_world_with_none():
    """The guard that makes the rest credible. Before it existed this accepted splits in
    seven of twenty noise worlds, because a lucky fold paid for two unlucky ones."""
    accepted = 0
    for trial in range(6):
        model = belief.blank()
        belief.fit(model, pure_noise(60, trial))
        accepted += model["splits_accepted"]
    assert accepted == 0, f"it invented {accepted} distinctions in six worlds with no rule"


def test_a_distinction_must_beat_what_shuffling_produces():
    """A split is not real because it improves accuracy once. Compare it against the same
    split under verdicts that have been shuffled -- if shuffling does as well, there is nothing
    there. This is the difference between a gate and a formality."""
    data = pure_noise(120, 11)
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    node = belief._leaf_from(data)
    before, after, _ = belief._verdict(node, "a", 0.5, folds)
    p = belief._cv_p(node, "a", 0.5, folds, after)
    assert p > belief.PERMUTATION_ALPHA, (
        f"a split on noise in a noise world passed the null (p={p})")

    real = separable(120, 12)
    real_folds = belief.capability_folds(real, seed=belief.PERMUTATION_SEED)
    real_node = belief._leaf_from(real)
    _, real_after, _ = belief._verdict(real_node, "aura", 0.55, real_folds)
    real_p = belief._cv_p(real_node, "aura", 0.55, real_folds, real_after)
    assert real_p < belief.PERMUTATION_ALPHA, (
        f"a real rule failed the null (p={real_p}); the gate is too strict to learn anything")


def test_it_says_nothing_when_it_knows_nothing():
    model = belief.blank()
    assert belief.predict(model, {"anything": 1.0}) is None
    assert belief.confidence(model, {"anything": 1.0}) == 0.0
    hit, answered = belief.accuracy(model, separable(20, 5))
    assert answered == 0 and hit == 0.0
    # and "no answer" is never counted as a correct answer
    assert belief.majority_baseline([]) == 0.0


def test_it_predicts_something_it_has_never_seen():
    """The whole point. Every training example is a different group; the model is then asked
    about signals it has never been given, and it answers from the rule rather than from a
    memory of the question."""
    train = separable(80, 21)
    model = belief.blank()
    belief.fit(model, train)
    for example in train:
        belief.observe(model, example["signals"], example["verdict"])

    for aura, expected in ((0.95, "BAD"), (0.05, "OK")):
        signals = {"aura": aura, "noise": 0.5}
        assert belief.predict(model, signals) == expected, (
            f"at aura={aura} it expected {belief.predict(model, signals)!r}, not {expected!r}")


def test_an_unreadable_signal_falls_back_to_what_it_knew():
    """A split must not turn a missing sense into a missing opinion."""
    model = {"root": belief._split_node(
        {"kind": "leaf", "counts": {"OK": 5}}, "aura", 0.5,
        {"kind": "leaf", "counts": {"OK": 9}}, {"kind": "leaf", "counts": {"BAD": 9}})}
    assert belief.predict(model, {"aura": 0.9}) == "BAD"
    assert belief.predict(model, {}) == "OK", "it lost its prior when a sense was missing"


def test_folds_never_put_a_group_on_both_sides():
    data = separable(40, 31)
    folds = belief.capability_folds(data, k=4)
    for train, test in folds:
        train_groups = {ex["group"] for ex in train}
        test_groups = {ex["group"] for ex in test}
        assert not (train_groups & test_groups), "a group was fitted and tested at once"
    seen = [ex["group"] for _, test in folds for ex in test]
    assert sorted(seen) == sorted({ex["group"] for ex in data}), "some group was never tested"


def test_the_described_structure_matches_what_it_predicts():
    """A report that does not reconstruct the behaviour is decoration."""
    train = separable(60, 41)
    model = belief.blank()
    belief.fit(model, train)
    for example in train:
        belief.observe(model, example["signals"], example["verdict"])
    described = belief.describe(model)
    assert described["schema"] == belief.SCHEMA
    assert described["structure"], "it described itself as nothing"
    assert "ACCURACY_IS_MEANINGLESS_WITHOUT_THE_BASELINE_IT_IS_COMPARED_TO" in described["non_claims"]


def test_a_split_that_helps_on_average_but_hurts_a_group_is_refused():
    """Measured 2026-11-04: without this rule, twenty pure-noise worlds produced ten accepted
    splits, because one lucky group paid for two unlucky ones. A rule about the world does not
    need a group to make an exception for it."""
    def ex(s, v, group):
        return {"group": group, "signals": {"s": s}, "verdict": v}

    # both folds agree with the split in their training data; only their test sets differ
    train = [ex(0.1, "X", "g"), ex(0.2, "X", "g"), ex(0.8, "Y", "g"), ex(0.9, "Y", "g")]
    friendly = [ex(0.6, "Y", "a"), ex(0.7, "Y", "a"), ex(0.8, "Y", "a"), ex(0.9, "Y", "a")]
    hostile = [ex(0.6, "X", "b"), ex(0.7, "X", "b"), ex(0.8, "X", "b"), ex(0.9, "Y", "b")]

    node = {"kind": "leaf", "counts": {"X": 5, "Y": 3}}
    folds = [(train, friendly), (train, hostile)]
    before, after, worst = belief._verdict(node, "s", 0.5, folds)
    assert after > before, f"the fixture must improve on average ({before} -> {after})"
    assert worst < 0, f"the fixture must hurt a group (worst {worst})"

    ok, record = belief._accepts(node, "s", 0.5, folds, index=0, require_every_fold=True)
    assert not ok, "a distinction that hurt a group was accepted anyway"
    assert record["reason"] == "helped_on_average_but_hurt_a_group", record
