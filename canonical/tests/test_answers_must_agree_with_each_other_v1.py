"""Verification was per-expression, and that is the wrong layer.

Every check in this system asks whether ONE answer is sound against its own law. Nothing
asks whether the SET of answers is coherent, so on `sales.csv` all of these were returned
with `verified: True` and nothing compared them:

    what is the total amount                 -> 550
    what is the total amount per region      -> [150, 150, 250]     (sums to 550)
    what is the total amount divided by how
      many regions                           -> 1.5                (right answer: 183.33)

The third is built as `half(count(sum(amount) by region))` -- it asks "how many regions"
and then halves that count rather than using it as a divisor, because no binary
combinator exists to express `A / B`. Its law grade was `None`, which read as "no law
required" when it in fact meant "no law found". So the one answer that was entirely
unchecked was also the one reporting itself as needing no check.

A system that can verify every sentence and never notice that two of them disagree is not
verified, it is locally consistent. This adds the missing layer: memory of what it has
already said, and a rule that compares a new answer with the answers it depends on.

What this is NOT, deliberately:

  * It does not resolve contradictions. Choosing which of two verified answers to believe
    is the guess this project keeps refusing to make. Both survive; the disagreement is
    reported as a disagreement.
  * It does not compare across trees. A fact about one directory is not a fact about
    another; the same expression over different data is SUPPOSED to give a different
    answer. Getting this wrong is a false positive that happens in front of a user
    instead of in front of a test.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from canonical.runtime import answer_ledger_v1 as L  # noqa: E402
from canonical.runtime import inspect_v1 as I  # noqa: E402
from canonical.runtime import value_algebra_v1 as V  # noqa: E402

SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _clean():
    L.reset()
    yield
    L.reset()


# ---------------------------------------------------------------------------
# The contradiction is reported, and the parts are not silently preferred.
# ---------------------------------------------------------------------------

def test_a_vector_that_claims_to_be_the_parts_must_recombine(tmp_path):
    """[150, 150] cannot be the parts of a total that was already reported as 550."""
    L.record("what is the total amount", _total_node(tmp_path), 550.0, verified=True)
    L.record("the total amount split in two", _parts_node(tmp_path, [150.0, 150.0]),
             [150.0, 150.0], verified=True)

    out = L.contradictions()
    assert [c["kind"] for c in out] == ["PARTS_NOT_WHOLE"], out
    assert "recombine" in out[0]["why"]


def test_parts_that_do_add_up_are_not_reported(tmp_path):
    """The check has to be able to pass, or it is just an alarm that always rings."""
    L.record("what is the total amount", _total_node(tmp_path), 550.0, verified=True)
    L.record("the total amount per region", _parts_node(tmp_path, [150.0, 150.0, 250.0]),
             [150.0, 150.0, 250.0], verified=True)
    assert L.contradictions() == []


def test_a_quotient_is_not_mistaken_for_a_total(tmp_path):
    """The false positive that had to be fixed before this check was trustworthy.

    `what is the total amount divided by how many regions` returns 1.5. It sits on the
    same table as the 550 total and is a scalar, so the first version of this rule
    reported "[150, 150, 250] does not add up to 1.5". 1.5 never claimed to be a total.
    A check that fires on the wrong pair teaches readers to ignore every firing.
    """
    L.record("what is the total amount divided by how many regions",
             V._n("map", ("half", _count_node(tmp_path)), V.NUMBER, set(), "h"),
             1.5, verified=True)
    L.record("the total amount per region", _parts_node(tmp_path, [150.0, 150.0, 250.0]),
             [150.0, 150.0, 250.0], verified=True)
    assert L.contradictions() == []


# ---------------------------------------------------------------------------
# Scope: an answer is only comparable with an answer about the same tree.
# ---------------------------------------------------------------------------

def test_the_same_question_over_two_trees_is_not_a_contradiction(tmp_path):
    """550 and 100 are both correct; they are about different directories."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "sales.csv").write_text("region,amount\nnorth,100\n")

    L.record("what is the total amount", _total_node(tmp_path), 550.0,
             verified=True, root=str(tmp_path))
    L.record("what is the total amount", _total_node(other), 100.0,
             verified=True, root=str(other))

    assert L.contradictions() == []


def test_the_same_question_over_one_tree_is_a_contradiction(tmp_path):
    """Same shape, same tree, different value: one of them is wrong."""
    L.record("what is the total amount", _total_node(tmp_path), 550.0,
             verified=True, root=str(tmp_path))
    L.record("what is the total amount", _total_node(tmp_path), 100.0,
             verified=True, root=str(tmp_path))

    kinds = [c["kind"] for c in L.contradictions()]
    assert "SAME_SHAPE" in kinds, kinds


# ---------------------------------------------------------------------------
# Only verified answers are compared: an unverified answer cannot contradict.
# ---------------------------------------------------------------------------

def test_an_unverified_answer_never_contradicts(tmp_path):
    L.record("what is the total amount", _total_node(tmp_path), 550.0, verified=True)
    L.record("a guess", _parts_node(tmp_path, [1.0, 2.0]), [1.0, 2.0], verified=False)
    assert L.contradictions() == []


# ---------------------------------------------------------------------------
# The door uses it, and a crashed check is not a passing check.
# ---------------------------------------------------------------------------

def test_the_door_reports_contradictions_on_its_answer(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total amount", root)
    assert "contradicts" in out
    assert out["contradicts"] == []


def test_the_door_remembers_across_questions(tmp_path):
    """The property `answer()` did not have: it is no longer a pure function of one call."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    I.answer("what is the total amount", root)
    I.answer("what is the total amount in west", root)
    I.answer("what is the total amount in north", root)
    I.answer("what is the total amount in south", root)

    assert len(L.entries()) == 4
    # 250 + 150 + 150 = 550, so a working system must report nothing here.
    assert L.contradictions() == []


def test_a_crashed_ledger_is_not_a_clean_ledger(monkeypatch, tmp_path):
    """If the check cannot run, the answer must not claim it passed."""
    def boom(*a, **k):
        raise RuntimeError("ledger exploded")

    monkeypatch.setattr(L, "record", boom)
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total amount", root)
    assert out["contradicts"], "a check that crashed reported nothing wrong"
    assert out["contradicts"][0]["kind"] == "LEDGER_FAILED"


# ---------------------------------------------------------------------------
# Helpers: small expression nodes, so the rules are tested without the enumerator.
# ---------------------------------------------------------------------------

def _total_node(tmp_path):
    c = V._n("column", (str(tmp_path / "sales.csv"), "amount"), V.NUMVEC, set(), "c")
    return V._n("aggregate", ("sum", c), V.NUMBER, set(), "s")


def _count_node(tmp_path):
    c = V._n("column", (str(tmp_path / "sales.csv"), "region"), V.NUMVEC, set(), "c")
    return V._n("count", (c,), V.NUMBER, set(), "n")


def _parts_node(tmp_path, values):
    """A vector node whose literal values are `values`, typed as the source column."""
    c = V._n("column", (str(tmp_path / "sales.csv"), "amount"), V.NUMVEC, set(), "c")
    nodes = tuple(V._n("aggregate", ("sum", c), V.NUMBER, set(), f"p{i}")
                  for i in range(len(values)))
    n = V._n("vector", nodes, V.NUMVEC, set(), "v")
    return n


# ---------------------------------------------------------------------------
# `law_grade: None` must mean "no aggregate was applied", and nothing else.
#
# The FIRST fix for this was a hand-typed list of operators that carry a law. It missed
# `column_from`, whose subtree applies `sum` through a `groups` node, so the correct
# `per region` answer reported the null grade while the unchecked 1.5 reported NONE --
# the two readings were the wrong way round. A list of operator names is not an inventory
# of what carries a law; the grade is now derived from the operator table.
# ---------------------------------------------------------------------------

def test_an_answer_that_applies_an_aggregate_is_never_ungraded(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    for question in (
        "what is the total amount",
        "what is the total amount per region",          # sum applied via a `groups` node
        "what is the total amount in west",
        "what is the average amount",
    ):
        comp = I.answer(question, root)["computation"]
        assert comp["law_grade"] is not None, question


def test_the_grouped_answer_is_graded_at_least_as_well_as_the_flat_one(tmp_path):
    """`per region` applies the same sum the flat total does; neither outranks the other."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    flat = I.answer("what is the total amount", root)["computation"]["law_grade"]
    grouped = I.answer("what is the total amount per region", root)["computation"]["law_grade"]
    assert grouped == flat, (flat, grouped)


def test_an_unchecked_composite_grades_none_not_null(tmp_path):
    """THE ORIGINAL DEFECT. 1.5 is `verified: True` with no law behind it."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    comp = I.answer("what is the total amount divided by how many regions", root)["computation"]
    assert comp["law_grade"] == "NONE", comp["law_grade"]
    assert comp["law_grade"] is not None


def test_none_is_reserved_for_expressions_with_nothing_to_grade(tmp_path):
    """A bare column read applies no aggregate, so it has no law -- and says so."""
    from canonical.runtime import value_enumeration_v1 as E

    c = V._n("column", (str(tmp_path / "sales.csv"), "amount"), V.NUMVEC, set(), "c")
    assert E._answer_law_grade(c) is None
    total = V._n("aggregate", ("sum", c), V.NUMBER, set(), "s")
    assert E._answer_law_grade(total) == "MODERATE"


# ---------------------------------------------------------------------------
# The ledger has to read the shape of value the DOOR produces.
#
# Every value in a computation dict is rendered text: "550", "[150.0, 150.0, 250.0]",
# "yes". The first version of `_numbers` accepted only int/float/list-of-float and
# returned None for all of them, so `contradictions()` skipped every comparison and
# reported nothing on every conversation ever held. Three checks this round passed their
# tests for the same reason: the test handed the function the convenient type.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rendered, expected", [
    ("550", [550.0]),
    ("1.5", [1.5]),
    ("[150.0, 150.0, 250.0]", [150.0, 150.0, 250.0]),
    (550, [550.0]),
    (1.5, [1.5]),
    ([150.0, 250.0], [150.0, 250.0]),
])
def test_a_rendered_value_is_read_as_the_numbers_it_renders(rendered, expected):
    assert L._numbers(rendered) == expected


@pytest.mark.parametrize("not_a_number", ["yes", "no", "a.csv", "", "  ", [], True, None])
def test_text_that_is_not_a_rendered_number_is_not_guessed_at(not_a_number):
    assert L._numbers(not_a_number) is None


def test_the_ledger_fires_through_the_door_when_the_data_changes(tmp_path):
    """The end-to-end property, on the path a real question takes."""
    f = tmp_path / "sales.csv"
    f.write_text(SALES)
    I.answer("what is the total amount", str(tmp_path))
    f.write_text("region,amount\nnorth,100\n")
    out = I.answer("what is the total amount", str(tmp_path))

    kinds = [c["kind"] for c in out["contradicts"]]
    assert kinds == ["SAME_SHAPE"], kinds
    assert out["contradicts"][0]["value_a"] == "550"
    assert out["contradicts"][0]["value_b"] == "100"


# ---------------------------------------------------------------------------
# A shape has to keep the words that make two questions different.
#
# `shape_of` stripped every string argument -- "a kind, a column name: part of the shape?
# no". That answer was wrong in the dangerous direction: sum(amount), sum(qty) and
# max(amount) all collapsed to `aggregate(column())` and would have been reported as the
# same question. On sales.csv/stock.csv that is 550 against 27, both correct.
#
# It never fired because `node` was None for every answer the door produced. Two defects
# were covering for each other.
# ---------------------------------------------------------------------------

def test_different_columns_are_different_questions():
    a = V._n("aggregate", ("sum", V._n("column", ("sales.csv", "amount"),
                                      V.NUMVEC, set(), "c1")), V.NUMBER, set(), "s1")
    b = V._n("aggregate", ("sum", V._n("column", ("sales.csv", "qty"),
                                      V.NUMVEC, set(), "c2")), V.NUMBER, set(), "s2")
    assert L.shape_of(a) != L.shape_of(b)


def test_different_aggregates_are_different_questions():
    col = V._n("column", ("sales.csv", "amount"), V.NUMVEC, set(), "c")
    s = V._n("aggregate", ("sum", col), V.NUMBER, set(), "s")
    m = V._n("aggregate", ("max", col), V.NUMBER, set(), "m")
    assert L.shape_of(s) != L.shape_of(m)


def test_asking_the_same_thing_twice_is_the_same_question():
    def node():
        col = V._n("column", ("sales.csv", "amount"), V.NUMVEC, set(), "c")
        return V._n("aggregate", ("sum", col), V.NUMBER, set(), "s")
    assert L.shape_of(node()) == L.shape_of(node())


def test_a_filtered_total_is_a_different_question_from_the_whole(tmp_path):
    """`in west` and `altogether` both produce a sum of the same column."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    whole = I.answer("what is the total amount", root)["computation"]
    west = I.answer("what is the total amount in west", root)["computation"]
    assert whole["expression"] != west["expression"]


# ---------------------------------------------------------------------------
# Which answers CAN be checked against each other is discovered, not declared.
#
# The rule above started life as three typed lists: `_TOTAL_OPS`, `_is_a_total`, and a
# hardcoded `sum()`. That is the defect this whole project is about -- a vocabulary nobody
# derived -- and it was reproduced here in the same commit that removed it elsewhere. The
# list named `mean` as a total, so a mean would have been "checked" by adding up means,
# which is not a property of a mean; and `max`/`min` were named as totals and then compared
# with `sum`, which is false for both.
#
# The question is put to the operator instead: split a probe set every way, apply the
# aggregate to the whole and to each part, and see which recombination reproduces the
# whole. A newly declared operator decomposes correctly with no edit to the law.
# ---------------------------------------------------------------------------

from canonical.runtime import decomposition_law_v1 as D  # noqa: E402


def test_each_aggregate_decomposes_the_way_its_own_definition_says():
    assert D.decomposes_by("sum") == "sum"
    assert D.decomposes_by("count") == "sum"      # a total count is the sum of the counts
    assert D.decomposes_by("max") == "max"        # the largest of all is the largest of each
    assert D.decomposes_by("min") == "min"


def test_a_mean_declares_that_it_does_not_decompose():
    """THE PAYOFF. A mean of means is not the mean; it needs the group sizes.

    A typed list called `mean` a total and would have compared it with a sum. The
    discovery returns None, which is a real statement: this answer cannot be checked
    against its parts, and the system has to say so instead of blessing it.
    """
    assert D.decomposes_by("mean") is None


def test_an_operator_declared_after_the_law_was_written_decomposes_correctly():
    """The property that makes this a creature and not a table: no edit is needed here."""
    import math

    import canonical.runtime.value_algebra_v1 as valg
    saved = valg._AGGREGATES.get("product")
    try:
        valg._AGGREGATES["product"] = {
            "fn": lambda v: math.prod([float(x) for x in v]),
            "laws": ("non_negative",),
        }
        D._CACHE.pop("product", None)
        assert D.decomposes_by("product") == "product"
    finally:
        if saved is None:
            valg._AGGREGATES.pop("product", None)
        else:
            valg._AGGREGATES["product"] = saved
        D._CACHE.pop("product", None)


def test_an_operator_that_does_not_decompose_is_reported_uncheckable_not_agreed():
    import canonical.runtime.value_algebra_v1 as valg
    saved = valg._AGGREGATES.get("median")
    try:
        valg._AGGREGATES["median"] = {
            "fn": lambda v: sorted([float(x) for x in v])[len(v) // 2],
            "laws": ("within_inputs",),
        }
        D._CACHE.pop("median", None)
        assert D.decomposes_by("median") is None
        verdict = D.check_parts_against_whole(None, [1.0, 2.0], None, 3.0, kind="median")
        assert verdict["verdict"] == "uncheckable", verdict
    finally:
        if saved is None:
            valg._AGGREGATES.pop("median", None)
        else:
            valg._AGGREGATES["median"] = saved
        D._CACHE.pop("median", None)


def test_a_max_is_not_checked_by_adding_up():
    """The typed list compared maxima with sum(). 150+150+250 is 550, and max is 250."""
    L.record("the totals per region", _grouped_parts("max"), [150.0, 150.0, 250.0], verified=True)
    L.record("the largest amount", _flat("max"), 250.0, verified=True)
    assert L.contradictions() == []


def test_a_max_that_is_not_the_largest_part_is_a_contradiction():
    L.record("the totals per region", _grouped_parts("max"), [150.0, 150.0, 250.0], verified=True)
    L.record("the largest amount", _flat("max"), 999.0, verified=True)
    kinds = [c["kind"] for c in L.contradictions()]
    assert kinds == ["PARTS_NOT_WHOLE"], kinds


def test_something_that_cannot_be_checked_is_not_reported_as_a_contradiction():
    """A note, not a contradiction -- otherwise a coherent conversation floods with them."""
    L.record("the totals per region", _grouped_parts("mean"), [150.0, 150.0, 250.0], verified=True)
    L.record("the average amount", _flat("mean"), 137.5, verified=True)
    assert L.contradictions() == []
    assert [n["kind"] for n in L._NOTES] == ["UNCHECKABLE_PAIR"]


def test_the_door_records_which_aggregate_an_answer_applies(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    seen = {}
    for question in ("what is the total amount", "what is the total amount per region",
                     "what is the average amount"):
        seen[question] = I.answer(question, root)["computation"].get("aggregate")
    assert seen["what is the total amount"] == "sum"
    # the sum is declared on the CHILD `groups` node here; the search has to descend
    assert seen["what is the total amount per region"] == "sum"
    assert seen["what is the average amount"] == "mean"


def _flat(kind: str):
    c = V._n("column", ("sales.csv", "amount"), V.NUMVEC, set(), "c")
    return V._n("aggregate", (kind, c), V.NUMBER, set(), "s")


def _grouped_parts(kind: str):
    t = V._n("table", ("sales.csv",), V.TABLE, set(), "t")
    g = V._n("group", (t, "region", "amount"), V.TABLE, set(), "g")
    gs = V._n("groups", (g, kind, "region", "amount"), V.TABLE, set(), "gs")
    return V._n("values_of", (gs, f"{kind}(amount)"), V.NUMVEC, set(), "v")


# ---------------------------------------------------------------------------
# The false positives, kept as tests because each one came back after I removed it.
#
# Every guard below exists because a specific wrong pair was MEASURED on a coherent
# conversation. Removing any of them re-introduced the pair it prevents.
# ---------------------------------------------------------------------------

def test_a_breakdown_of_one_column_is_not_compared_with_another_column(tmp_path):
    """[150,150,250] of `amount` against 27 of `qty` -- both correct, unrelated."""
    root = _tree(tmp_path, **{"sales.csv": SALES,
                              "stock.csv": "item,qty\nbolt,5\nnut,15\nbolt,7\n"})
    I.answer("what is the total qty", root)
    out = I.answer("what is the total amount per region", root)
    assert out["contradicts"] == []


def test_a_filtered_slice_is_not_the_whole(tmp_path):
    """250 is the total *in west*; 150+150+250 is every region. Not the same question."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    I.answer("what is the total amount in west", root)
    out = I.answer("what is the total amount per region", root)
    assert out["contradicts"] == []


def test_a_quotient_is_not_the_whole(tmp_path):
    """1.5 is `half(count(...))`. It applies an aggregate and reads the same column, and
    it still never claimed to be the total of anything."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    I.answer("what is the total amount per region", root)
    out = I.answer("what is the total amount divided by how many regions", root)
    assert out["contradicts"] == []


def test_the_whole_conversation_on_one_tree_reports_nothing(tmp_path):
    """The end-to-end statement: eight correct answers, no contradictions."""
    root = _tree(tmp_path, **{"sales.csv": SALES,
                              "stock.csv": "item,qty\nbolt,5\nnut,15\nbolt,7\n"})
    for question in ("what is the total amount", "what is the total qty",
                     "what is the total amount in west", "what is the total amount in north",
                     "what is the total amount per region", "what is the average amount",
                     "count the items", "what is the total amount divided by how many regions"):
        out = I.answer(question, root)
        assert out["contradicts"] == [], (question, out["contradicts"])


def test_is_a_whole_is_decided_by_where_the_aggregate_sits():
    """The aggregate has to be the OUTERMOST operator, not merely present."""
    c = V._n("column", ("sales.csv", "amount"), V.NUMVEC, set(), "c")
    whole = V._n("aggregate", ("sum", c), V.NUMBER, set(), "s")
    covered = V._n("map", ("half", whole), V.NUMBER, set(), "m")
    assert D.is_a_whole(whole) is True
    assert D.is_a_whole(covered) is False


def test_a_breakdown_of_sums_is_not_checked_against_a_minimum(tmp_path):
    """FOUND ON MERGED MAIN, as a contradiction between two CORRECT answers.

    `[150, 150, 250]` is one SUM per region. `50` is the SMALLEST amount. The check took
    the aggregate from the WHOLE side -- `min` -- recombined the sums with `min`, got 150,
    and reported a disagreement with 50. The parts' own aggregate is what has to recombine:
    a breakdown of sums is not a breakdown of minima, whatever they read.

    One side cannot dictate the law for both.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    for question in ("what is the total amount per region",
                     "what is the largest amount",
                     "what is the smallest amount",
                     "what is the average amount",
                     "what is the total amount in west"):
        out = I.answer(question, root)
        assert out["contradicts"] == [], (question, out["contradicts"])


def test_mismatched_aggregates_are_reported_uncheckable_not_compared():
    verdict = D.check_parts_against_whole(None, [150.0, 150.0, 250.0], None, 50.0,
                                          kind="min", parts_kind="sum")
    assert verdict["verdict"] == "uncheckable", verdict
    assert "breakdown and total of one quantity" in verdict["why"]


def test_eleven_correct_answers_on_one_tree_report_nothing(tmp_path):
    """The whole conversation, every aggregate, one tree."""
    root = _tree(tmp_path, **{"sales.csv": SALES,
                              "stock.csv": "item,qty\nbolt,5\nnut,15\nbolt,7\n"})
    questions = ("what is the total amount", "what is the total qty",
                 "what is the total amount in west", "what is the total amount in north",
                 "what is the total amount per region", "count the items",
                 "how many regions", "what is the largest amount",
                 "what is the smallest amount", "what is the average amount",
                 "what is the total amount divided by how many regions")
    for question in questions:
        out = I.answer(question, root)
        assert out["contradicts"] == [], (question, out["contradicts"])
    assert len(L.entries()) == len(questions)
