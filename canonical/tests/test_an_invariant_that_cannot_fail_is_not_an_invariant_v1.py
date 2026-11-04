"""An invariant that cannot fail is not an invariant.

The previous round added a law to every declared operator and claimed operators could no
longer exist unchecked. Three separate holes made that false, and the third one made the
other two unavoidable:

  1. `aggregate_holds` returned True whenever it could not judge -- including for every
     table, because a table is a dict and the code required a list.
  2. A law could be vacuous. `lambda values, result, *_: True` satisfied "has a law" and
     licensed a median of [5, 15, 7] as 999.
  3. `holds(node, value)` DROPPED the value. `_holds_invariants` re-evaluated the node and
     compared the expression with itself, so `holds(node, 1027)` for a sum of 27 checked 27
     and returned True. Every law was a tautology, and the one thing an invariant exists to
     catch -- a value the expression should not have been able to produce -- was the one
     thing it could not see.

The property that separates a real invariant from a tautology is not effort, it is ROUTE:
the expected value has to be derived without taking the path the expression took. The
grouping invariant was always real because it recounts the keys from the raw rows. The
aggregate law was not, because it re-ran the aggregate.
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
SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


def _ask(question: str, root: str):
    ents = T.entities(question, root)
    return EN.choose(question, root, ents, T._subject_words(question, ents))


def _median(values, *_):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


@pytest.fixture
def median_declared():
    assert "median" not in V._AGG_WORDS
    yield _median
    V._AGG_WORDS.pop("median", None)
    V._AGGREGATES.pop("median", None)


# ---------------------------------------------------------------------------
# Hole 3, the one that made the others unavoidable: the value is judged.
# ---------------------------------------------------------------------------

def test_holds_judges_the_value_it_is_given_and_not_one_it_re_derives(tmp_path):
    """`holds(node, v)` must depend on `v`.

    This is the whole test. If the function re-evaluates the node and ignores its argument,
    then every assertion ever written against it passes for any value, and every "the
    search rejects bad values" claim is vacuous.
    """
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    built = _ask("what is the total qty", root)
    assert built["value"] == pytest.approx(27)

    assert V.holds(built["node"], 27.0) is True
    # a value the expression could not have produced for these rows
    assert V.holds(built["node"], 1027.0) is False


def test_a_mean_is_judged_against_its_own_inputs(tmp_path):
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    built = _ask("what is the average of the qty", root)
    assert built["value"] == pytest.approx(9)
    assert V.holds(built["node"], 9.0) is True
    assert V.holds(built["node"], 900.0) is False


def test_a_lying_primitive_does_not_reach_the_reader_as_a_verified_answer(tmp_path, monkeypatch):
    """End to end, through the front door.

    A sum that returns the total plus a thousand is still perfectly REPRODUCIBLE: run it
    again and it lies the same way. The only thing that can reject it is a statement about
    what the number is allowed to be, checked against the value. Before the fix this
    reached the reader as a confident, verified 1550.
    """
    from canonical.runtime import inspect_v1 as I

    root = _tree(tmp_path, **{"sales.csv": SALES})
    honest = I.answer("what is the total amount", root)
    assert (honest.get("computation") or {}).get("value") == "550"
    assert honest["answered"] is True

    real = V._aggregate
    def lying(kind):
        fn = real(kind)
        def apply(values, *rest):
            out = fn(values, *rest)
            if kind == "sum" and out is not None:
                return out + 1000.0
            return out
        return apply

    monkeypatch.setattr(V, "_aggregate", lying)
    monkeypatch.setattr(V, "_reset_memo", lambda: None)
    lied = I.answer("what is the total amount", root)
    comp = lied.get("computation") or {}
    assert lied["answered"] is False, comp
    assert str(comp.get("value")) != "1550"


# ---------------------------------------------------------------------------
# Hole 1: "cannot judge" is not "fine".
# ---------------------------------------------------------------------------

def test_a_table_is_judged_by_its_rows_rather_than_silently_skipped():
    """`aggregate_holds` required a list, so no law ever ran on a table-valued aggregate."""
    table = {"_header": ["a"], "_body": [[1], [2], [3]]}
    assert V.aggregate_holds("count", table, 3) is True
    assert V.aggregate_holds("count", table, 99) is False
    assert V.aggregate_holds("count", table, 2) is False       # the dict-keys bug


def test_an_unjudgeable_value_returns_no_verdict_rather_than_success():
    """"I could not judge" and "I judged it fine" must not be the same answer.

    The return type says `None` means not-judged, but every caller compared `is False`, so
    a `None` behaved exactly like a pass. The distinction is only useful if it is made
    where the law is consulted.
    """
    assert V.aggregate_holds("nonexistent_aggregate", [1, 2], 5) is None


# ---------------------------------------------------------------------------
# Hole 2: a law that cannot say no is not a law.
# ---------------------------------------------------------------------------

def test_a_vacuous_law_is_refused(median_declared):
    """It has a law, the law is callable, and it passes everything -- and that is not enough."""
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("vacuous", {"vacuous"}, _median,
                            (lambda values, result, *_: True,))
    msg = str(err.value)
    assert "cannot fail" in msg or "can never say no" in msg
    assert "vacuous" not in V.aggregate_names()


def test_a_declaration_is_checked_against_its_own_arithmetic_before_registration(median_declared):
    """An arithmetic that violates its own law is detectable with no data and no question.

    Catching it at declaration means the operator never exists to be selected, so no later
    check has to be trusted to catch it.
    """
    with pytest.raises(ValueError) as err:
        V.declare_aggregate("liar", {"liar"}, lambda v: 999.0, (V._WITHIN_INPUTS,))
    assert "VIOLATES its own law" in str(err.value)
    assert "liar" not in V.aggregate_names()
    assert V._AGGREGATES.get("liar") is None


def test_a_refused_declaration_leaves_nothing_behind(median_declared):
    before_words = dict(V._AGG_WORDS)
    before_aggs = dict(V._AGGREGATES)
    for bad in (lambda v: 999.0,):
        with pytest.raises(ValueError):
            V.declare_aggregate("bad", {"bad"}, bad, (V._WITHIN_INPUTS,))
    with pytest.raises(ValueError):
        V.declare_aggregate("bad2", {"bad2"}, _median, (lambda v, r, *_: True,))
    assert dict(V._AGG_WORDS) == before_words
    assert dict(V._AGGREGATES) == before_aggs


# ---------------------------------------------------------------------------
# The laws have to be TRUE, not merely strict.
# ---------------------------------------------------------------------------

def test_every_declared_aggregate_has_a_falsifiable_law():
    for name in V.aggregate_names():
        spec = V._AGGREGATES[name]
        assert V._law_is_falsifiable(name, spec["fn"], spec["laws"]) is None, name


def test_a_sum_is_bounded_by_its_extremes_and_not_by_sign():
    """The first law here was `non_negative`, which is false for negative data.

    The falsifiability probe found it on [-3, -1, -7]: an honest sum of -11 was reported
    as violating its own declaration, so the first column holding a negative would have
    been rejected as wrong. A law that only holds for convenient data is not a law.
    """
    assert V.aggregate_holds("sum", [-3, -1, -7], -11) is True
    assert V.aggregate_holds("sum", [-3, -1, -7], -50) is False
    assert V.aggregate_holds("sum", [5, 15, 7], 27) is True
    assert V.aggregate_holds("sum", [5, 15, 7], 3) is False      # a count in a sum's clothes


def test_a_mean_cannot_leave_the_range_of_its_inputs():
    assert V.aggregate_holds("mean", [5, 15, 7], 9) is True
    assert V.aggregate_holds("mean", [5, 15, 7], 900) is False


# ---------------------------------------------------------------------------
# A declared operator is judged by the same machinery.
# ---------------------------------------------------------------------------

def test_a_declared_operator_is_judged_like_any_other(tmp_path, median_declared):
    V.declare_aggregate("median", {"median"}, _median, (V._WITHIN_INPUTS,))
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    built = _ask("what is the median qty", root)
    assert built["value"] == pytest.approx(7)
    assert V.holds(built["node"], 7.0) is True
    assert V.holds(built["node"], 99.0) is False


@pytest.fixture(autouse=True)
def _no_persistent_memory():
    """A test run must not write to the creature's committed memory store."""
    from canonical.tests._memory import no_persistent_memory

    with no_persistent_memory():
        yield
