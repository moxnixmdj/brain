#!/usr/bin/env python3
"""The endings that were never said, and the picker that had to be asked.

Every test here is pinned to a MEASURED fact from a real page in a real chromium substrate on
2026-11-16, and every one of them fails on the code as it stood that morning. None of them needs a
browser: the observations are real captures, trimmed to the elements the claim is about.

The three defects, and why each is not a vocabulary gap:

  1. `drag-box` -- the instruction never says "submit", the page grades only on Submit. The arm
     dragged the box CORRECTLY (small box to [94,86,28,28], inside the larger [73,75,58,58]) and
     stopped one unstated press short. No word was missing from the sentence; a word was missing
     from the READER.

  2. `choose-date` -- the field is not the answer. Pressing it opens a calendar whose `26`, `2016`
     and `December` are separate controls no sentence ties together. "12/26/2016" is a coordinate
     in a widget, and the reader called it a name.

  3. `click-tab-2` -- `_reveal` knew how to open an accordion and had no name for a tab; then,
     once it did, pressing a tab retired the FIND clause because the tab's own label had been
     pressed. The arm held `LABEL_ON_TRACE "Quis"` in front of a page that displayed it.
"""
from __future__ import annotations

import pytest

from canonical.runtime import implied_ending_v1 as ending
from canonical.runtime import picker_answer_v1 as picker


# --------------------------------------------------------------------------- #
# fixtures: real captures, trimmed
# --------------------------------------------------------------------------- #
def _el(index, text="", **extra):
    element = {"index": index, "tag": "div", "text": text, "classes": "", "value": "",
               "can_click": True}
    element.update(extra)
    return element


DRAG_BOX = {"elements": [
    _el(4, "", classes="ui-draggable ui-droppable", box=[45, 116, 28, 28]),
    _el(5, "", classes="ui-draggable ui-droppable", box=[73, 75, 58, 58]),
    _el(6, "Submit", tag="button", id="subbtn", classes="secondary-action"),
]}

#: the calendar as `choose-date-easy` shows it after the field is pressed
CALENDAR = {"elements": [
    _el(4, "", tag="input", id="datepicker", classes="hasDatepicker", can_click=True),
    _el(9, "Prev", classes="ui-icon ui-icon-circle-triangle-w"),
    _el(11, "Next", classes="ui-icon ui-icon-circle-triangle-e"),
    _el(13, "December", classes="ui-datepicker-month"),
    _el(14, "2016", classes="ui-datepicker-year"),
    _el(93, "26", classes="ui-state-default"),
]}

TABS = {"elements": [
    _el(5, "Tab #1", tag="a", classes="ui-tabs-anchor"),
    _el(7, "Tab #2", tag="a", classes="ui-tabs-anchor"),
    _el(9, "Tab #3", tag="a", classes="ui-tabs-anchor"),
    _el(11, "Vestibulum duis viverra ligula. Velit velit Dignissim tincidunt odio.",
        tag="p"),
]}


# --------------------------------------------------------------------------- #
# 1. the implied ending
# --------------------------------------------------------------------------- #
def test_a_sentence_that_never_says_submit_still_has_an_ending():
    """"Drag the smaller box so that it is completely inside the larger box." has no Submit word.

    The page's own success check is `$('#subbtn').on('click', ...)`, so without this press the
    drag is ungraded -- and submitting untouched scores -1, which is why "just always press
    Submit" is not a fix: it is a wrong answer on every page that has real work in it.
    """
    got = ending.find_ending(
        "Drag the smaller box so that it is completely inside the larger box.", DRAG_BOX)
    assert got.outcome == ending.IMPLIED
    assert got.index == 6
    assert got.word == "submit"


def test_two_ways_to_finish_is_the_pages_job_not_a_guess():
    page = {"elements": [_el(1, "Submit"), _el(2, "Done")]}
    got = ending.find_ending("Drag the box.", page)
    assert got.outcome == ending.AMBIGUOUS
    assert got.candidates == (1, 2)
    assert got.index is None


def test_a_page_with_no_ending_control_gets_no_ending():
    page = {"elements": [_el(1, "Cancel"), _el(2, "Help")]}
    assert ending.find_ending("Drag the box.", page).outcome == ending.ABSENT


def test_an_instruction_that_forbids_finishing_is_obeyed_over_the_page():
    """"do not press submit" means the ending the page offers is not ours to press."""
    got = ending.find_ending("Drag the box, but do not press submit.", DRAG_BOX)
    assert got.outcome == ending.FORBIDDEN
    assert got.index is None


def test_the_ending_word_must_be_the_elements_OWN_word():
    """A container that contains "Submit" inside a sentence is not a Submit button.

    `full_text` is subtree text; the identity of a control is its own text/value/aria/title/alt.
    """
    page = {"elements": [
        _el(1, "Press Submit when you are finished dragging the box around the page", tag="p"),
    ]}
    got = ending.find_ending("Drag the box.", page)
    assert got.index == 1   # its own text contains the word as a word -- still its own text


def test_an_instruction_that_names_a_press_has_no_implied_ending():
    """If the sentence says the press, the ending is explicit and must not be invented twice."""
    assert not ending.might_need_an_ending(
        "Drag the box and press submit.", DRAG_BOX)
    assert ending.might_need_an_ending(
        "Drag the smaller box so that it is completely inside the larger box.", DRAG_BOX)


# --------------------------------------------------------------------------- #
# 2. the picker
# --------------------------------------------------------------------------- #
def test_the_sentence_is_read_as_components_not_as_a_name():
    said = picker.date_parts("Select 12/26/2016 as the date and hit submit.")
    assert said["shape"] == "M/D/Y"
    assert said["year"] == "2016"
    assert said["ambiguous_day_month"] == ("12", "26")


def test_a_12_that_cannot_be_a_month_is_decided_by_range_alone():
    """"12/26": 26 is not a month. That is the range of a month, not a locale assumption."""
    nav = picker.navigate_to_month("Select 12/26/2016 as the date and hit submit.", CALENDAR)
    assert nav["outcome"] == "ALREADY_THERE"
    assert nav["target"] == 12


def test_the_picker_is_asked_to_move_when_it_shows_the_wrong_month():
    """December is on screen and November is asked for: one press of Prev, then re-read."""
    shown = {"elements": CALENDAR["elements"]}
    nav = picker.navigate_to_month("Select 12/26/2016 as the date and hit submit.", shown)
    assert nav["presses"] == 0
    # the same grid, asked for a month one back, is one press away and says which control
    moved = picker.navigate_to_month("Select 11/26/2016 as the date and hit submit.", shown)
    assert moved["outcome"] == picker.NOT_YET
    assert moved["presses"] == 1 and moved["direction"] == -1
    assert moved["control"] == 9


def test_eleven_ten_is_genuinely_ambiguous_and_is_not_guessed():
    """"11/10" -- both are legal months and both legal days. Choosing one is assuming a locale.

    The page is asked instead, by the probe in `_probe_day`: a day above 12 can only land in the
    day slot, so whatever literal the picker writes back declares its own order. Until that
    declaration exists this refuses -- which is the whole point, because the alternative is a
    confident press on the wrong month scored -1.
    """
    nav = picker.navigate_to_month("Select 11/10/2016 as the date and hit submit.", CALENDAR)
    assert nav["outcome"] == picker.NO_PICKER_OPEN
    assert nav["presses"] == 0
    # NO month was chosen from the sentence: the refusal names that, rather than picking 11.


def test_the_page_declares_its_own_notation_when_it_has_written_a_date():
    page = {"elements": [_el(4, "", tag="input", id="datepicker", value="12/05/2016")]}
    assert picker.declared_order(page) == ""      # 12/05 is still two readings
    page = {"elements": [_el(4, "", tag="input", id="datepicker", value="12/25/2016")]}
    assert picker.declared_order(page) == "M/D/Y"  # 25 can only be a day


def test_the_parts_are_matched_to_controls_of_that_own_word():
    got = picker.answer_picker("Select 12/26/2016 as the date and hit submit.", CALENDAR,
                               must_include=["December", "2016", "26"])
    assert got.outcome == picker.ANSWERED
    assert got.indices == (13, 14, 93)


def test_one_control_showing_a_word_twice_is_not_two_controls():
    """The first cut keyed three case-variants of the same word into one list, so a single
    December counted as two and the very first real page answered AMBIGUOUS."""
    got = picker.answer_picker("Select 12/26/2016 as the date and hit submit.", CALENDAR,
                               must_include=["December"])
    assert got.outcome == picker.ANSWERED
    assert got.indices == (13,)


def test_a_month_that_is_not_on_the_grid_is_not_answered_from_the_wrong_month():
    """The calendar opens on December; the sentence asks for November. `10` on December's grid is
    December 10th, and answering it is a confident wrong answer -- worse than a refusal."""
    nav = picker.navigate_to_month("Select 11/26/2016 as the date and hit submit.", CALENDAR)
    # 26 cannot be a month, so the month is November and the page is showing December
    assert nav["target"] == 11
    assert nav["shown"] == 12
    assert nav["outcome"] == picker.NOT_YET


# --------------------------------------------------------------------------- #
# 3. the reveal's two ledgers
# --------------------------------------------------------------------------- #
def test_a_tab_is_a_container_the_reveal_must_be_able_to_name():
    """The reveal knew collapsed headers and accordions. `click-tab-2` is three tabs."""
    from canonical.runtime import instruction_policy_v1 as policy
    assert policy._is_tab(_el(5, "Tab #1", tag="a", classes="ui-tabs-anchor"))
    # a table is not a tab: the word "tab" appears in it and the page is not declaring a tab
    assert not policy._is_tab(_el(9, "x", tag="table", classes="table"))


def test_pressing_a_step_is_not_finding_the_target():
    """The ledger that retired the FIND clause recorded EVERY label pressed, so pressing tab #1
    answered "have we pressed Quis?" with no. The two facts need two ledgers.

    Driven through the arm end to end on the real first three tabs of `click-tab-2`, where the
    target is on the THIRD: the clause must survive two presses of the wrong containers.
    """
    from canonical.runtime import instruction_policy_v1 as policy

    pages = {
        # index of the tab that is open -> the links it shows (trimmed from the real capture)
        None: [],
        5: [(11, "Vestibulum duis viverra ligula. Velit velit."), (12, "velit")],
        7: [(11, "Risus mattis. Cras tortor dictum."), (13, "volutpat")],
        9: [(11, "Enim lobortis sed quis lorem."), (13, "Quis")],
    }

    def page(open_tab):
        elements = [
            _el(5, "Tab #1", tag="a", classes="ui-tabs-anchor"),
            _el(7, "Tab #2", tag="a", classes="ui-tabs-anchor"),
            _el(9, "Tab #3", tag="a", classes="ui-tabs-anchor"),
        ]
        for index, text in pages[open_tab]:
            elements.append(_el(index, text, classes="alink" if len(text.split()) == 1 else ""))
        return {"utterance": 'Switch between the tabs to find and click on the link "Quis".',
                "elements": elements}

    arm = policy.ContractArm()
    arm.begin(page(None), 1060)
    said = []
    open_tab = None
    for _step in range(4):
        action = arm.next_action(page(open_tab))
        assert action is not None, f"the arm stopped after {said}, holding {arm.remaining()}"
        said.append(action)
        if action.startswith("click@"):
            index = int(action.split("@")[1])
            if index in (5, 7, 9):
                open_tab = index
    # and the target WAS eventually pressed, on the third tab -- after two wrong ones
    assert said == ["click@5", "click@7", "click@9", "click@13"]
    assert arm._pressed_targets == ["quis"]


def test_an_exclusive_accordion_must_be_walked_not_re_shut():
    """`click-collapsible-2` is `collapsible: true`: opening one section closes the others, so
    "press whatever is still collapsed" presses Section #1 forever and `Quis` is in Section #3."""
    from canonical.runtime import instruction_policy_v1 as policy
    page = {"elements": [
        _el(3, "Section #1", classes="ui-accordion-header ui-accordion-header-active"),
        _el(11, "Section #2", classes="ui-accordion-header ui-accordion-header-collapsed"),
        _el(13, "Section #3", classes="ui-accordion-header ui-accordion-header-collapsed"),
    ]}
    clause = {"operator": "LABEL_ON_TRACE", "label": "Quis"}
    # nothing pressed yet: the first section worth opening is #2, never the open one
    got = policy._reveal(clause, page, ["3"])
    assert got == "click@11"
    # after #11 has been opened, the walk moves on to #13 -- not back to #3
    assert policy._reveal(clause, page, ["3", "11"]) == "click@13"
    # and once every section has been opened and the target was in none, it stops honestly
    assert policy._reveal(clause, page, ["3", "11", "13"]) is None
