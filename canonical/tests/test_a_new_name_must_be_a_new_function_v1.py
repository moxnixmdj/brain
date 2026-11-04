"""A name for an operator that already exists is not a new capability.

The previous round let a declaration supply only words and arithmetic, and induced its law
from that arithmetic. It was measured working -- `median` declared with no law answered 7,
verified -- and it was WRONG in a way that produced certified wrong answers:

    V.declare_aggregate("median", {"median"}, lambda v: min(v))
    I.answer("what is the median qty", ...)  ->  5,  verified: True

The true median of [5, 15, 7] is 7. The system reported the minimum and certified it.

WHY NO LAW COULD HAVE CAUGHT IT

min, max and median are structurally identical: permutation-invariant, positively
homogeneous, and inside their inputs. Every induced form -- within_inputs,
is_one_of_the_inputs, bounded_by_extremes -- is TRUE of min. So the induction was not
lax; it was answering a question that has no answer. NO predicate on (inputs, result) can
separate min from median, because they agree on what a single input set permits. Inventing
more values would never have found it.

WHAT DOES SEPARATE THEM

A comparison, not a predicate. `min` is already declared. An arithmetic that returns the
same number as `min` on every input is min, and giving it another name adds nothing. The
rivals are not a list somebody wrote -- they are whatever is currently declared, so this
check tightens by itself as the vocabulary grows, which is the opposite of a static rule.

This is the property that actually distinguishes a new capability from a renamed old one:
IT MUST BE POSSIBLE TO TELL THEM APART.
"""

from __future__ import annotations

import pathlib
import statistics
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import canonical.runtime.value_algebra_v1 as V  # noqa: E402


def _median(values, *_):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


@pytest.fixture(autouse=True)
def _no_leftovers():
    before = (dict(V._AGG_WORDS), dict(V._AGGREGATES))
    yield
    V._AGG_WORDS.clear()
    V._AGG_WORDS.update(before[0])
    V._AGGREGATES.clear()
    V._AGGREGATES.update(before[1])


# ---------------------------------------------------------------------------
# The hole itself, stated as the thing that must never happen again.
# ---------------------------------------------------------------------------

def test_an_operator_that_is_really_min_cannot_be_declared_as_median():
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("median", {"median"}, lambda v: min(v))
    msg = str(err.value)
    assert "SAME FUNCTION as min" in msg, msg
    assert "median" not in V.aggregate_names()


def test_an_operator_that_is_really_max_cannot_be_declared_as_median():
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("median", {"median"}, lambda v: max(v))
    assert "SAME FUNCTION as max" in str(err.value)


def test_renaming_an_existing_operator_adds_nothing():
    """The check is about the arithmetic, not about the words."""
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("total2", {"total2"}, sum)
    assert "SAME FUNCTION as sum" in str(err.value)


def test_the_refusal_names_the_rival_it_could_be_confused_with():
    """The message has to say WHICH operator, or the author cannot tell what to change."""
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("middle", {"middle"}, lambda v: min(v))
    assert "min" in str(err.value)
    assert "middle" not in V.aggregate_names()


def test_a_median_under_a_different_word_is_admitted():
    """The positive direction: the check must not refuse everything.

    `middle` is a synonym a person might really use, and a true median is not any declared
    operator, so it goes through with its law induced. A check that only ever refuses would
    pass every test in the file above and be useless.
    """
    V.declare_aggregate("middle", {"middle"}, _median)
    assert "middle" in V.aggregate_names()
    assert V.aggregate_holds("middle", [5.0, 15.0, 7.0], 7.0) is True


# ---------------------------------------------------------------------------
# It refuses the liar and admits what is genuinely new.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind,fn", [
    ("median", _median),
    ("range", lambda v: max(v) - min(v)),
    ("stdev", statistics.pstdev),
])
def test_an_arithmetic_that_is_genuinely_new_is_admitted(kind, fn):
    V.declare_aggregate(kind, {kind}, fn)
    assert kind in V.aggregate_names()
    assert V.indistinguishable_from(kind, fn) == []


def test_a_genuine_operator_outside_the_form_inventory_is_refused_and_that_is_recorded():
    """A KNOWN FALSE NEGATIVE, written down instead of discovered later.

    A product is a real operator and is not a rename of anything declared: 525 for
    [5, 15, 7] is outside its inputs, outside the total magnitude, and not one of them. So
    the discriminability check would admit it -- and the LAW check refuses it, because none
    of the five forms can be true of a product.

    That is the safe direction to be wrong in: the system declines a capability rather than
    certifying a wrong answer. What it means is that the form inventory is still a finite
    list somebody wrote, which is the next layer -- the forms have to become derivable, not
    enumerated. This test exists so that "the creature can grow its vocabulary" cannot be
    claimed again while this is true.
    """
    import math

    with pytest.raises(ValueError) as err:
        V.declare_aggregate("prod", {"prod"}, math.prod)
    assert "INDUCED" in str(err.value)
    assert "prod" not in V.aggregate_names()

    # and it is genuinely new: nothing declared agrees with it
    assert V.indistinguishable_from("prod", math.prod) == []
    # the reason is the form inventory, not the arithmetic
    assert V.induce_laws(math.prod) == ()


def test_no_declared_operator_is_indistinguishable_from_itself_under_another_name():
    """Every pair of currently declared operators must be separable."""
    names = V.aggregate_names()
    for a in names:
        for b in names:
            if a == b:
                continue
            assert not V._agrees_with(V._AGGREGATES[a]["fn"], V._AGGREGATES[b]["fn"]), \
                f"{a} and {b} are the same function"


# ---------------------------------------------------------------------------
# Why a law could not have caught it: the forms are all true of min.
# ---------------------------------------------------------------------------

def test_every_induced_law_is_true_of_min_which_is_why_the_comparison_is_needed():
    """This is the justification for the new check, asserted rather than asserted-at.

    If some induced form had rejected min, the discriminability check would be
    unnecessary. It is necessary because every form that is true of a median is also true
    of min -- the induction is healthy and still cannot help.
    """
    median_forms = V.induce_laws(_median)
    min_forms = V.induce_laws(lambda v: min(v))
    assert median_forms, "no forms induced for a median"
    for name in median_forms:
        form = V.law_from_name(name)
        for values in V._PROBE_SETS:
            assert V._holds_on(values, float(min(values)), form), name
    # and the two are indistinguishable to the forms...
    assert set(median_forms)
    # ...while the comparison sees it immediately
    assert V.indistinguishable_from("median", lambda v: min(v)) == ["min"]
    assert V.indistinguishable_from("median", _median) == []


def test_the_probes_contain_data_that_separates_the_hardest_pair():
    """min and max agree on every ascending run, so the probes must not all ascend."""
    has_unsorted = any(values != sorted(values) for values in V._PROBE_SETS)
    assert has_unsorted, "a probe set of only ascending runs cannot separate min from max"
    has_repeats = any(len(set(values)) < len(values) for values in V._PROBE_SETS)
    assert has_repeats
