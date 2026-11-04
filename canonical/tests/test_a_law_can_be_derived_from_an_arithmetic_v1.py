"""A law can be DERIVED from an arithmetic instead of written for it.

Every law in the previous round was hand-written: I decided that a sum is bounded by
n*min and n*max, that a mean stays inside its inputs, that a count equals its row count.
So the vocabulary was static in the way that matters -- anyone could declare a new
operator, but only a human could say what would make it wrong. The system could accept a
check; it could not produce one.

The laws are now stated as FORMS that take the arithmetic and the data, with no mention of
any operator by name. Which forms are true of a given arithmetic is MEASURED by running
that arithmetic, and the strongest survivors become its law. This file asserts what that
derivation produces for operators nobody wrote a law for, and -- just as important -- what
it refuses.

The boundary is honest and is asserted here too: an induced law can only state what holds
for every input the probes tried, so for some operators it is strictly weaker than a law a
human who knew the definition could write. A median's induced law accepts its minimum and
its maximum, because both really are inputs.
"""

from __future__ import annotations

import math
import pathlib
import statistics
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import canonical.runtime.value_algebra_v1 as V  # noqa: E402

PROBES = [5.0, 15.0, 7.0]


def _median(values, *_):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


# ---------------------------------------------------------------------------
# The derivation produces the right law for each operator, knowing no names.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn,expected", [
    (sum, "bounded_by_extremes"),
    (statistics.mean, "within_inputs"),
    (max, "is_one_of_the_inputs"),
    (min, "is_one_of_the_inputs"),
    (lambda v: max(v) - min(v), "bounded_by_extremes"),
    (statistics.pstdev, "bounded_by_extremes"),
])
def test_the_induction_finds_a_true_law_for_an_operator_it_was_never_told_about(fn, expected):
    induced = V.induce_laws(fn)
    named = [e for e in induced if isinstance(e, str)]
    assert expected in named, f"{expected} not among named forms {named}"
    # and every induced law is actually true of the arithmetic on the probes
    for values in V._PROBE_SETS:
        honest = fn(list(values))
        for entry in induced:
            law = V.resolve_law(entry)
            assert law(list(values), honest) is True, (entry, values)


def test_sum_and_count_get_different_laws_from_the_same_mechanism():
    """No branch anywhere says "if this is a count". The arithmetic decides."""
    assert V.induce_laws(sum) != V.induce_laws(lambda v: len(v))
    assert "is_the_row_count" in V.induce_laws(lambda v: len(v))


# ---------------------------------------------------------------------------
# An arithmetic that is not tied to its data must not get a law at all.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn", [
    lambda v: 999.0,
    lambda v: 0.0,
    lambda v: 1.0,
    lambda v: 0.0 * len(v),
])
def test_a_constant_arithmetic_gets_no_law_and_cannot_be_declared(fn):
    """The liar that nearly got through.

    `lambda v: 0.0` passed a falsifiability test that invented wrong values: |0| is within
    the total magnitude, and the form rejected 1000, so it looked like a check. It was not
    one -- the value it gives for any input is the same, so no statement about a single
    input can tell it from a correct answer. The test has to be CROSS-DATA: does the law
    reject the honest answer computed from DIFFERENT rows?

    A constant gives the same answer on every probe, so nothing separates it, and the
    declaration is refused with nothing registered.
    """
    assert V.induce_laws(fn) == ()
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("sneaky", {"sneaky"}, fn)
    assert "law" in str(err.value).lower()
    assert "sneaky" not in V.aggregate_names()
    assert V._AGGREGATES.get("sneaky") is None


def test_a_declaration_with_no_law_induces_one_rather_than_being_refused():
    """The capability this file exists for: declare words and arithmetic, get a check."""
    V.declare_aggregate("median", {"median", "middle"}, _median)
    try:
        assert V.aggregate_names().__contains__("median")
        assert V._AGGREGATES["median"]["laws"], "no law was induced"
        honest = _median(PROBES)
        assert honest == 7
        assert V.aggregate_holds("median", PROBES, honest) is True
        assert V.aggregate_holds("median", PROBES, 999.0) is False
        assert V.aggregate_holds("median", PROBES, -1.0) is False
    finally:
        V._AGG_WORDS.pop("median", None)
        V._AGGREGATES.pop("median", None)


# ---------------------------------------------------------------------------
# The honest boundary: an induced law is weaker than a written one, and says so.
# ---------------------------------------------------------------------------

def test_an_induced_law_is_now_stronger_than_the_bounds_it_started_with():
    """This test used to record a weakness. The weakness is gone, and it says so.

    It asserted that a median's induced law accepted its own minimum and maximum, because
    every form was a BOUND and both are inputs. The law is now synthesised from relations
    between features, and the strongest true form for a median is `below ~= above` -- the
    order relation that makes a number the middle one. min has nothing below it, so a
    median's law now rejects its own minimum and maximum.

    What has NOT changed: the law is a check on values, not a proof of the arithmetic. A
    value that genuinely balances the data is admitted, and that is recorded here too.
    """
    induced = [V.resolve_law(e) for e in V.induce_laws(_median)]
    assert induced

    def holds(result):
        return all(law(list(PROBES), float(result)) for law in induced)

    assert holds(7.0) is True            # the median
    assert holds(5.0) is False           # was True when the laws were only bounds
    assert holds(15.0) is False          # was True
    assert holds(999.0) is False
    # the honest limit: 9 balances [5, 15, 7] as well as 7 does
    assert holds(9.0) is True
