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


def test_a_genuine_operator_outside_the_named_forms_is_now_declarable():
    """The limitation recorded last round is GONE, and this asserts that it is.

    A product used to be refused: every law form was one of five I wrote, and none is true
    of a product. The forms are now SYNTHESISED from relations between features of
    (inputs, result), so an operator whose law is not any sentence I thought of can still be
    declared. Recording the limit in a test is what made it checkable; this is the same test
    flipped once the limit was removed.
    """
    import math

    V.declare_aggregate("prod", {"prod"}, math.prod)
    assert "prod" in V.aggregate_names()
    assert V._AGGREGATES["prod"]["laws"]
    assert V.indistinguishable_from("prod", math.prod) == []
    assert math.prod([5.0, 15.0, 7.0]) == pytest.approx(525)

    # AND IT IS HONEST ABOUT HOW WELL IT CAN BE CHECKED. A product's strongest true law
    # excludes only about a third of nearby wrong values; calling that "checked" without
    # saying so would be the overstatement this project keeps having to retract.
    strength = V.law_strength(math.prod, V._AGGREGATES["prod"]["laws"])
    assert strength["grade"] in ("WEAK", "MODERATE"), strength


# ---------------------------------------------------------------------------
# Why a law could not have caught it: the forms are all true of min.
# ---------------------------------------------------------------------------

def test_the_written_forms_cannot_separate_median_from_min_but_a_synthesised_one_can():
    """What this round changed about the justification for the comparison check.

    The comparison check was introduced because EVERY law true of a median was also true of
    min -- bounds cannot see order. That is still true of the two bound forms. It is NOT
    true of the synthesised form `below ~= above`: min has nothing below it, so the form is
    false of min on most probes, and it really can tell the two apart.

    So the comparison is no longer the ONLY thing separating them, and this test says
    exactly which law does it rather than repeating a claim that has stopped being true.
    """
    median_laws = [V.resolve_law(entry) for entry in V.induce_laws(_median)]
    bound_forms = [law for law in median_laws if law.__name__ in
                   ("_form_within_inputs", "_form_bounded_by_extremes")]
    assert bound_forms, "expected the bound forms to be induced for a median"
    for law in bound_forms:
        for values in V._PROBE_SETS:
            assert law(list(values), float(min(values))) is True, law.__name__

    order_forms = [law for law in median_laws if getattr(law, "_source", None) ==
                   ("below", "~=", "above")]
    assert order_forms, "the order law was not induced for a median"
    disagreeing = [values for values in V._PROBE_SETS
                   if order_forms[0](list(values), float(min(values))) is False]
    assert disagreeing, "the order law must be false of min, or it separates nothing"

    # the comparison check still exists and still catches the case a law cannot
    assert V.indistinguishable_from("median", lambda v: min(v)) == ["min"]
    assert V.indistinguishable_from("median", _median) == []


def test_the_probes_contain_data_that_separates_the_hardest_pair():
    """min and max agree on every ascending run, so the probes must not all ascend."""
    has_unsorted = any(values != sorted(values) for values in V._PROBE_SETS)
    assert has_unsorted, "a probe set of only ascending runs cannot separate min from max"
    has_repeats = any(len(set(values)) < len(values) for values in V._PROBE_SETS)
    assert has_repeats
