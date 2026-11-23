"""The effect vocabulary is a law with two integer parameters, not a five-row table.

The tests below are the ones that would have caught my own error: `is_single` was first written
as `|net| <= 1 and replaced <= 1`, which called `(-1, 0, 2)` -- one net lost, two replaced,
three entities moved -- a single-entity change. It claimed 36 single shapes where the table
named 5.

The load-bearing test is `test_the_law_reproduces_every_name_the_table_gave`: where the old
classifier produced a name, the law must produce the SAME name, or the law is a redefinition
rather than a generalisation.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import an_effect_is_one_entity_moved_v1 as LAW
import instant_learning_in_a_new_environment_v1 as ILNE


def test_the_law_reproduces_every_name_the_table_gave():
    checked = 0
    for change in range(-2, 3):
        for arrived in range(0, 4):
            for departed in range(0, 4):
                old = ILNE.classify(change, arrived, departed)
                if old == ILNE.UNCLASSIFIED:
                    continue
                checked += 1
                assert LAW.describe(change, arrived, departed)["kind"] == old
    assert checked == 5, f"expected the five original shapes, saw {checked}"


def test_the_description_is_total_over_every_POSSIBLE_diff():
    checked = 0
    for change in range(-12, 13):
        for arrived in range(0, 13):
            for departed in range(0, 13):
                if not LAW.is_possible(change, arrived, departed):
                    continue
                checked += 1
                d = LAW.describe(change, arrived, departed)
                assert d["kind"] and d["description"]
                assert d["moved"] == abs(change) + min(arrived, departed)
    assert checked > 100


def test_change_is_never_independent_of_arrived_and_departed():
    """The grid of three INDEPENDENT integers is mostly impossible, and measuring on it was
    my error: 66 of 80 cells can never occur, so '5 of 80' was not a fraction of anything."""
    possible = [(c, a, d) for c in range(-2, 3) for a in range(0, 4) for d in range(0, 4)
                if LAW.is_possible(c, a, d)]
    assert len(possible) == 14
    assert all(c == a - d for c, a, d in possible)


def test_a_multi_entity_change_is_described_not_called_single():
    # (-2, 1, 3) is a POSSIBLE diff: three left and one arrived, so the count fell by two.
    # The earlier version of this test used (-1, 0, 2), which cannot occur -- and asserting
    # on an impossible diff is how a green test can still be wrong.
    assert LAW.is_possible(-2, 1, 3)
    d = LAW.describe(-2, 1, 3)
    assert d["kind"] == "REMOVE"
    assert d["net"] == -2 and d["replaced"] == 1
    assert d["moved"] == 3
    assert not d["is_single"], "two net plus one replaced; not a single-entity change"


def test_the_five_original_shapes_are_possible_and_named():
    """All five are POSSIBLE diffs and all five carry a name from the closed vocabulary.

    Not all five are SINGLE: APPEND moves three entities and INERT moves none. A vocabulary
    may name a shape for any reason, and conflating "named" with "single" is what made my
    first predicate claim 36 single shapes where the table had 5.
    """
    for shape in ((1, 1, 0), (-1, 0, 1), (0, 1, 1), (1, 2, 1), (0, 0, 0)):
        assert LAW.is_possible(*shape), shape
        d = LAW.describe(*shape)
        assert d["is_named"] and d["kind"] in ("PERSIST", "REMOVE", "REPLACE", "APPEND", "INERT")


def test_single_and_named_are_different_questions():
    append = LAW.describe(1, 2, 1)
    assert append["kind"] == "APPEND" and append["is_named"]
    assert not append["is_single"], "APPEND moves three entities"
    inert = LAW.describe(0, 0, 0)
    assert inert["kind"] == "INERT" and inert["is_named"]
    assert not inert["is_single"], "INERT moves none"


def test_a_single_entity_change_is_named_at_any_magnitude_one():
    assert LAW.describe(1, 1, 0)["kind"] == "PERSIST"
    assert LAW.describe(-1, 0, 1)["kind"] == "REMOVE"
    assert LAW.describe(0, 1, 1)["kind"] == "REPLACE"
    assert LAW.describe(0, 0, 0)["kind"] == "INERT"


def test_append_is_persist_with_a_copy():
    assert LAW.describe(1, 2, 1)["kind"] == "APPEND"
    assert LAW.describe(1, 2, 1)["net"] == 1
