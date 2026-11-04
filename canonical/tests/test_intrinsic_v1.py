"""Constants the creature derives, and an intrinsic reason to keep a thought that is not yet right.

Log 19 ended on a wall with two named blockers: the algebra had no constants, so no
threshold-centred rule was spellable, and every thought had to pay immediately, so a chain of
worthless-looking steps died. This module fixes the first and measures the second honestly.

Paired tests, as the laws require: each claim below has a world where it must fail, and each
limitation is labelled as a limitation rather than a safety property, so no widening change may be
blocked by one.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import intrinsic_v1 as intrinsic   # noqa: E402
from canonical.runtime import program_v1 as program       # noqa: E402
from canonical.tools import worlds_v1                     # noqa: E402

PARITY = ("bin", "mul",
          ("bin", "mul", ("bin", "sub", ("base", "a"), ("base", "m")),
           ("bin", "sub", ("base", "b"), ("base", "m"))),
          ("bin", "sub", ("base", "c"), ("base", "m")))


def centred(rows: list[dict], value: float) -> list[dict]:
    return [{**ex, "signals": {**ex["signals"], "m": value}} for ex in rows]


def pooled_median(rows: list[dict]) -> float:
    return intrinsic.median([value for ex in rows
                             for value in (ex["signals"]["a"], ex["signals"]["b"], ex["signals"]["c"])])


# ------------------------------------------------------------------ constants are derived, not typed
def test_a_constant_is_a_property_of_the_data_not_of_the_file():
    """Shift the signal, and the derived constant shifts with it. A typed 0.5 would not move."""
    rows = worlds_v1.world("xor3", 60, 1)
    base = intrinsic.derived_constants(rows)
    shifted = [{**ex, "signals": {**ex["signals"], "a": ex["signals"]["a"] + 3.0}} for ex in rows]
    moved = intrinsic.derived_constants(shifted)
    assert set(base) == {"med_a", "med_b", "med_c"}, base
    assert abs((moved["med_a"] - base["med_a"]) - 3.0) < 1e-9, (base, moved)
    assert abs(moved["med_b"] - base["med_b"]) < 1e-9, "an untouched signal's constant moved"


def test_the_constant_is_a_median_and_not_one_lucky_sample():
    """A single row's value would be a constant too -- and would be wrong. One corrupted signal in
    the data must move the derived centre by almost nothing, because the creature needs a quantity
    it can trust, not the first number it saw.
    """
    rows = worlds_v1.world("xor3", 60, 1)
    before = intrinsic.derived_constants(rows)["med_a"]
    corrupted = [{**row, "signals": dict(row["signals"])} for row in rows]
    corrupted[0]["signals"]["a"] = 1000.0
    after = intrinsic.derived_constants(corrupted)["med_a"]
    assert abs(after - before) < 0.05, (
        f"one extreme sample moved the centre from {before:.4f} to {after:.4f}")


def test_the_parity_rule_is_spellable_without_anybody_typing_the_threshold():
    """Log 19 could not spell this at all: `vocabulary_v1` has no constants, so `a - k` did not
    exist. With the data's own pooled median it separates held-out data completely.
    """
    train, test = worlds_v1.world("xor3", 120, 1), worlds_v1.world("xor3", 120, 1001)
    centre = pooled_median(train)
    assert 0.3 < centre < 0.7, f"the derived centre is {centre}, which is not a centre"
    assert program.separability(centred(train, centre), PARITY) >= 0.95
    assert program.separability(centred(test, centre), PARITY) >= 0.95


# ------------------------------------------------------- what it now solves that it did not before
def test_one_computed_column_solves_xor_exactly():
    """Log 19: xor was 0.975 by the method space and 0.931 by nearest(k) -- never exact. With a
    derived constant, a single column is the true rule.
    """
    train, test = worlds_v1.world("xor", 120, 1), worlds_v1.world("xor", 120, 1001)
    centred_train, _ = intrinsic.with_derived_constants(train)
    centred_test, _ = intrinsic.with_derived_constants(test)
    found = intrinsic.search(centred_train, policy="objective", budget=1200, per_level=16,
                             max_size=intrinsic.MAX_SIZE)
    column, separation = intrinsic.best_column(found, centred_train)
    assert separation >= 0.99, f"best column separates at {separation:.3f}"
    assert program.separability(centred_test, column) >= 0.99, "the exact rule did not hold out"


def test_sum_is_solved_by_one_column_where_methods_reached_only_0_point_942():
    """A solved world, so the number is a boundary and not a rate."""
    train, test = worlds_v1.world("sum", 120, 1), worlds_v1.world("sum", 120, 1001)
    centred_train, _ = intrinsic.with_derived_constants(train)
    centred_test, _ = intrinsic.with_derived_constants(test)
    found = intrinsic.search(centred_train, policy="objective", budget=1200, per_level=16,
                             max_size=intrinsic.MAX_SIZE)
    column, separation = intrinsic.best_column(found, centred_train)
    assert separation >= 0.99 and program.separability(centred_test, column) >= 0.99


# ------------------------------------------------------------------------- the intrinsic signal
def test_novelty_is_a_real_signal_against_a_paired_null():
    """Same archive budget, same algebra, same survivors per level; only the ranking differs from
    picking at random. Novelty must be better than the null or it is decoration.
    """
    train = worlds_v1.world("xor3", 120, 1)
    centred_train, _ = intrinsic.with_derived_constants(train)
    armoury = {}
    for policy in ("novelty", "random"):
        found = intrinsic.search(centred_train, policy=policy, budget=1200, per_level=16,
                                 max_size=intrinsic.MAX_SIZE)
        armoury[policy] = intrinsic.best_column(found, centred_train)[1]
    assert armoury["novelty"] > armoury["random"] + 0.05, (
        f"novelty {armoury['novelty']:.3f} is not meaningfully above the random null "
        f"{armoury['random']:.3f}")


# ------------------------------------------------------------------------------------ the wall
def test_novelty_keeps_thoughts_the_answer_would_throw_away():
    """The claim is not "novelty beats random", it is "novelty values thoughts the answer does not".

    So look at what each policy KEEPS at one size. Measured 2026-11-05 at size 6 on xor3: the
    objective memory's median gain is 0.1029 and the novelty memory's is 0.0236, with ZERO overlap
    between the two sets. Novelty is not objective ranking renamed -- it is a different mind about
    what is worth holding.

    The naive form of this test -- "novelty keeps something that earns exactly nothing" -- is false:
    an optimistically-thresholded split gives almost any column a little gain, which is itself worth
    knowing.
    """
    train = worlds_v1.world("xor3", 120, 1)
    centred_train, _ = intrinsic.with_derived_constants(train)
    assert intrinsic.search(centred_train, max_size=2, budget=400)["constants_used"], (
        "the derived constants vanished from the search's own report")

    kept = {}
    for policy in ("objective", "novelty"):
        found = intrinsic.search(centred_train, policy=policy, budget=1200, per_level=16, max_size=6)
        kept[policy] = found["memory"][6]
    median = lambda rows: sorted(gain for gain, _ in rows)[len(rows) // 2]   # noqa: E731
    assert median(kept["objective"]) > 3 * median(kept["novelty"]), (
        f"objective {median(kept['objective']):.4f} vs novelty {median(kept['novelty']):.4f}: "
        "the memories are not valuing different things")
    shared = {render for _, render in kept["objective"]} & {render for _, render in kept["novelty"]}
    assert not shared, f"the two policies hold the same thoughts: {list(shared)[:2]}"


def test_no_policy_holds_a_chain_whose_every_prefix_is_at_chance():
    """A LIMITATION, not a safety property: it may never block a widening change.

    Measured 2026-11-05: the parity structure is spellable and separates at 0.992, but no policy
    holds it. Every prefix is at chance, each level keeps 16 of thousands of columns, so the chain
    is dropped long before it pays. The wall is RETENTION -- credit over intermediate thoughts --
    not ranking and not expressibility.
    """
    train = worlds_v1.world("xor3", 120, 1)
    centred_train, _ = intrinsic.with_derived_constants(train)
    centred_train = centred(centred_train, pooled_median(train))   # the one shared centre
    best = 0.0
    for policy in ("objective", "novelty", "mixed"):
        found = intrinsic.search(centred_train, policy=policy, budget=1200, per_level=16,
                                 max_size=intrinsic.MAX_SIZE)
        best = max(best, intrinsic.best_column(found, centred_train)[1])
    assert best < 0.85, f"a policy now reaches {best:.3f} on xor3 -- update the log"
    assert program.separability(centred_train, PARITY) >= 0.95, (
        "the chain got harder to spell, which is a different failure than the one recorded")


def test_the_stall_detector_fires_on_the_wrong_worlds():
    """LIMITATION of the adaptive policy, recorded because it was my attempt at self-direction.

    A deceptive world hands out small incidental gains (xor3 climbs 0.08 -> 0.26 in entropy), which
    look exactly like progress. So the detector that is supposed to say "I am not learning, try
    something else" stays quiet precisely where thinking differently was needed, and fires on the
    worlds where progress is real but bumpy.
    """
    stalled_world = worlds_v1.world("xor3", 120, 1)
    productive = worlds_v1.world("sum", 120, 1)
    stalled_train, _ = intrinsic.with_derived_constants(stalled_world)
    productive_train, _ = intrinsic.with_derived_constants(productive)
    quiet = intrinsic.search(stalled_train, policy="adaptive", budget=1200, per_level=16,
                             max_size=intrinsic.MAX_SIZE)
    noisy = intrinsic.search(productive_train, policy="adaptive", budget=1200, per_level=16,
                             max_size=intrinsic.MAX_SIZE)
    assert set(quiet["policy_by_size"].values()) == {"objective"}, quiet["policy_by_size"]
    assert "novelty" in noisy["policy_by_size"].values(), noisy["policy_by_size"]
