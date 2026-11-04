"""Laws are synthesised, not typed.

Every law in this system was a form I wrote: within_inputs, bounded_by_extremes,
is_one_of_the_inputs, is_a_whole_number, is_the_row_count. Five sentences. They were
measured -- the arithmetic decided which survived -- but the INVENTORY was mine, so two
things were true that should not have been:

  1. An operator whose honest law was not one of my five could not be declared at all.
     `prod` was refused every round, though a product is genuinely new (525 for [5, 15, 7]
     is outside its inputs and outside their total magnitude).

  2. The five were also WEAK. All of them are bounds, and a bound cannot see order. The
     induced law for a median accepted 15 as the median of [5, 15, 7], because 15 is an
     input -- and this was recorded in the previous round as a permanent limitation.

Both are consequences of the same thing: a law was a sentence somebody thought of. A law is
now a RELATION between measurable features of (inputs, result) -- how many inputs lie below
the result, how many above, the count, the sum, the extremes, the mean -- and the relations
are generated rather than chosen. The arithmetic still decides which are true.

The result that matters: `below ~= above` is what makes a number the middle one, it is false
of min, and no bound form could ever have said it.
"""

from __future__ import annotations

import math
import pathlib
import statistics
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import canonical.runtime.value_algebra_v1 as V  # noqa: E402
from canonical.runtime import law_synthesis_v1 as LS  # noqa: E402


def _median(values, *_):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


@pytest.fixture(autouse=True)
def _clean():
    before = (dict(V._AGG_WORDS), dict(V._AGGREGATES))
    yield
    V._AGG_WORDS.clear()
    V._AGG_WORDS.update(before[0])
    V._AGGREGATES.clear()
    V._AGGREGATES.update(before[1])


# ---------------------------------------------------------------------------
# The space of forms is generated, not listed.
# ---------------------------------------------------------------------------

def test_forms_are_generated_from_features_rather_than_enumerated_by_hand():
    generated = list(LS.candidate_forms())
    assert len(generated) > 500, "the space should be far larger than a hand-written list"
    # nothing in the space names an operator
    assert all(hasattr(f, "_source") and len(f._source) == 3 for f in generated)


def test_each_operator_gets_a_law_that_is_true_of_it():
    for fn in (sum, statistics.mean, max, min, statistics.median, math.prod):
        rows = LS.synthesise(fn, V._PROBE_SETS)
        assert rows, f"no true form found for {fn}"
        strongest = rows[0]["form"]
        for values in V._PROBE_SETS:
            assert strongest(list(values), float(fn(list(values)))) is True


# ---------------------------------------------------------------------------
# The result the whole round turns on: order is expressible.
# ---------------------------------------------------------------------------

def test_the_median_law_is_the_order_relation_and_it_is_not_a_bound():
    rows = LS.synthesise(_median, V._PROBE_SETS)
    sources = [r["source"] for r in rows]
    assert ("below", "~=", "above") in sources, sources

    order = next(r["form"] for r in rows if r["source"] == ("below", "~=", "above"))
    values = [5.0, 15.0, 7.0]
    assert order(values, 7.0) is True
    # THE FAILURE RECORDED LAST ROUND: 15 was accepted, because every form was a bound.
    assert order(values, 15.0) is False
    assert order(values, 5.0) is False
    assert order(values, 999.0) is False


def test_the_order_law_is_false_of_min_which_is_how_median_is_told_apart():
    """A bound cannot separate median from min. This can, and that is not a small thing.

    min has nothing below it, so below == above is false for min on most data. The previous
    round's justification for the comparison check -- that every law true of a median is
    also true of min -- has stopped being true for this law, and the test says which.
    """
    order = next(r["form"] for r in LS.synthesise(_median, V._PROBE_SETS)
                 if r["source"] == ("below", "~=", "above"))
    false_for_min = [v for v in V._PROBE_SETS if order(list(v), float(min(v))) is False]
    assert false_for_min, "the order law would separate nothing"


def test_honest_medians_are_never_rejected_by_the_synthesised_law():
    """A law that rejects correct answers is worse than no law at all."""
    order = next(r["form"] for r in LS.synthesise(_median, V._PROBE_SETS)
                 if r["source"] == ("below", "~=", "above"))
    for values in ([5.0, 15.0, 7.0], [2.0, 4.0, 6.0, 8.0], [-3.0, -1.0, -7.0],
                   [1.0, 1.0, 4.0], [0.5, 2.25, 9.0, 1.75], [1.0, 2.0, 3.0],
                   [10.0, 20.0], [7.0]):
        assert order(list(values), float(statistics.median(values))) is True, values


# ---------------------------------------------------------------------------
# The operator that was refused because no sentence of mine fitted it.
# ---------------------------------------------------------------------------

def test_a_product_can_now_be_declared_and_reports_how_weakly_it_is_checked():
    """Refusing a genuine operator was a capability limit; calling it checked would be a lie.

    A product admits only weak laws -- its strongest true form excludes about a third of
    nearby wrong values, against 95% for a sum. It is declarable now, and its grade says
    WEAK. Both halves of that are the point.
    """
    V.declare_aggregate("prod", {"prod"}, math.prod)
    assert "prod" in V.aggregate_names()
    assert V.aggregate_holds("prod", [5.0, 15.0, 7.0], 525.0) is True
    assert V.aggregate_holds("prod", [5.0, 15.0, 7.0], -999.0) is False

    strength = V.law_strength(math.prod, V._AGGREGATES["prod"]["laws"])
    assert strength["grade"] in ("WEAK", "MODERATE"), strength
    assert strength["rejected_fraction"] < 0.8


def test_a_sum_gets_an_exact_law_rather_than_the_bound_i_wrote():
    """`sum == r` is true and exact; the bound n*min..n*max was a weakening of it."""
    rows = LS.synthesise(sum, V._PROBE_SETS)
    assert rows[0]["source"] == ("sum", "==", "r"), rows[0]["source"]
    strongest = rows[0]["form"]
    assert strongest([5.0, 15.0, 7.0], 27.0) is True
    assert strongest([5.0, 15.0, 7.0], 28.0) is False


# ---------------------------------------------------------------------------
# Nothing became unchecked by being synthesised.
# ---------------------------------------------------------------------------

def test_a_constant_still_gets_no_law():
    for c in (0.0, 1.0, 999.0):
        assert LS.synthesise(lambda v, c=c: c, V._PROBE_SETS) == []


def test_synthesised_forms_that_say_nothing_are_discarded():
    """True and inert is the vacuity this layer exists to refuse."""
    rows = LS.synthesise(sum, V._PROBE_SETS)
    for row in rows:
        assert row["excluded"] > 0.0, row["source"]


def test_every_declared_operator_still_reports_a_grade():
    for name in V.aggregate_names():
        spec = V._AGGREGATES[name]
        strength = V.law_strength(spec["fn"], spec["laws"])
        assert strength["grade"] in ("STRONG", "MODERATE", "WEAK", "NONE"), name
        assert strength["grade"] != "NONE", f"{name} has laws that check nothing"
