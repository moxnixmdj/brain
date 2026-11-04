"""Deeper composition: what it buys, and the one thing it provably cannot reach.

Log 16 composed pairs. Log 18 chose among method families. Both left one question open: is the
SHAPE of a thought fixed, or can it grow? This module searches expressions bottom-up instead of
reading them from a list, so `mul(mul(sub(a, .5), sub(b, .5)), sub(c, .5))` is at least spellable.

Measured 2026-11-04, and the honest headline is a negative: on every world tried, deeper
composition bought NOTHING over the method space's own choice (xor3 0.842 with and without,
count3 1.000, product 0.975, circles 0.942). It does lift the weak incumbent learner (xor3
0.517 -> 0.85), which is real but is not a capability the system did not already have.

The parity result is the valuable one, and it is mechanical rather than mysterious: the exact
three-way rule exists, has size 11, and every proper part of it is at CHANCE (0.575, 0.517). A
search guided by agreement with the answer therefore prunes away the only path to it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief     # noqa: E402
from canonical.runtime import method_v1 as method     # noqa: E402
from canonical.runtime import program_v1 as program   # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402
from canonical.tools import program_probe_v1 as probe  # noqa: E402
from canonical.tools import worlds_v1                # noqa: E402


def size(expr: tuple) -> int:
    if expr[0] == "base":
        return 1
    if expr[0] == "un":
        return 1 + size(expr[2])
    return 1 + size(expr[2]) + size(expr[3])


def separability(examples: list[dict], expr: tuple) -> float:
    """Delegates: one implementation of "how well does this column separate", mutation-checked."""
    return program.separability(examples, expr)


def with_constant(kind: str, n: int = 120, seed: int = 1) -> list[dict]:
    rows = worlds_v1.world(kind, n, seed)
    for row in rows:
        row["signals"]["k"] = 0.5
    return rows


def best_method(train, test, vocabulary=None) -> float:
    best = 0.0
    for candidate in method.method_space(bool(vocabulary and vocabulary.get("entries"))):
        rows_train = method._prepare(candidate, train, vocabulary)
        rows_test = method._prepare(candidate, test, vocabulary)
        try:
            predictor = method.make(candidate, method.names_of(rows_train))(rows_train)
        except Exception:                                                # noqa: BLE001
            continue
        accuracy = sum(1 for ex in rows_test
                       if predictor.predict(ex["signals"]) == ex["verdict"]) / len(rows_test)
        best = max(best, accuracy)
    return best


# --------------------------------------------------------------------------- the shape grows
def test_it_builds_expressions_deeper_than_the_fixed_list_ever_could():
    """`vocabulary_v1` cannot produce a size-5 expression at all. If this module cannot either, it
    is the old list wearing a new name."""
    rows = with_constant("xor3")
    found = program.ranked(rows, limit=40, max_size=5)
    assert found["candidates"], "nothing was ranked at all"
    deepest = max(size(expr) for expr in found["candidates"])
    assert deepest >= 5, f"deepest candidate is size {deepest}, so nothing is nested"


def test_two_spellings_of_the_same_column_are_one_idea():
    """`add(a, b)` and `add(b, a)` are the same column. Deduping on syntax spends the budget on
    algebra's synonyms; deduping on values does not."""
    rows = with_constant("product")
    found = program.ranked(rows, limit=60, max_size=5)
    signatures = set()
    for expr in found["candidates"]:
        values = tuple(round(v, 9) if v is not None else None
                       for v in (vocab.evaluate(expr, ex["signals"]) for ex in rows))
        signatures.add(values)
        signatures.add(tuple(reversed(values))) if False else None
    assert len(signatures) == len(found["candidates"]), (
        "two candidates produced the same column of values")


# --------------------------------------------------------------------------- what it buys
def test_programs_lift_the_weak_learner():
    """Real, measurable, and not the same as a capability: the incumbent gets better."""
    rows = worlds_v1.world("xor3", 120, 1)
    folds = belief.capability_folds(rows, seed=belief.PERMUTATION_SEED)
    discovered = program.discover(rows, folds)
    assert discovered["entries"], "the parity world admitted nothing to lift anything with"
    verdict = discovered["pays_for_itself"]
    assert verdict["with"] > verdict["without"] + 0.10, verdict


def test_programs_do_not_beat_the_method_space_on_parity_or_product():
    """A LIMITATION, not a safety property: it may never block a widening change.

    Measured 2026-11-05, with the method menu held FIXED across arms -- the earlier version of this
    test handed the programs arm six extra families and called the difference a gain. Only the
    feature columns differ here.
    """
    for kind in ("xor3", "product"):
        train, test = worlds_v1.world(kind, 120, 1), worlds_v1.world(kind, 120, 2)
        discovered = program.discover(
            train, belief.capability_folds(train, seed=belief.PERMUTATION_SEED))
        plain, _ = probe._best_nested(train, test, {"entries": []})
        augmented, _ = probe._best_nested(train, test, discovered)
        assert augmented <= plain + 0.02, (
            f"{kind}: programs now add {augmented - plain:.3f} -- update the log")


def test_programs_do_beat_the_method_space_on_sum():
    """The one world in ten where composition is worth its cost, and why it is not a breakthrough.

    A computed column makes `sum` separable by a single cut, so the winning family is
    `stump[invented]` -- the same stump the system already had, reading a column it could not
    express before. Repeatable across seeds (nested lift +0.058, +0.058, +0.042, +0.075, 0.000), and
    specific: on `product` the same mechanism REGRESSES the score, which is reported, not hidden.
    """
    train, test = worlds_v1.world("sum", 120, 1), worlds_v1.world("sum", 120, 2)
    discovered = program.discover(
        train, belief.capability_folds(train, seed=belief.PERMUTATION_SEED))
    assert discovered["pays_for_itself"]["pays"], discovered["pays_for_itself"]
    plain, _ = probe._best_nested(train, test, {"entries": []})
    augmented, family = probe._best_nested(train, test, discovered)
    assert augmented > plain + 0.03, f"the sum lift did not reproduce: {augmented:.3f} vs {plain:.3f}"
    assert "invented" in family, f"the lift came from {family}, not from a computed column"


# --------------------------------------------------------------------------- the wall
def test_three_way_parity_is_expressible_but_unreachable_by_a_gain_guided_search():
    """The mechanical explanation for why parity has failed every log.

    The exact rule exists and separates the world perfectly -- but it has size 11, and every proper
    part of it is at chance, so any search that keeps what agrees with the answer prunes the only
    path to it.
    """
    rows = with_constant("xor3")
    a, b, c, k = (("base", name) for name in ("a", "b", "c", "k"))
    sub = lambda x, y: ("bin", "sub", x, y)                            # noqa: E731
    mul = lambda x, y: ("bin", "mul", x, y)                            # noqa: E731
    rule = mul(mul(sub(a, k), sub(b, k)), sub(c, k))

    assert size(rule) == 11, f"the exact rule is size {size(rule)}"
    assert separability(rows, rule) > 0.99, "the exact rule does not separate the world"

    centred = separability(rows, sub(a, k))
    pair = separability(rows, mul(sub(a, k), sub(b, k)))
    assert centred < 0.70 and pair < 0.70, (
        f"a sub-expression now predicts parity ({centred:.3f}, {pair:.3f}) -- update the log")

    found = program.ranked(rows, limit=60, max_size=7)
    best = max((separability(rows, expr) for expr in found["candidates"]), default=0.0)
    assert best < 0.90, f"a size<=7 gain-guided search found parity ({best:.3f}) -- update the log"


def test_a_program_that_changes_nothing_is_set_aside():
    """Log 16's doctrine at this layer: passing your own gate is not paying for yourself.

    `count3` is the fixture because computed senses DO pass the out-of-group gate there and still
    make the model worse: 0.908 with them, 1.000 without. A world where the gates reject everything
    (`noise`) never reaches this check -- with `noise` nothing is set aside because nothing is
    admitted -- which is why the paying-check needs a world that gets that far.
    """
    rows = worlds_v1.world("count3", 120, 1)
    folds = belief.capability_folds(rows, seed=belief.PERMUTATION_SEED)
    discovered = program.discover(rows, folds)
    assert not discovered["pays_for_itself"]["pays"], discovered["pays_for_itself"]
    assert not discovered["entries"], "senses that change nothing were kept"
    assert discovered["set_aside"], "it dropped them without recording that it had"

    noise = worlds_v1.world("noise", 120, 5)
    quiet = program.discover(noise, belief.capability_folds(noise, seed=belief.PERMUTATION_SEED))
    assert not quiet["entries"], "a structureless world kept computed senses"


def test_the_record_has_one_shape_whether_or_not_a_program_pays():
    """Measured 2026-11-04: `set_aside` was only created on the failing branch, so reading it on a
    world where programs worked raised KeyError. A verdict must not change the schema of its own
    record -- otherwise `describe()` works on the worlds that fail and crashes on the ones that
    don't, which is exactly the wrong way round.
    """
    shapes = {}
    for world, expected in (("and", True), ("count3", False)):
        rows = worlds_v1.world(world, 120, 1)
        discovered = program.discover(
            rows, belief.capability_folds(rows, seed=belief.PERMUTATION_SEED))
        assert discovered["pays_for_itself"]["pays"] is expected, (world, discovered["pays_for_itself"])
        shapes[world] = set(discovered)
        described = program.describe(discovered)
        assert described["deepest"] >= 1 or discovered["set_aside"], (
            f"{world} kept nothing and set nothing aside, so there is nothing to describe")
        assert described["admitted"] or described["set_aside"], f"{world} described itself as empty"
    assert shapes["and"] == shapes["count3"], f"shape depends on the verdict: {shapes}"


def test_adding_a_world_cannot_silently_renumber_the_old_ones():
    """Measured 2026-11-05: giving `worlds_v1` a third signal drew `rng.random()` for EVERY world,
    burning one draw per row and renumbering every two-signal fixture earlier logs were measured on.
    Two committed tests failed. Nothing asserted the old worlds' values, so a fixture could move
    under a measurement and look like a change in the thing being measured.

    These fingerprints are the committed values. If they change, a log's numbers are stale -- that
    is a fact worth failing on, not a tolerance to widen.
    """
    import hashlib
    import json

    frozen = {"and": "bba68ac521317020", "xor": "cca1c8027514cf50",
              "circles": "5317bd6f2293f9f0", "noise": "8cae0198a42d6df4"}
    for kind, digest in frozen.items():
        rows = worlds_v1.world(kind, 20, 1)
        assert hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16] == digest, (
            f"{kind} changed under the measurements -- every logged number for it is stale")
        assert set(rows[0]["signals"]) == {"a", "b"}, f"{kind} gained or lost a signal"
    for kind in ("xor3", "count3"):
        assert set(worlds_v1.world(kind, 5, 1)[0]["signals"]) == {"a", "b", "c"}


def test_the_three_signal_worlds_have_three_signals():
    """The fixture property that made this measurement possible at all."""
    rows = worlds_v1.world("xor3", 40, 1)
    assert set(rows[0]["signals"]) == {"a", "b", "c"}, rows[0]["signals"].keys()
    labels = {row["verdict"] for row in rows}
    assert len(labels) == 2, labels
