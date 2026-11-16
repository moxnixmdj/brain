#!/usr/bin/env python3
"""One description language for both halves: the bottleneck found by asking a different question.

THE DEFECT THIS PINS
--------------------
Acting and learning did not share a vocabulary:

    acting   `instruction_policy_v1` -> `instruction_contract_v1` + `anchored_frame_v1` -> an INDEX
    learning `demonstration_version_space_v1` -> its own private tuple grammar

So the 5.43 bits a step costs (`what_one_experience_buys_v1`) were spent identifying an element in a
language the acting half never consults. A skill could be perfectly learned and structurally
unreachable — the same failure this tree has already paid for at three other layers.

MEASURED 2026-11-16, 1415 actionable elements on 130 real pages:

    named to exactly ONE element by its description      946  (66.9%)
    neither own words nor an id                          318  -> class + order
    a name that repeats                                  151  -> order separates the twins
    mean bits if position is usable                     0.93  (vs 5.43 for the learner)

and ordinals are 95.0% stable across seeds (229 of 241 descriptions), breaking exactly where the
number of peers changes — which is why an ordinal is never stored without its peer-count.

The observations below are real captures trimmed to the elements each claim is about.
"""
from __future__ import annotations

import pytest

from canonical.runtime import one_description_language_v1 as L


def _el(index, text="", **extra):
    element = {"index": index, "tag": "div", "text": text, "classes": "", "value": "",
               "parent": 0, "can_click": True}
    element.update(extra)
    return element


def _page(*elements):
    return {"elements": [{"index": 0, "tag": "body", "text": "", "parent": -1,
                          "can_click": False}] + list(elements)}


#: four labels all reading "Duration:", as `buy-ticket` really has at seed 1060
DURATIONS = _page(*[_el(i, "Duration:", tag="label", parent=1) for i in (6, 14, 22, 30)])


# --------------------------------------------------------------------------- #
# identity comes from the element's OWN words
# --------------------------------------------------------------------------- #
def test_identity_is_the_elements_own_words_and_never_its_subtree():
    """`full_text` is subtree text; using it makes one record look like seven (measured earlier)."""
    page = _page(_el(5, "Quis", tag="span", classes="alink"))
    got = L.describe(page["elements"][1], page)
    assert got.own == "quis"
    assert got.tag == "span"


def test_a_shared_description_names_one_element_when_it_is_unique():
    page = _page(_el(5, "Submit", tag="button", id="subbtn"))
    got = L.describe(page["elements"][1], page)
    assert L.identify(got, page) == [5]
    assert L.bits(got, page) == 0.0


# --------------------------------------------------------------------------- #
# gap one: 318 elements with neither own words nor an id
# --------------------------------------------------------------------------- #
def test_an_element_with_no_name_is_not_evidence_that_the_page_cannot_name_it():
    """An SVG `circle` with class `init-black` has no text and no id.

    A description built only from name-like properties is EMPTY for it, and an empty description
    matched 10 elements on `email-inbox` — a reported 3.32 bits that was really "this language has
    nothing to say here", not "the page is ambiguous".
    """
    page = _page(_el(4, "", tag="circle", classes="init-black"),
                 _el(7, "", tag="circle", classes="init-black"))
    got = L.describe(page["elements"][1], page)
    assert L.residual(got, page, 4).startswith("NAMED_BY_CLASS_AND_ORDER_ONLY")


def test_class_and_position_together_name_what_neither_names_alone():
    page = _page(_el(4, "", tag="circle", classes="init-black"),
                 _el(7, "", tag="circle", classes="init-black"))
    got = L.describe(page["elements"][1], page)
    assert L.identify(got, page) == [4, 7]
    assert L.identify(got, page, ordinal=2) == [7]


# --------------------------------------------------------------------------- #
# gap two: 151 names that repeat
# --------------------------------------------------------------------------- #
def test_a_repeated_name_is_separated_by_its_place_among_its_twins():
    """Four labels read "Duration:". The observation already says which is which."""
    got = L.describe(DURATIONS["elements"][1], DURATIONS)
    assert L.identify(got, DURATIONS) == [6, 14, 22, 30]
    assert L.residual(got, DURATIONS, 6) == "THE_NAME_REPEATS__ORDER_SEPARATES_THE_TWINS"
    assert L.ordinal(DURATIONS["elements"][1], DURATIONS) == "1"
    assert L.identify(got, DURATIONS, ordinal=1) == [6]
    assert L.identify(got, DURATIONS, ordinal=4) == [30]


def test_an_ordinal_past_the_end_names_nothing_rather_than_the_wrong_element():
    got = L.describe(DURATIONS["elements"][1], DURATIONS)
    assert L.identify(got, DURATIONS, ordinal=5) == []


# --------------------------------------------------------------------------- #
# the honest caveat that makes a stored ordinal safe or dangerous
# --------------------------------------------------------------------------- #
def test_an_ordinal_must_be_stored_with_the_count_it_was_taken_under():
    """MEASURED: ordinals are 95% stable across seeds and break where the peer count changes.

    On `email-inbox` the number of rows differs per instance (5, 6, 10). A stored ordinal without
    its count cannot be checked on replay, so the skill would confidently name the wrong element.
    """
    got = L.describe(DURATIONS["elements"][1], DURATIONS)
    assert L.peer_count(got, DURATIONS) == 4
    assert L.ordinal_is_valid(3, 4, got, DURATIONS) is True
    # the same description on a page where the count moved: the ordinal is REFUSED, not reinterpreted
    fewer = _page(_el(6, "Duration:", tag="label", parent=1),
                  _el(14, "Duration:", tag="label", parent=1))
    assert L.peer_count(got, fewer) == 2
    assert L.ordinal_is_valid(3, 4, got, fewer) is False


# --------------------------------------------------------------------------- #
# the round trip: a stored description must re-find its element, or say why not
# --------------------------------------------------------------------------- #
def test_a_description_that_still_fits_its_element_round_trips_cleanly():
    page = _page(_el(5, "Submit", tag="button", id="subbtn"))
    got = L.describe(page["elements"][1], page)
    assert L.round_trip_problem(got, 5, page) is None


def test_a_description_that_no_longer_fits_is_refuted_not_silently_used():
    """The check the two-language defect needed: reachability of a stored skill."""
    page = _page(_el(5, "Submit", tag="button", id="subbtn"))
    got = L.describe(page["elements"][1], page)
    other = _page(_el(9, "Cancel", tag="button", id="cancel"))
    assert L.round_trip_problem(got, 5, other) == "REFUTED__THE_DESCRIPTION_NOW_MATCHES_NOTHING"


def test_a_description_that_fits_two_elements_says_so_instead_of_picking_one():
    page = _page(_el(6, "Duration:", tag="label"), _el(14, "Duration:", tag="label"))
    got = L.describe(page["elements"][1], page)
    assert L.round_trip_problem(got, 6, page).startswith("AMBIGUOUS__2_ELEMENTS")


def test_the_key_is_stable_and_names_one_line():
    """A description is stored as one string, so the same element on the same page is one key."""
    page = _page(_el(5, "Submit", tag="button", id="subbtn"))
    a = L.describe(page["elements"][1], page)
    b = L.describe(page["elements"][1], page)
    assert a.key() == b.key() and a.key().startswith("ELEM_")
