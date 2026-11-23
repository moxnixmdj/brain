"""Tests for planning a SEQUENCE of measured moves.

Every test asserts a measurement. Several exist because a number was wrong first, and
the docstring names the defect so the test is not weakened later by someone who thinks
the reason was style.
"""

from __future__ import annotations

import gzip
import shutil
import tempfile

import pytest

from canonical.runtime import a_goal_that_needs_two_moves_v1 as P
from canonical.runtime import goal_to_door_v1 as G

HAVE = {name: shutil.which(name) for name in ("cp", "mv", "rm", "gzip")}

#: The four classes round 4 measured, as FULL signatures. Full, not the `moved()`
#: subset -- see `test_the_moved_subset_loses_the_precondition`.
COPY = {"CARD": "INCREASED", "IDENT": "CHANGED", "LOT": "RETAINED",
        "MULTISET": "CHANGED", "ORDER": "CHANGED", "PAIRING": "CHANGED"}
DELETE = {"CARD": "DECREASED", "IDENT": "CHANGED", "LOT": "PARTIAL",
          "MULTISET": "CHANGED", "ORDER": "CHANGED", "PAIRING": "CHANGED"}
RENAME = {"CARD": "SAME", "IDENT": "CHANGED", "LOT": "RETAINED",
          "MULTISET": "SAME", "ORDER": "CHANGED", "PAIRING": "CHANGED"}


def classes():
    return [P.move_of({"id": name, "tool": name}, signature=sig)
            for name, sig in (("copy", COPY), ("delete", DELETE), ("rename", RENAME))]


# --------------------------------------------------------------------------- #
# the transition, derived from the signature
# --------------------------------------------------------------------------- #
def test_a_copy_adds_a_name_without_creating_content():
    """A copy is not a creation of content, and CONTENTS must not move.

    The first model raised NAMES and READABLE and left CONTENTS alone; the second
    lowered CONTENTS on a delete as well as READABLE, which double-counted a single
    loss and made `cp; rm` look like it had destroyed everything.
    """
    copy = P.move_of({"id": "copy", "tool": "cp"}, signature=COPY)
    after = copy.apply(P.world(names=2, readable=2, contents=2))
    assert after[P.NAMES] == 3
    assert after[P.READABLE] == 3
    assert after[P.CONTENTS] == 2, "a copy must not be counted as a new content"


def test_a_delete_loses_one_content_not_two():
    """The double-count defect, stated as a number.

    `rm`'s LOT already says a content stopped being readable. Reading CARD DECREASED
    as a second loss made READABLE fall by 2 in a one-name world, so the floor at zero
    hid it in small worlds and every `cp; rm` sequence reported zero readable names
    left -- which is backwards, since that is the sequence that KEEPS one.
    """
    delete = P.move_of({"id": "delete", "tool": "rm"}, signature=DELETE)
    after = delete.apply(P.world(names=2, readable=2, contents=2))
    assert after[P.READABLE] == 1
    assert after[P.CONTENTS] == 1


def test_deleting_one_of_two_copies_keeps_the_content():
    """CONTENTS is derived from READABLE, not decremented independently.

    Two readable names holding one distinct content: deleting either leaves the
    content readable one place over. A model that subtracts CONTENTS cannot express
    that, and it is exactly the world where `rm` alone satisfies a naive goal.
    """
    delete = P.move_of({"id": "delete", "tool": "rm"}, signature=DELETE)
    world = P.world(names=2, readable=2, contents=1)
    after = delete.apply(world)
    assert after[P.READABLE] == 1
    assert after[P.CONTENTS] == 1


def test_lost_destroys_every_readable_content():
    """LOT LOST is about the RESULT, so it is a set and not a decrement.

    With a decrement, a LOST move in a three-content world left two contents behind --
    a move labelled "nothing survives" claiming two things survived.
    """
    lost = P.move_of({"id": "wipe", "tool": "shred"},
                     signature={**DELETE, "LOT": "LOST"})
    after = lost.apply(P.world(names=3, readable=3, contents=3))
    assert after[P.READABLE] == 0
    assert after[P.CONTENTS] == 0


def test_a_rename_neither_adds_nor_removes_a_name():
    """`mv` must not count as a cleanup.

    REMOVED counts the times the name count FELL. A rename moves a name; that is not a
    removal, and counting it as one is how `mv` would be offered for "clean up the
    original", which it does not do.
    """
    rename = P.move_of({"id": "rename", "tool": "mv"}, signature=RENAME)
    after = rename.apply(P.world(names=2, readable=2, contents=2))
    assert after[P.NAMES] == 2
    assert after[P.REMOVED] == 0


def test_the_moved_subset_loses_the_precondition():
    """The defect that made every move applicable in an empty world.

    `moved()` drops `LOT: RETAINED` because it is "unchanged", which is right when
    CHOOSING a door and wrong when SEQUENCING one: RETAINED is the statement that the
    move had content to work on. Fed the subset, a rename is applicable to a world with
    nothing in it.
    """
    subset = {k: v for k, v in G.moved(RENAME).items()}
    with pytest.raises(ValueError):
        P.move_of({"id": "rename", "tool": "mv"}, signature=subset)


# --------------------------------------------------------------------------- #
# the sequence
# --------------------------------------------------------------------------- #
def test_no_single_door_satisfies_the_goal():
    """The premise of the whole round. Asserted, not assumed.

    Two earlier goal statements failed this and both were caught here: `rm` satisfied
    {REMOVED>=1, READABLE>=1} in a world holding a duplicate content, and it satisfied
    {REMOVED>=1, READABLE>=1, NAMES>=3} in a world already holding four names.
    """
    moves = classes()
    start = P.world(names=2, readable=2, contents=2)
    goal = P.Goal(at_least={P.NAMES: 2, P.READABLE: 2, P.REMOVED: 1})
    assert P.one_move_answers(goal, moves, start) == []


def test_two_moves_reach_it_and_the_order_is_the_whole_answer():
    """`cp` then `rm` keeps the content; `rm` then `cp` cannot run at all.

    This is the measurement round 4 could not make: a join that answers one move at a
    time sees two doors and no difference.
    """
    moves = classes()
    start = P.world(names=2, readable=2, contents=2)
    goal = P.Goal(at_least={P.NAMES: 2, P.READABLE: 2, P.REMOVED: 1})
    assert P.plan(start, goal, moves) == ["copy", "delete"]

    experiment = P.why_order_matters(moves, P.world(names=1, readable=1, contents=1))
    assert experiment["order_decides"] is True
    assert experiment["copy_then_delete"]["holds"] is True
    assert experiment["delete_then_copy"]["holds"] is False
    assert experiment["delete_then_copy"]["refused_because"], "a refusal says WHY"


def test_the_plan_is_the_same_class_sequence_in_every_world():
    """The claim that makes it transfer: the answer does not mention a world.

    Three worlds of different sizes get the same two classes; only the instantiation
    differs. A plan that changed with the filenames would be the round-4 defect again.
    """
    moves = classes()
    plans = []
    for names in (2, 3, 4):
        goal = P.Goal(at_least={P.NAMES: names, P.READABLE: names, P.REMOVED: 1})
        plans.append(P.plan(P.world(names=names, readable=names, contents=names), goal,
                            moves))
    assert plans == [["copy", "delete"]] * 3


def test_an_unreachable_goal_is_refused_and_names_the_missing_fact():
    """A planner that always returns a plan has not been tested.

    "No names left, yet content still readable" needs a move that removes a name while
    keeping its content one place over; no measured class does that. The refusal names
    the condition that no remaining move can provide.
    """
    goal = P.Goal(at_most={P.NAMES: 0}, at_least={P.READABLE: 1})
    with pytest.raises(P.Refusal) as caught:
        P.plan(P.world(names=2, readable=2, contents=2), goal, classes())
    assert caught.value.code == P.UNREACHABLE
    assert "NAMES" in caught.value.detail


def test_a_goal_naming_an_unknown_dimension_is_rejected():
    """A goal over a word the state does not have would silently match nothing."""
    with pytest.raises(ValueError):
        P.Goal(at_least={"COLOUR": 1})


def test_two_moves_with_one_id_are_refused():
    """An ambiguous plan is worse than no plan."""
    moves = classes()
    with pytest.raises(P.Refusal):
        P.plan(P.world(names=1, readable=1), P.Goal(at_least={P.NAMES: 9}),
               [moves[0], P.move_of({"id": "copy", "tool": "cp"}, signature=COPY)])


# --------------------------------------------------------------------------- #
# against the real filesystem
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not (HAVE["cp"] and HAVE["rm"]), reason="needs cp and rm")
def test_the_prediction_matches_the_tree():
    """The model is only worth its predictions, so one is checked on disk.

    `cp` then `rm` must leave the content readable; `rm` then `cp` must fail. Both are
    run for real rather than reasoned about.
    """
    import os
    import subprocess

    where = tempfile.mkdtemp(prefix="brain-twomoves-test-")
    try:
        def fresh():
            for child in os.listdir(where):
                os.remove(os.path.join(where, child))
            with open(os.path.join(where, "in.txt"), "wb") as handle:
                handle.write(b"PROBE_CONTENT_ALPHA")

        # copy then delete: content survives under the new name
        fresh()
        subprocess.run(["cp", "in.txt", "COPY"], cwd=where, check=True)
        subprocess.run(["rm", "-f", "in.txt"], cwd=where, check=True)
        assert sorted(os.listdir(where)) == ["COPY"]
        with open(os.path.join(where, "COPY"), "rb") as handle:
            assert handle.read() == b"PROBE_CONTENT_ALPHA"

        # delete then copy: the copy has nothing to copy
        fresh()
        subprocess.run(["rm", "-f", "in.txt"], cwd=where, check=True)
        failed = subprocess.run(["cp", "in.txt", "COPY"], cwd=where,
                                capture_output=True)
        assert failed.returncode != 0
        assert sorted(os.listdir(where)) == []
    finally:
        shutil.rmtree(where, ignore_errors=True)


def test_the_harness_finds_copies_at_all():
    """The round-4 measurement defect, guarded.

    Round 4 seeded `in.txt`/`in.gz` while the census binds `cp`/`mv` to `in.json`, so
    both doors aborted on a missing operand and produced ZERO rows -- and the receipt
    said "4 programs". A harness that cannot see a copy cannot plan one.
    """
    from canonical.tools import a_goal_that_needs_two_moves_v1 as T

    if not all(HAVE[n] for n in ("cp", "mv", "rm", "gzip")):
        pytest.skip("needs cp, mv, rm and gzip")
    rows = T.measure_rows()
    tools = {row["tool"] for row in rows}
    assert "cp" in tools and "rm" in tools, f"only measured {sorted(tools)}"
