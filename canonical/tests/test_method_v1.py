"""The creature chooses how to think. These tests say when that is a story.

Seventeen logs, one learning procedure, every constant in it mine. `xor` failed in every one of
them -- not because xor is hard, but because the only hypothesis space available was an axis-aligned
greedy tree with cuts applied one at a time. Nearest neighbours do not care what shape the boundary
is. So the method is not an implementation detail; it is what the creature is capable of.

Measured 2026-11-04 with the method search in place, held out on worlds it never saw: xor 0.915
against a 0.502 baseline (0.506 before), circles 0.957 against 0.720 (0.800 before), sum 0.961,
stripe 0.996, and no method adopted in the structureless worlds that were measured -- 1 of 30.

The danger here is not the search. It is the SELECTION: choosing the best of ten methods on one
grouping and believing its score. The tests below pin the discipline that stops that.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief     # noqa: E402
from canonical.runtime import method_v1 as method     # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402
from canonical.tools import worlds_v1                 # noqa: E402


def chosen_for(kind: str, seed: int = 1) -> tuple[dict, list[dict], list[dict]]:
    train, test = worlds_v1.world(kind, 90, seed), worlds_v1.world(kind, 90, seed + 1000)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    vocabulary = vocab.discover(train, folds)
    return method.choose(train, folds, vocabulary=vocabulary), train, test


def heldout_accuracy(kind: str, seed: int = 1) -> tuple[float, float, str]:
    decision, train, test = chosen_for(kind, seed)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    vocabulary = vocab.discover(train, folds)
    chosen = decision["chosen"]
    if not isinstance(chosen, method.Method):
        chosen = next(m for m in method.method_space(True) if m.name == chosen)
    rows = method._prepare(chosen, train, vocabulary)
    predictor = method.make(chosen, method.names_of(rows))(rows)
    scored = method._prepare(chosen, test, vocabulary)
    accuracy = sum(1 for ex in scored
                   if predictor.predict(ex["signals"]) == ex["verdict"]) / len(scored)
    majority = collections.Counter(ex["verdict"] for ex in train).most_common(1)[0][0]
    baseline = sum(1 for ex in test if ex["verdict"] == majority) / len(test)
    return accuracy, baseline, chosen.name


# --------------------------------------------------------------------------- the capability
def test_it_learns_xor_by_choosing_a_different_kind_of_hypothesis():
    """Seventeen logs of failure, and the cause was the hypothesis space rather than the world."""
    accuracy, baseline, name = heldout_accuracy("xor")
    assert accuracy > baseline + 0.25, f"xor still unsolved: {accuracy:.3f} vs {baseline:.3f}"
    assert "nearest" in name or "tree(depth=3)" in name, (
        f"it solved xor with {name} -- worth checking that this is not a fluke of the seed")


def test_it_learns_a_boundary_no_axis_aligned_tree_can_draw():
    accuracy, baseline, name = heldout_accuracy("circles")
    assert accuracy > baseline + 0.20, f"circles not learned: {accuracy:.3f} vs {baseline:.3f}"


def test_it_keeps_the_answers_it_already_had():
    """Widening must not cost what worked. `or` fell to its base rate when the search declined and
    the fallback was 'learn nothing' rather than the incumbent model."""
    for kind in ("and", "or", "stripe"):
        accuracy, baseline, _ = heldout_accuracy(kind)
        assert accuracy > baseline + 0.15, f"{kind} regressed: {accuracy:.3f} vs {baseline:.3f}"


def test_the_space_is_a_product_not_a_list():
    """`nearest neighbours over invented features` is a combination nobody wrote down. It exists
    because the space is crossed, and the creature picked it for xor on one seed."""
    names = [m.name for m in method.method_space(True)]
    assert any("nearest" in n and "invented" in n for n in names), "the product is not being built"
    assert any("tree(depth=3)" in n for n in names)


# --------------------------------------------------------------------------- the safety property
def test_it_does_not_adopt_a_method_in_a_world_with_no_rule():
    """A SAFETY property, with its measured rate rather than a wish.

    Measured 2026-11-04 over 40 structureless worlds: one adoption. On that world the adopted
    method scored 0.578 out of sample against a majority of 0.489 -- better, by luck, so no harm is
    demonstrated -- but the claim was not warranted and this test says so at the size it can afford.
    """
    adopted = 0
    for seed in range(12):
        decision, _, _ = chosen_for("noise", seed * 3 + 1)
        adopted += int(decision["adopted"])
    assert adopted <= 1, f"it adopted a method in {adopted} of 12 structureless worlds"


def test_a_winner_must_survive_a_grouping_it_was_not_chosen_on():
    """The selection discipline. Without it, the best of many methods always looks good."""
    decision, _, _ = chosen_for("xor")
    assert decision["adopted"]
    checks = decision["checks"]
    assert len(checks) >= 2, "no second or third grouping was examined"
    for check in checks:
        assert check["margin"] >= method.MIN_GAIN, f"a grouping disagreed: {check}"
        assert check["worst"] > 0, f"one fold got worse: {check}"
        assert check["over_incumbent"] >= method.MIN_GAIN, f"not better than the incumbent: {check}"


def test_selection_optimism_is_reported_rather_than_hidden():
    """The gap between the score that won and the score on a grouping it did not see is the honest
    measure of how much of the win was the search. It is recorded, not assumed small."""
    decision, _, _ = chosen_for("xor")
    assert "selection_optimism" in decision
    assert abs(decision["selection_optimism"]) < 0.20, (
        f"the winner lost {decision['selection_optimism']} when regrouped")


def test_an_inconclusive_search_keeps_the_incumbent_model():
    """'Nothing adopted' must not mean 'forget everything'. The incumbent is a member of the space."""
    space = [m.name for m in method.method_space(True)]
    assert "belief[incumbent]" in space
    decision, _, _ = chosen_for("stripe")
    assert "belief" in decision["chosen"] or decision["adopted"], decision["reason"]


# --------------------------------------------------------------------------- the fixture itself
def test_every_named_world_is_the_world_it_is_named():
    """`circles` was measured as 0.476 and reported as a method failure. It had never been
    measured: the probe imported a generator with no `circles` branch, which fell through to noise
    and still returned a number. A fixture that cannot silently become noise is the fix."""
    report = worlds_v1.check()
    assert "circles" in report
    assert report["circles"]["majority_share"] < 0.95
    assert set(report["circles"]["labels"]) == {"IN", "OUT"}, (
        "the circles world does not have circle labels -- it has fallen through to noise again")
    try:
        worlds_v1.world("circles_misspelled", 10, 1)
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown world name was accepted instead of raising")


def test_the_winner_must_beat_shuffled_verdicts():
    """Directly, because a guard that is only exercised indirectly is a guard nobody checks.

    Measured 2026-11-04: this null was broken in a way that looked conservative -- it scored the
    ORIGINAL verdicts thirty times, so it rejected every world including the learnable ones. It was
    found by asserting the passing case, not the failing one.
    """
    train = worlds_v1.world("and", 90, 1)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    tree = method.Method("tree", 3, "raw")
    observed = method.score(tree, train, folds)["cv"]
    assert observed > 0.75, f"the fixture is not learnable; cv={observed}"
    assert method.winner_null(tree, train, folds, observed)["passed"], (
        "a learnable world failed the null -- the null is scoring the wrong labels")

    noise = worlds_v1.world("noise", 90, 5)
    noise_folds = belief.capability_folds(noise, seed=belief.PERMUTATION_SEED)
    noise_cv = method.score(tree, noise, noise_folds)["cv"]
    verdict = method.winner_null(tree, noise, noise_folds, noise_cv)
    assert not verdict["passed"] or noise_cv <= 0.60, (
        f"chance-level structure ({noise_cv:.3f}) passed the null")


def test_the_tree_family_still_cannot_learn_xor_and_that_is_the_point():
    """A LIMITATION, not a safety property: it may never block a widening change.

    A depth-two tree CAN express xor mathematically, and I expected per-branch recursion to fix it.
    Measured 2026-11-04: it does not. Every cut at 0.5 has zero information gain on xor, so the
    greedy chooser never finds one and picks an extreme cut instead -- 0.625 on its own training
    data. The world was solved by a different hypothesis FAMILY, not by a deeper tree. That is the
    whole argument for choosing methods over tuning one.
    """
    train = worlds_v1.world("xor", 120, 3)
    predictor = method.make(method.Method("tree", 2, "raw"), method.names_of(train))(train)
    accuracy = sum(1 for ex in train
                   if predictor.predict(ex["signals"]) == ex["verdict"]) / len(train)
    assert accuracy < 0.90, (
        f"the greedy tree now learns xor ({accuracy:.3f}) -- good news, update the log rather "
        "than deleting this test")


def test_a_winner_that_does_not_beat_the_incumbent_is_not_adopted():
    """`stripe` is a world the incumbent already solves. Nothing new should be adopted there,
    however good the search looks."""
    decision, _, _ = chosen_for("stripe")
    assert not decision["adopted"], f"it replaced a working method: {decision['reason']}"
    assert decision["reason"] in {"did_not_beat_the_incumbent", "did_not_survive_regrouping",
                                  "did_not_beat_the_incumbent_when_regrouped",
                                  "not_beyond_shuffled_verdicts"}, decision["reason"]
