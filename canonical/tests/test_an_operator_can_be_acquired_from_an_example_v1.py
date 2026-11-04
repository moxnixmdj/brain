"""The creature acquires an operator instead of being handed one.

On a question it could not answer the system had exactly one move: refuse. It could already
build `column(qty)`, it held [5, 15, 7], and it had no way to COMBINE them into one number
unless a person edited the source. That is the static-code property this project is about,
and no amount of checking fixes it -- checking gates what arrives; it does not make anything
arrive.

WHAT THIS DOES NOT DO, stated first because the previous round's claim was too large:

  * It does not learn a word's meaning from the word. `acquire("median", {"median"})`
    enumerates what is expressible and REFUSES, because a word alone does not identify a
    function. Everything here is driven by worked examples.
  * It does not synthesise new primitives. Candidates are compositions of what the tree
    already does with a list of numbers: order, count, sum, min, max, mean, and arithmetic
    on those. The reach grows with the primitives, not with the operators I typed, but it
    is a finite reach and saying otherwise would be the same overstatement again.

WHAT IT DOES DO: given examples, it keeps the distinct functions consistent with all of
them, refuses while more than one survives, and declares the arithmetic itself -- with a
law it induces and the same gates every hand-written operator must pass. A creature that
refuses to guess is the point; a creature that guesses a median and installs a range is
the defect.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import canonical.runtime.value_algebra_v1 as V  # noqa: E402
from canonical.runtime import inspect_v1 as I  # noqa: E402
from canonical.runtime import operator_acquisition_v1 as OA  # noqa: E402

STOCK = "item,qty\nbolt,5\nnut,15\nbolt,7\n"


@pytest.fixture(autouse=True)
def _clean():
    before = (dict(V._AGG_WORDS), dict(V._AGGREGATES))
    yield
    V._AGG_WORDS.clear()
    V._AGG_WORDS.update(before[0])
    V._AGGREGATES.clear()
    V._AGGREGATES.update(before[1])


# ---------------------------------------------------------------------------
# A word is not a definition.
# ---------------------------------------------------------------------------

def test_the_word_alone_is_refused_and_says_why():
    """Installing "whichever candidate passed first" would answer a range for "median"."""
    result = OA.acquire("median", {"median"})
    assert result["acquired"] is False
    assert result["reason"] == "no_example"
    assert result["expressible"] > 1
    assert "median" not in V.aggregate_names()


def test_one_example_is_usually_not_enough_and_the_system_says_so():
    result = OA.acquire_from_examples("median", {"median"}, [([5.0, 15.0, 7.0], 7.0)])
    assert result["acquired"] is False
    assert result["reason"] == "ambiguous"
    assert len(result["alternatives"]) > 1
    assert "median" not in V.aggregate_names()


def test_alternatives_are_counted_by_function_not_by_formula():
    """Four different ways of writing a median are ONE alternative, not four.

    The same mistake as a new name for an old function, one layer up: two formulas that
    compute the same function are not two choices. Counting the formula made the system
    report "ambiguous" about a word it had actually determined.
    """
    admitted = [r for r in OA.survey() if r["admitted"]]
    distinct = OA._distinct(admitted)
    assert len(distinct) < len(admitted), "the collapse never fires -- it is not testing anything"
    for a in distinct:
        for b in distinct:
            if a is not b:
                assert not OA._same_function(a["fn"], b["fn"])


# ---------------------------------------------------------------------------
# Enough examples determine the function, and then it is declared.
# ---------------------------------------------------------------------------

def test_two_examples_acquire_a_median():
    result = OA.acquire_from_examples(
        "median", {"median"},
        [([5.0, 15.0, 7.0], 7.0), ([2.0, 4.0, 6.0, 8.0], 5.0)],
    )
    assert result["acquired"] is True, result
    assert "median" in V.aggregate_names()
    assert result["laws"], "an acquired operator must still carry a law"

    median = V._AGGREGATES["median"]["fn"]
    assert median([5.0, 15.0, 7.0]) == pytest.approx(7)
    assert median([2.0, 4.0, 6.0, 8.0]) == pytest.approx(5)
    assert median([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]) == pytest.approx(3.5)


def test_an_acquired_operator_answers_through_the_front_door(tmp_path):
    """The question it could not answer, answered by an operator it wrote itself."""
    (tmp_path / "stock.csv").write_text(STOCK)
    root = str(tmp_path)

    before = I.answer("what is the median qty", root)
    assert before["answered"] is False

    result = OA.acquire_from_examples(
        "median", {"median"},
        [([5.0, 15.0, 7.0], 7.0), ([2.0, 4.0, 6.0, 8.0], 5.0)],
    )
    assert result["acquired"] is True, result

    after = I.answer("what is the median qty", root)
    computation = after.get("computation") or {}
    assert computation.get("value") == "7"
    assert after["answered"] is True
    # and nothing else moved
    assert (I.answer("what is the total qty", root).get("computation") or {}).get("value") == "27"


def test_examples_that_nothing_can_satisfy_are_refused_rather_than_forced():
    result = OA.acquire_from_examples(
        "nonsense", {"nonsense"},
        [([5.0, 15.0, 7.0], 7.0), ([5.0, 15.0, 7.0], 999.0)],
    )
    assert result["acquired"] is False
    assert result["reason"] == "nothing_expressible_matches"
    assert "nonsense" not in V.aggregate_names()


# ---------------------------------------------------------------------------
# Gating: an acquired operator is not exempt from anything.
# ---------------------------------------------------------------------------

def test_every_candidate_is_gated_before_it_can_be_chosen():
    """No candidate becomes available by being generated. Each reports its refusal."""
    rows = OA.survey()
    assert rows
    for row in rows:
        if row["admitted"]:
            assert row["refused_because"] is None
            assert row["laws"], row["arity"]
        else:
            assert row["refused_because"]


def test_a_constant_is_never_an_admissible_candidate():
    """"It gives the right answer once" must not be enough.

    0.0 is the correct answer for a list of zeros, and a constant that returns 0 would
    reproduce such an example exactly. It is not admissible because no law can be induced
    for an arithmetic that does not depend on its data -- the same gate that refuses a
    constant at declaration refuses it here, before it can be chosen.
    """
    constants = [0.0, 1.0, 999.0]
    admissible = [r for r in OA.survey() if r["admitted"]]
    for row in admissible:
        for c in constants:
            assert not OA._same_function(row["fn"], (lambda v, c=c: c)), row["arity"]

    # and the specific trap: 0.0 is right for an all-zero list
    assert all(not OA._same_function(r["fn"], lambda v: 0.0)
               for r in admissible)


def test_acquiring_the_same_function_twice_is_refused_the_second_time():
    """The new-name check applies to acquired operators exactly as to declared ones."""
    examples = [([5.0, 15.0, 7.0], 7.0), ([2.0, 4.0, 6.0, 8.0], 5.0)]
    first = OA.acquire_from_examples("median", {"median"}, examples)
    assert first["acquired"] is True
    second = OA.acquire_from_examples("middle", {"middle"}, examples)
    assert second["acquired"] is False
    assert second["reason"] == "already_declared"
    assert "median" in second["detail"]
    assert "middle" not in V.aggregate_names()


# ---------------------------------------------------------------------------
# The weakness that remains, asserted so it cannot be forgotten.
# ---------------------------------------------------------------------------

def test_the_induced_law_for_an_acquired_median_is_too_weak_to_catch_a_min():
    """Recorded, not hidden: an acquired operator's law has the same limit as any other.

    A median's induced forms accept 5 and 15 for [5, 15, 7] because both are inputs. The
    value 15 is not a median and the law cannot say so. What protects the system here is
    not the law -- it is that the arithmetic was pinned by examples before it was declared.
    Stating this keeps anyone from reading `verified=True` as `every wrong value is caught`.
    """
    result = OA.acquire_from_examples(
        "median", {"median"},
        [([5.0, 15.0, 7.0], 7.0), ([2.0, 4.0, 6.0, 8.0], 5.0)],
    )
    assert result["acquired"] is True
    assert V.aggregate_holds("median", [5.0, 15.0, 7.0], 7.0) is True
    assert V.aggregate_holds("median", [5.0, 15.0, 7.0], 15.0) is True   # the limit
    assert V.aggregate_holds("median", [5.0, 15.0, 7.0], 999.0) is False
