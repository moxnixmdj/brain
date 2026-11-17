#!/usr/bin/env python3
"""The wall was the candidate set, not the search, and this is the smallest thing that moves it.

MEASURED 2026-11-17, real pages, real layout, no model, $0
----------------------------------------------------------
`simple-arithmetic` prints `8 + 3 =`, its instruction says "solve the math problem and type your
answer", and its answer is `11`. `type_candidates` offers 16 strings at every tier from 0 to 3 and
`11` is among none of them, because `11` appears nowhere on the page. Four arms -- baseline, a
learned inert-action prior, a page-local oracle prior, and a shuffled control -- each spent
exactly 1200 actions and none of them succeeded. A hand typing `11` and pressing Submit succeeded
immediately. The search was never short of budget.

Wired into the same explorer, same seeds, same budget, 2 seeds x 7 pages:

    verified on a fresh page   11 of 14   ->   13 of 14
    actions spent                1232      ->    472
    every page that already worked: bit-identical (same pass, same spend)

The two pages that changed are both `simple-arithmetic`, both from fail-at-400 to pass-at-20.

WHAT THIS MODULE IS NOT
-----------------------
It is not a table of answers: at seed 1060 the page says `8 + 3 =` and the value is 11; at seed
1061 it says `1 + 7 =` and the value is 8; at 1062 `7 x 1 =` and the value is 7. Nothing about
those answers is stored. What is stored is the reading of four symbols. It is not a model and has
no parameters. It never decides, never types, and never claims an answer is right -- the page's
own reward stays the only verdict.

The general statement, for the next probe: a value a caller may type can be a FUNCTION of what the
page states, and a generator that can only copy will fail on every such page regardless of budget.
"""
from __future__ import annotations

import pytest

from canonical.runtime import derived_text_candidate_v1 as DER


def _page(*texts, utterance="", values=None):
    elements = [{"index": 0, "tag": "body", "text": ""}]
    for i, text in enumerate(texts, start=1):
        element = {"index": i, "tag": "div", "text": text}
        if values and i in values:
            element["value"] = values[i]
        elements.append(element)
    return {"elements": elements, "utterance": utterance}


# --------------------------------------------------------------------------- #
# it reads what the page printed
# --------------------------------------------------------------------------- #
def test_a_question_the_page_spells_is_answered_by_the_operator_it_printed():
    page = _page("8 + 3 =", "Submit",
                 utterance="Solve the math problem and type your answer into the textbox.")
    got = DER.spelled(page)
    assert [r["text"] for r in got] == ["11"]
    assert got[0]["operator"] == "+"
    assert got[0]["operands"] == [8.0, 3.0]
    assert got[0]["from_element"] == 1


def test_each_operator_the_page_can_print_is_read_as_itself():
    """WHY EACH PAIR IS CHOSEN TO BE UNIQUELY SATISFIED BY ONE OPERATOR.

    A first version of this test used `4 * 7 = 28` and survived a mutation that replaced
    multiplication with addition, because 4 + 7 is 11 and the mutation was caught only by the
    `3 x 5` case if that had also been changed. A test whose expected value is not produced by
    exactly one candidate reading does not pin the reading at all. Every pair below gives a
    different value under every other operator this module understands.
    """
    cases = (("4 * 7 =", "28", (11, -3, 1.75)),      # + - /
             ("9 - 2 =", "7", (11, 18, 4.5)),
             ("8 / 2 =", "4", (10, 6, 16)),
             ("3 x 5 =", "15", (8, -2, 0.6)),
             ("6 × 7 =", "42", (13, -1, 0.8571428571428571)),
             ("5 + 6 =", "11", (-1, 30, 0.8333333333333334)))
    for spelled, expected, other_values in cases:
        got = [r["text"] for r in DER.spelled(_page(spelled))]
        assert got == [expected], spelled
        for other in other_values:
            assert got[0] != str(other).rstrip("0").rstrip("."), (spelled, other)


def test_the_answer_is_never_in_the_page_text_it_answers():
    """The whole point: the derived value must be a value the page does not already show."""
    page = _page("8 + 3 =", "Submit")
    shown = " ".join(str(e.get("text")) for e in page["elements"])
    derived = [r["text"] for r in DER.spelled(page)]
    assert derived == ["11"]
    assert "11" not in shown


# --------------------------------------------------------------------------- #
# the refusals are the other half of the contract
# --------------------------------------------------------------------------- #
def test_a_page_that_states_arithmetic_without_asking_for_it_is_not_answered():
    """`8 + 3` with no `=` is a statement. Nothing here may turn it into an answer."""
    assert DER.spelled(_page("8 + 3")) == []
    assert DER.spelled(_page("8+3 =")) != []       # the same facts WITH the question mark of a form


def test_an_unknown_symbol_derives_nothing_instead_of_guessing():
    assert DER.spelled(_page("8 % 3 =")) == []
    assert DER.spelled(_page("8 ^ 3 =")) == []


def test_a_page_that_spells_nothing_leaves_the_candidate_set_exactly_as_it_was():
    page = _page("Submit", utterance="Click submit.")
    existing = ["Submit", "Click"]
    assert DER.candidates(page, existing=existing) == existing
    assert DER.describe(page, existing=existing)["unchanged_when_nothing_spelled"] is True


def test_division_by_zero_derives_nothing():
    assert DER.spelled(_page("8 / 0 =")) == []


# --------------------------------------------------------------------------- #
# ordering: a derived value never displaces a value the page stated
# --------------------------------------------------------------------------- #
def test_the_pages_own_text_comes_first_and_the_derived_value_after_it():
    page = _page("8 + 3 =", "Submit")
    existing = ["Submit", "Solve"]
    got = DER.candidates(page, existing=existing)
    assert got[:2] == ["Submit", "Solve"]
    assert got[2] == "11"


def test_a_derived_value_already_offered_is_not_duplicated():
    page = _page("1 + 1 =")
    assert DER.candidates(page, existing=["2", "other"]) == ["2", "other"]


def test_the_value_can_arrive_as_a_field_value_or_as_the_instruction():
    """A page may put its question in an input's value, or spell it in the instruction itself."""
    assert [r["text"] for r in DER.spelled(_page("", values={1: "6 + 6 ="}))] == ["12"]
    assert [r["text"] for r in DER.spelled(_page("", utterance="What is 5 + 4 = ?"))] == ["9"]


def test_whole_number_answers_are_written_without_a_trailing_point_zero():
    got = [r["text"] for r in DER.spelled(_page("7 + 0 ="))]
    assert got == ["7"]


def test_a_fractional_answer_keeps_its_fraction():
    got = [r["text"] for r in DER.spelled(_page("7 / 2 ="))]
    assert got == ["3.5"]


# --------------------------------------------------------------------------- #
# the measurement the receipt quotes
# --------------------------------------------------------------------------- #
def test_describe_reports_what_was_added_and_from_what_reading():
    page = _page("8 + 3 =", "Submit")
    described = DER.describe(page, existing=["Submit"])
    assert described["added"] == 1
    assert described["derived"] == ["11"]
    assert described["spelled"][0]["reading"] == "8 + 3 ="
    assert described["schema"] == DER.SCHEMA
    assert described["authority"] == "NONE"
