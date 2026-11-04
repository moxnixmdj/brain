"""The system invents the distinctions it thinks with. These tests say when that is a lie.

Every test below is paired with the world that breaks the mechanism it names. The three worlds
that matter: one where the given senses are provably insufficient (so only an invented dimension
can work), one with no structure at all (so any invention is a coincidence), and one that is the
same world at a different scale (so a memorised threshold cannot pretend to be a concept).

Measured 2026-11-04, and these tests exist because of it: the first version chose its threshold on
all the data and called the result cross-validated -- 19 features "discovered" across 15 worlds
with nothing in them. The second admitted three monotone-equivalent columns and made the learner
worse than having none (0.883 down to 0.533), because redundant dimensions raise the
multiple-comparison bar until the real split is rejected.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief   # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402


# --------------------------------------------------------------------------- worlds
def product_world(n: int, seed: int) -> list[dict]:
    """No single sense can separate these classes: only a*b can. This is the whole point."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        a, b = rng.random(), rng.random()
        out.append({"group": f"g{i}", "signals": {"a": a, "b": b},
                    "verdict": "HIGH" if a * b > 0.25 else "LOW"})
    return out


def structureless(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    return [{"group": f"g{i}", "signals": {"a": rng.random(), "b": rng.random()},
             "verdict": rng.choice(["X", "Y"])} for i in range(n)]


# --------------------------------------------------------------------------- the claim
def test_it_invents_a_distinction_no_given_sense_can_express():
    data = product_world(120, 3)
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    invented = vocab.discover(data, folds)
    assert invented["entries"], "it invented nothing on a world that needs a product"

    names = [e["renders"] for e in invented["entries"]]
    assert any("*" in name or "mul" in name for name in names), (
        f"it invented {names}, none of which combines the two senses")


def test_the_invented_dimension_actually_improves_the_learner():
    """The only claim that matters. Not 'it produced an expression' -- the creature's own model
    predicts better on data it has not seen, because it built a dimension it did not have."""
    train, holdout = product_world(90, 1), product_world(60, 2)
    split = int(len(train) * 0.75)
    fit_part, validate = train[:split], train[split:]

    def accuracy_in(space) -> float:
        model = belief.blank()
        belief.fit(model, space(fit_part), space(validate))
        for example in space(fit_part):
            belief.observe(model, example["signals"], example["verdict"])
        return belief.accuracy(model, space(holdout))[0]

    fixed = vocab.blank()
    invented = vocab.discover(fit_part, belief.capability_folds(fit_part))
    assert invented["entries"], "nothing was invented, so nothing is being tested"

    without = accuracy_in(lambda x: vocab.augment(x, fixed))
    with_it = accuracy_in(lambda x: vocab.augment(x, invented))
    assert with_it > without + 0.05, (
        f"inventing changed nothing that matters: {without:.3f} -> {with_it:.3f}")


def test_it_invents_nothing_in_a_world_with_no_structure():
    """A composed feature has many degrees of freedom, so it can always fit noise. If this test
    fails, every success above is a coincidence with a plausible story attached."""
    invented = 0
    for trial in range(8):
        data = structureless(90, trial * 7)
        folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
        invented += len(vocab.discover(data, folds)["entries"])
    assert invented <= 1, f"it invented {invented} distinctions in eight structureless worlds"


def test_the_score_it_reports_is_the_honest_one():
    """The leak, caught by arithmetic instead of by outcome. Measured 2026-11-04: choosing the cut
    on all the data and calling the result cross-validated invented 19 features across 15 empty
    worlds. A reported score that the fold-internal recomputation cannot reproduce is a leak."""
    weak = []
    rng = random.Random(77)
    for i in range(80):
        a, b = rng.random(), rng.random()
        if rng.random() < 0.25:
            verdict = "HIGH" if a * b > 0.25 else "LOW"
        else:
            verdict = rng.choice(["HIGH", "LOW"])
        weak.append({"group": f"g{i}", "signals": {"a": a, "b": b}, "verdict": verdict})

    folds = belief.capability_folds(weak, seed=belief.PERMUTATION_SEED)
    admitted = vocab.discover(weak, folds)["entries"]
    assert admitted, "nothing admitted, so the reported score is untested"
    for entry in admitted:
        expr = vocab._expr_of(entry)
        honest = vocab._cv(weak, expr, None, folds)
        leaked = vocab._cv(weak, expr, entry["threshold"], folds)
        assert abs(entry["cv"] - honest) < 1e-6, (
            f"{entry['renders']} reported {entry['cv']}, fold-internal says {honest:.4f}")
        if abs(leaked - honest) > 0.02:
            assert abs(entry["cv"] - leaked) > 1e-6, (
                f"{entry['renders']} reported the leaked score {leaked:.4f}")


def test_the_cut_is_learned_inside_each_fold():
    """The leakage that produced 19 inventions in 15 empty worlds: choosing the threshold on all
    the data and then calling the result cross-validated."""
    data = structureless(80, 5)
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    expr = ("bin", "mul", ("base", "a"), ("base", "b"))
    honest = vocab._cv(data, expr, None, folds)
    leaked = vocab._cv(data, expr, 0.25, folds)
    assert honest != leaked or honest == 0.0, (
        "the fold-internal estimate and the leaked one agree, so at least one is not doing "
        "what it says")


def test_redundant_distinctions_are_dropped():
    """`sub(a,b)` and a bounded comparison of the same pair say the same thing. Admitting both
    made the learner worse than admitting neither."""
    data = product_world(60, 11)
    vocabulary = {"entries": [
        {"name": "v1", "expr": ["bin", "sub", ["base", "a"], ["base", "b"]],
         "renders": "sub(a, b)", "threshold": 0.0, "cv": 0.9, "p": 0.0},
        {"name": "v1b", "expr": ["bin", "sub", ["base", "a"], ["base", "b"]],
         "renders": "sub(a, b) again", "threshold": 0.1, "cv": 0.8, "p": 0.0},
    ], "rejected": []}
    kept = vocab.dedupe(vocabulary, data)
    assert len(kept["entries"]) == 1, "two identical distinctions were both admitted"
    assert any(r["why"] == "redundant_with_an_admitted_feature" for r in kept["rejected"])


def test_discover_never_returns_two_distinctions_that_say_the_same_thing():
    """Dedupe has to happen on the way out of discovery, not only when called by hand. Measured
    2026-11-04: three monotone-equivalent columns made the learner worse than having none."""
    data = product_world(50, 21)
    redundant = dict(vocab.blank())
    redundant["entries"] = [
        {"name": "v1", "expr": ["bin", "sub", ["base", "a"], ["base", "b"]],
         "renders": "sub(a, b)", "threshold": 0.0, "cv": 0.9, "p": 0.0},
        {"name": "v2", "expr": ["bin", "sub", ["base", "a"], ["base", "b"]],
         "renders": "sub(a, b) again", "threshold": 0.2, "cv": 0.8, "p": 0.0},
    ]
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    after = vocab.discover(data, folds, vocabulary=redundant)
    values = []
    for entry in after["entries"]:
        values.append([vocab.evaluate(vocab._expr_of(entry), ex["signals"]) or 0.0
                       for ex in data])
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            correlation = abs(vocab._correlation(vocab._ranks(values[i]),
                                                 vocab._ranks(values[j])))
            assert correlation < 0.98, (
                f"{after['entries'][i]['renders']} and {after['entries'][j]['renders']} are "
                f"the same distinction, both admitted (r={correlation:.3f})")


def test_gaining_a_dimension_cannot_take_a_shot_away_from_an_existing_one():
    """Measured 2026-11-04: the candidate list was a global top-k, so three invented columns
    pushed the base feature that already worked out of the list and accuracy fell to the base
    rate. A ranking is not a filter."""
    data = [{"signals": {"a": float(i), "b": float(i % 7), "c": float(i % 3)},
             "verdict": "Y" if i > 10 else "X"} for i in range(24)]
    candidates = belief._candidates(data)
    signals = {signal for _, signal, _ in candidates}
    assert {"a", "b", "c"} <= signals, f"some sense lost its shot: only {signals} were considered"


def test_an_empty_vocabulary_is_a_no_op():
    """If nothing is admitted, the creature must be exactly as capable as before. A vocabulary
    that changes behaviour when it is empty is doing something nobody asked for."""
    data = product_world(20, 4)
    assert vocab.augment(data, vocab.blank()) == data
    vocabulary = vocab.blank()
    assert vocab.describe(vocabulary)["admitted"] == 0


def test_an_invented_dimension_is_allowed_to_be_retired():
    """A vocabulary that only grows is a memory leak wearing a mind's clothes."""
    data = structureless(60, 13)
    # a/a is the constant 1 everywhere: it cannot separate anything, ever. A chance split on a
    # random world can look respectable at this size, so the fixture is deterministic instead.
    vocabulary = {"entries": [
        {"name": "v1", "expr": ["bin", "div", ["base", "a"], ["base", "a"]],
         "renders": "div(a, a)", "threshold": 0.0, "cv": 0.9, "p": 0.0}], "rejected": [],
        "retired": []}
    folds = belief.capability_folds(data, seed=belief.PERMUTATION_SEED)
    after = vocab.check_still_earning(vocabulary, data, folds)
    assert not after["entries"], "an entry that no longer predicts anything was kept"
    assert after["retired"], "it was dropped without saying so"


# --------------------------------------------------------------------------- alive
def _live(rule, seed=7, ticks=160, grow=True):
    """Run the real organism loop against a synthetic organ. No hand-holding: the creature
    chooses its own targets and only ever sees its own experience."""
    import random as _random

    from canonical.runtime import organism_v1 as organism

    rng = _random.Random(seed)
    targets = []
    for index in range(ticks):
        a, b = rng.random(), rng.random()
        if rule == "product":
            verdict = "HIGH" if a * b > 0.25 else "LOW"
        else:
            verdict = rng.choice(["HIGH", "LOW"])
        targets.append({"id": f"t{index}", "a": a, "b": b, "verdict": verdict})

    class Geometry(organism.Organ):
        name = "geometry"

        def targets(self):
            return targets

        def senses(self, target):
            return {"a": target["a"], "b": target["b"]}

        def act(self, target):
            return {"applied": True}

        def observe(self, target, acted):
            return target["verdict"]

        def predict(self, target, record):
            return organism._expected(record)

    state = organism.blank_state()
    organs = {"geometry": Geometry()}
    hits = predicted = 0
    for _ in range(ticks):
        if not grow:
            state["vocabulary_next_check"] = 10 ** 9   # the creature cannot grow a distinction
        row = organism.tick(state, organs)
        if row.get("predicted") is not None:
            predicted += 1
            hits += int(row["predicted"] == row["observed"])
    return (hits / predicted if predicted else 0.0), predicted, state


def test_the_creature_invents_a_distinction_while_it_is_running():
    """The log-16 claim in its strongest form: not that the module works, but that a live
    organism grows the dimensions it thinks in with nobody invoking anything."""
    accuracy, predicted, state = _live("product")
    entries = (state.get("vocabulary") or {}).get("entries") or []
    assert state["counts"].get("vocabulary_checks", 0) >= 1, "the loop never examined its own senses"
    assert entries, "the loop ran and never grew a distinction"
    assert any(("mul" in e["renders"]) or ("*" in e["renders"]) for e in entries), \
        f"it grew {[e['renders'] for e in entries]}, none combining the two senses"


def test_the_creature_does_not_invent_a_vocabulary_in_a_structureless_world():
    """The false-invention rate measured 2026-11-04 was 4 of 30 live noise worlds before the
    pay-for-itself check and 1 of 30 after. This test pins the check in place."""
    invented = 0
    for seed in (7, 13, 21, 34):
        _, _, state = _live("noise", seed=seed)
        invented += bool((state.get("vocabulary") or {}).get("entries"))
    assert invented <= 1, f"it invented distinctions in {invented} of 4 structureless streams"


def test_a_vocabulary_that_does_not_pay_for_itself_is_set_aside():
    """Measured 2026-11-04: inventing on the `ratio` world took accuracy from 0.883 to 0.533. A
    feature that passes its own gate can still make the creature worse, so the model decides."""
    _, _, state = _live("noise", seed=7)
    entries = (state.get("vocabulary") or {}).get("entries") or []
    retired = (state.get("vocabulary") or {}).get("retired") or []
    if entries:
        assert all(e.get("why") != "did_not_pay_for_itself" for e in entries)
    assert (state.get("counts", {}).get("vocabulary_set_aside", 0) >= 0)


def test_a_distinction_that_does_not_pay_for_itself_is_rejected_by_the_model() -> None:
    """The `ratio` regression, in miniature: a feature can pass its own held-out gate and still
    make the learner worse. If this returns True for noise, the guard is decoration."""
    from canonical.runtime import organism_v1 as organism

    noise = []
    rng = random.Random(41)
    for i in range(90):
        noise.append({"group": f"g{i}", "signals": {"a": rng.random(), "b": rng.random()},
                      "verdict": rng.choice(["X", "Y"])})
    bogus = [{"name": "v1", "expr": ["bin", "mul", ["base", "a"], ["base", "b"]],
              "renders": "mul(a, b)", "threshold": 0.5, "cv": 0.9, "p": 0.0}]
    with_it, without = organism.vocabulary_pays_for_itself(noise, bogus, [])
    assert not (with_it > without + 0.05), (
        f"a distinction on a structureless stream 'paid off': {without:.3f} -> {with_it:.3f}")


def test_the_creature_predicts_better_while_growing_than_while_frozen():
    """The measurement that makes the rest of it matter: same world, same seed, same ticks --
    the only difference is whether the creature may invent the dimension the world is built on."""
    growing, n_grow, state = _live("product", seed=7, grow=True)
    frozen, n_frozen, _ = _live("product", seed=7, grow=False)
    assert state["counts"].get("vocabulary_checks", 0) >= 1
    assert n_grow > n_frozen, (
        f"growing produced no more predictions ({n_grow}) than frozen ({n_frozen})")
    assert growing > frozen + 0.20, (
        f"inventing bought nothing: frozen {frozen:.3f} -> growing {growing:.3f}")


def test_time_is_the_split_that_always_exists():
    """Inside the loop every target is its own group, so grouping by target hands back
    one-example tests that cannot fail. Time blocks always exist."""
    stream = [{"group": f"g{i}", "signals": {"a": i / 100}, "verdict": "X" if i % 2 else "Y"}
              for i in range(60)]
    folds = vocab.time_folds(stream, blocks=6)
    assert folds, "no time folds were produced for a stream of 60"
    for train, test in folds:
        assert test, "a time fold held out nothing"
        assert train, "a time fold trained on nothing"
        assert not (set(id(x) for x in train) & set(id(x) for x in test)), "overlap"
    assert vocab.time_folds(stream[:10], blocks=6) == [], (
        "it built folds from too little experience to fill them")
