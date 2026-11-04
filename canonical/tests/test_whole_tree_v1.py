"""Can the model learn a rule it cannot express one cut at a time?

Measured 2026-11-04, and this is the reason the file exists: on a world whose rule is
`a > 0.5 AND b > 0.5` the model refused to split at all and scored 0.700 against a base rate of
0.750 -- worse than a one-line rule. Neither cut of a conjunction gains anything on its own, and
the gate judged cuts one at a time. A system that can only learn additive rules is not a system
that can learn, and nothing in sixteen logs had measured that.

The fix judged a whole small tree against out-of-group folds instead of judging each cut. Two
earlier attempts are recorded in the log because they failed: judging pairs with a lookahead
admitted a split in roughly a third of structureless worlds, and judging by log loss admitted
fifty-odd. The tests below pin the fix and, just as importantly, pin the noise property it must
not break.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief   # noqa: E402
from canonical.tools import worlds_v1                # noqa: E402


def world(kind: str, n: int, seed: int) -> list[dict]:
    return worlds_v1.world(kind, n, seed)


def learned(kind: str, train_seed: int = 1, test_seed: int = 51) -> tuple[float, float, dict]:
    train, test = world(kind, 90, train_seed), world(kind, 60, test_seed)
    split = int(len(train) * 0.75)
    model = belief.blank()
    belief.fit(model, train[:split], train[split:])
    return (belief.accuracy(model, test)[0], belief.majority_baseline(test), model)


# --------------------------------------------------------------------------- the capability
def test_it_learns_a_conjunction():
    """Neither cut helps alone. If this fails, the model is back to additive rules only."""
    accuracy, baseline, model = learned("and")
    assert accuracy > baseline + 0.15, (
        f"conjunction not learned: {accuracy:.3f} against a base rate of {baseline:.3f}")
    assert model["splits_accepted"] >= 2, "a conjunction is two distinctions, not one"


def test_it_learns_a_disjunction():
    """The symmetric case, and the one where the gain sits in the LOW branch rather than the high
    one -- an implementation that only looks above the cut gets the base rate here."""
    accuracy, baseline, _ = learned("or")
    assert accuracy > baseline + 0.10, (
        f"disjunction not learned: {accuracy:.3f} against {baseline:.3f}")


def test_it_keeps_learning_the_additive_case():
    """Widening must not cost what already worked."""
    accuracy, baseline, _ = learned("product")
    assert accuracy > baseline + 0.20, f"product world fell back: {accuracy:.3f} vs {baseline:.3f}"


def test_a_structure_it_admits_is_stated_in_its_own_record():
    """A two-cut tree reported as `splits_accepted: 0` beside `accepted: []` is a status label
    that does not describe the thing it labels. AGENTS.md exists to stop exactly that."""
    _, _, model = learned("and")
    assert model["splits_accepted"] == len(model["accepted"])
    assert model["splits_accepted"] > 0
    assert any(entry.get("via") == "whole_tree" for entry in model["accepted"])


# --------------------------------------------------------------------------- the safety property
def test_it_still_refuses_structure_in_a_world_with_no_rule():
    """This is the property two earlier attempts broke. Measured 2026-11-04: pair lookahead
    accepted splits in 6-7 of 20 structureless worlds, log-loss in 57 of 10. The shipped version
    accepts none, and this test is what makes that a commitment rather than a memory."""
    accepted = 0
    for trial in range(8):
        model = belief.blank()
        belief.fit(model, world("noise", 60, trial * 5))
        accepted += model["splits_accepted"]
    assert accepted == 0, f"it invented {accepted} distinctions in eight worlds with no rule"


def test_a_tree_whose_leaves_are_too_small_is_not_evidence():
    """The two structureless worlds that survived every grouping cut at 0.83 and 0.96, carving
    three or four examples into pure leaves. A leaf that small is a memorised accident."""
    train = world("noise", 60, 3)
    assert belief._leaf_too_small(train, "a", 0.98), "a far-tail cut was treated as legitimate"
    assert not belief._leaf_too_small(train, "a", 0.5), "a balanced cut was refused"


def test_a_chosen_tree_must_survive_a_different_grouping():
    """The tree is CHOSEN on one grouping, so that grouping cannot also be its alibi."""
    train = world("and", 90, 1)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    without = belief.best_small_tree(train, folds)
    with_alt = belief.best_small_tree(
        train, folds, alt_folds=belief.capability_folds(train, seed=belief.PERMUTATION_SEED + 1))
    assert without["accepted"], "a real conjunction was refused with no cross-check at all"
    assert with_alt["accepted"], "a real conjunction did not survive regrouping"
    assert "second_grouping" in with_alt


# --------------------------------------------------------------------------- a limitation, not a property
def test_xor_is_still_not_learned():
    """A LIMITATION, not a safety property: it may never block a widening change. A two-cut tree
    applies the same two cuts everywhere, and xor needs a different cut in each branch. Recorded
    so nobody reads the conjunction result as 'it learns anything'."""
    accuracy, baseline, _ = learned("xor")
    assert accuracy <= baseline + 0.10, (
        "xor is being learned now -- good news, but update the log rather than deleting this test")


def test_the_decision_rule_can_be_interrogated_directly():
    """Every branch of the acceptance rule, because a guard nobody can call is a guard nobody can
    test -- and an untested guard is where the noise gets in."""
    assert belief.judge_small_tree(0.20, 0.05) == (True, "")
    assert belief.judge_small_tree(0.001, 0.05)[1] == "no_out_of_group_improvement"
    assert belief.judge_small_tree(0.20, 0.0)[1] == "helped_on_average_but_hurt_a_group"
    assert belief.judge_small_tree(0.20, -0.10)[1] == "helped_on_average_but_hurt_a_group"


def test_a_tree_is_rejected_when_a_different_grouping_disagrees():
    """The regrouping check itself, exercised: chosen on one split of the data, then shown a
    grouping built from shuffled labels. If this still passes, the check is decoration."""
    train = world("and", 90, 1)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    rng = random.Random(9)
    labels = [ex["verdict"] for ex in train]
    rng.shuffle(labels)
    scrambled = [{"group": ex["group"], "signals": ex["signals"], "verdict": labels[i]}
                 for i, ex in enumerate(train)]
    hostile = belief.capability_folds(scrambled, seed=belief.PERMUTATION_SEED + 1)
    record = belief.best_small_tree(train, folds, alt_folds=hostile)
    assert not record["accepted"], (
        "a tree chosen on one grouping was accepted even though a scrambled grouping disagreed")


def test_a_third_grouping_is_required_by_default():
    """The default is three groupings, and the number is a parameter so this test can show the
    difference rather than assert a constant."""
    import inspect
    signature = inspect.signature(belief.best_small_tree)
    assert signature.parameters["extra_groupings"].default == 2, (
        "the default no longer asks for a third grouping")
    train = world("and", 90, 1)
    folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
    assert belief.best_small_tree(train, folds, extra_groupings=2)["accepted"]


def test_the_third_grouping_is_the_one_that_refuses_here():
    """A concrete world where two groupings agree and the third does not. Found by searching 180
    structureless worlds: six of them survive two groupings and die on the third. Without the
    third grouping this world would be recorded as a discovery."""
    data = world("noise", 60, 14)
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    alt = belief.capability_folds(data, seed=belief.PERMUTATION_SEED + 1)
    two = belief.best_small_tree(data, folds, alt_folds=alt, extra_groupings=1)
    three = belief.best_small_tree(data, folds, alt_folds=alt, extra_groupings=2)
    assert two["accepted"], "the fixture no longer survives two groupings; pick another world"
    assert not three["accepted"], "the third grouping no longer refuses this world"


def test_a_combination_must_leave_leaves_big_enough_to_be_evidence():
    """Four examples carved into a pure leaf is a coincidence with a threshold attached."""
    train = world("and", 90, 1)
    assert belief._combination_leaves_big_enough([("a", 0.5)], train)
    assert not belief._combination_leaves_big_enough([("a", 0.99)], train), \
        "a cut leaving a handful of examples was accepted as a leaf"
