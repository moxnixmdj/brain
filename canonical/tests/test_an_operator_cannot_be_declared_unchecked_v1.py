"""An operator is one declaration, and it cannot exist unchecked.

The previous round proved that declaring an operator as data adds every composition
containing it. It did not prove the declaration was HONEST, and it wasn't: the claim was
"one vocabulary entry and the arithmetic behind it", while a vocabulary entry on its own
enumerated fine and raised `KeyError` when evaluated, because the arithmetic was a
hardcoded dict of five names. The test that "proved" the claim patched that dict itself.

That is the defect these tests exist for, and it is not a tidiness complaint. This
system's purpose is to not answer confidently when it cannot be right. An operator that
can be added without a way to be wrong is exactly the ability to be confidently wrong --
and a creature that can extend its own vocabulary while unable to check the extension is
more dangerous than a static one, because it will keep extending.

So a declaration must carry four things, and the weakest of them -- the law -- is
refused if absent. These tests assert the refusal, not just the success.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import canonical.runtime.value_algebra_v1 as V  # noqa: E402
from canonical.runtime import operation_trial_v1 as T  # noqa: E402
from canonical.runtime import value_enumeration_v1 as EN  # noqa: E402

STOCK = "item,qty\nbolt,5\nnut,15\nbolt,7\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


def _ask(question: str, root: str):
    ents = T.entities(question, root)
    words = T._subject_words(question, ents)
    return EN.choose(question, root, ents, words)


def _median(values, *_):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


@pytest.fixture
def median_declared():
    """Declare a new aggregate and take it away again, without touching any source."""
    assert "median" not in V._AGG_WORDS
    yield _median
    V._AGG_WORDS.pop("median", None)
    V._AGGREGATES.pop("median", None)


# ---------------------------------------------------------------------------
# A declaration without a law is refused, out loud.
# ---------------------------------------------------------------------------

def test_an_aggregate_without_a_law_is_refused():
    """The refusal is the point, not the mechanics.

    An operator nobody can be wrong with is not a capability. If `declare_aggregate` let
    one through, the vocabulary would grow faster than the ability to check it, and every
    later answer built on it would be unfalsifiable by construction.
    """
    before = V.aggregate_names()
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("median", {"median"}, _median, ())
    assert "law" in str(err.value)
    assert "median" not in V._AGG_WORDS
    assert V.aggregate_names() == before


def test_an_aggregate_without_words_or_arithmetic_is_refused():
    """The other two parts are required for the same reason in the other direction."""
    with pytest.raises(ValueError):
        V.declare_aggregate("median", set(), _median, (V._WITHIN_INPUTS,))
    with pytest.raises(ValueError):
        V.declare_aggregate("median", {"median"}, None, (V._WITHIN_INPUTS,))
    assert "median" not in V._AGG_WORDS


def test_a_declaration_is_refused_before_it_is_half_applied():
    """A refused declaration must leave nothing behind.

    A half-registered operator is worse than none: the enumerator would build it and the
    evaluator would not know it, which is precisely the KeyError this round began with.
    """
    before_words = dict(V._AGG_WORDS)
    before_aggs = dict(V._AGGREGATES)
    with pytest.raises(ValueError):
        V.declare_aggregate("median", {"median"}, _median, ("not_a_law",))
    assert dict(V._AGG_WORDS) == before_words
    assert dict(V._AGGREGATES) == before_aggs


# ---------------------------------------------------------------------------
# A declared operator computes, with no code edited anywhere.
# ---------------------------------------------------------------------------

def test_a_declaration_alone_answers_a_question(tmp_path, median_declared):
    """One call. No source file touched, no monkeypatch, no arithmetic dict patched.

    The previous round's demonstration patched `_aggregate` in the test, which is why it
    passed: it was measuring a code edit and calling it a declaration.
    """
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    assert _ask("what is the median qty", root) is None

    V.declare_aggregate("median", {"median", "middle"}, _median, (V._WITHIN_INPUTS,))

    built = _ask("what is the median qty", root)
    assert built is not None
    assert built["value"] == pytest.approx(7)          # 5, 15, 7
    assert "median" in built["node"].label
    # and the operators that were already there are untouched
    assert _ask("what is the total qty", root)["value"] == pytest.approx(27)


def test_a_declared_operator_is_visible_to_every_path(tmp_path, median_declared):
    """One vocabulary, not a copy per reader.

    `operation_trial_v1` kept its own `_AGG_WORDS` and the two had already diverged --
    the trial knew four aggregates and the algebra five. Harmless while nothing declared
    anything; the moment something does, a copy means the declaring path sees the new
    operator and this one does not.
    """
    V.declare_aggregate("median", {"median"}, _median, (V._WITHIN_INPUTS,))
    assert "median" in T._AGG_WORDS
    assert T._AGG_WORDS is V._AGG_WORDS


# ---------------------------------------------------------------------------
# A declared operator is CHECKABLE -- the property that makes the growth safe.
# ---------------------------------------------------------------------------

def test_a_declaration_must_state_what_makes_an_answer_wrong(median_declared):
    """The law is a testable statement, not documentation.

    `within_inputs` is the weakest honest thing to say about an aggregate of numbers: the
    answer is one of them, so it lies between the least and the greatest. Weak is still
    falsifiable -- 99 is not in [5, 7, 15], and a declared operator that said 99 would be
    caught by the same walk that catches a lossy grouping.
    """
    V.declare_aggregate("median", {"median"}, _median, (V._WITHIN_INPUTS,))
    assert V.aggregate_holds("median", [5, 7, 15], 7) is True
    assert V.aggregate_holds("median", [5, 7, 15], 99) is False
    assert V.aggregate_holds("median", [5, 7, 15], 1) is False


def test_the_invariant_walk_can_reject_a_wrong_answer_from_a_new_operator(tmp_path, median_declared):
    """The law must be reachable from `holds`, not merely callable from a test.

    This declares TWO aggregates over the same data: an honest one and a liar. The liar
    returns a value outside the inputs, which is impossible for any aggregate of numbers
    and is therefore caught by the invariant walk -- the same walk that already catches a
    grouping that drops a bucket. Nothing here is patched; the liar is a real declaration
    that would really be used, which is what makes the check meaningful.
    """
    root = _tree(tmp_path, **{"stock.csv": STOCK})

    V.declare_aggregate("median", {"median"}, _median, (V._WITHIN_INPUTS,))
    honest = _ask("what is the median qty", root)
    assert honest is not None and honest["value"] == pytest.approx(7)
    assert V.holds(honest["node"], honest["value"]) is not False

    # a declaration whose arithmetic lies in a way ONLY the law can see: 999 is not one
    # of [5, 15, 7] and cannot be, whatever the operator is called.
    V.declare_aggregate("liar", {"liar"}, lambda v: 999.0, (V._WITHIN_INPUTS,))
    try:
        built = _ask("what is the liar qty", root)
        # THE CHECK IS CONSULTED WHILE CHOOSING, NOT AFTERWARDS.
        #
        # This refuses outright rather than returning 999 and reporting it as unverified.
        # That is the whole distinction the project is built on: a check applied after the
        # answer is a gate that can be routed around, and a check applied while choosing
        # is what makes the answer. An unverified 999 that reaches a caller is a worse
        # outcome than no answer, even when the verdict beside it is honest.
        assert built is None, f"a law-breaking declaration was ANSWERED with {built and built['value']}"
    finally:
        V._AGG_WORDS.pop("liar", None)
        V._AGGREGATES.pop("liar", None)


def test_every_built_in_aggregate_declares_a_law():
    """No aggregate may be exempt from being checkable, `sum` included."""
    for name in V.aggregate_names():
        assert V._AGGREGATES[name]["laws"], name
        assert callable(V._AGGREGATES[name]["fn"]), name


def test_a_sum_cannot_be_smaller_than_its_largest_member(tmp_path):
    """The strongest cheap statement about a sum, checked against real data."""
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    built = _ask("what is the total qty", root)
    assert built is not None
    values = [5.0, 15.0, 7.0]
    assert V.aggregate_holds("sum", values, built["value"]) is True
    assert V.aggregate_holds("sum", values, 3.0) is False      # a count in a sum's clothes
