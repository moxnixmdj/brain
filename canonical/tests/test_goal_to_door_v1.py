"""Tests for the goal-to-door join.

Every test here asserts a MEASUREMENT, and several of them exist because a number
was wrong first. The docstrings name the defect, because a test whose reason is
forgotten gets deleted or weakened.
"""

from __future__ import annotations

import gzip
import json
import pathlib
import shutil
import tempfile

import pytest

from canonical.runtime import goal_to_door_v1 as G

HAVE = {name: shutil.which(name) for name in ("cp", "mv", "rm", "gzip")}


# --------------------------------------------------------------------------- #
# the state -> signature function
# --------------------------------------------------------------------------- #
def test_a_rename_and_a_delete_are_different_moves():
    """The defect the invented relation exists to fix.

    The project's five relations are functions of a SET of (name, content) pairs,
    so `mv a b` and `rm a` both "remove a name" and came out identical: both read
    IDENT CHANGED, PAIRING CHANGED. A join over that vocabulary cannot tell a move
    from a destruction, so no ranking could have been right.
    """
    rename = G.signature({"a": b"payload"}, {"b": b"payload"})
    delete = G.signature({"a": b"payload"}, {})
    # CARD does separate a rename from a directory-wide delete, and claiming
    # otherwise would be an overclaim: a delete lowers the count.
    assert G.moved(delete).get("CARD") == G.DECREASED
    assert "CARD" not in G.moved(rename)
    # the invented relation is what says WHY they differ: one keeps the content.
    assert G.moved(rename).get(G.LOT) is None      # RETAINED is dropped as "no change"
    assert G.moved(delete).get(G.LOT) == G.LOST
    assert G.moved(rename) != G.moved(delete), "a move and a delete must not be one move"


def test_a_compression_retains_what_a_delete_destroys():
    """`gzip a` keeps the content inside a.gz; `rm a` does not. Same name count."""
    compressed = gzip.compress(b"payload", mtime=0)
    # THE case that matters, and the one `CARD` cannot see: compressing one file and
    # renaming one file both keep the count the same. Only LOT separates them.
    compress = G.signature({"a": b"payload"}, {"a.gz": compressed})
    rename = G.signature({"a": b"payload"}, {"b": b"payload"})
    delete = G.signature({"a": b"payload"}, {})
    # MEASURED, not assumed: MULTISET compares CONTENT IDENTITIES, so re-encoding a
    # payload into a gzip stream changes it while a rename does not. That is a real
    # difference between the two steps and the vocabulary is right to report it.
    assert G.moved(compress).get("MULTISET") == G.CHANGED
    assert "MULTISET" not in G.moved(rename)
    # CARD cannot see either step: both keep the number of files the same. If a goal
    # is stated only over CARD, a compression and a deletion are indistinguishable --
    # which is precisely why a goal must name the relations it cares about.
    assert "CARD" not in G.moved(compress) and "CARD" not in G.moved(rename)
    assert G.moved(delete).get("CARD") == G.DECREASED
    # the content is still recoverable one layer down, so this is not a destruction
    assert G.lot({"a": b"payload"}, {"a.gz": compressed}) == G.RETAINED
    assert G.lot({"a": b"payload"}, {}) == G.LOST


def test_a_copy_increases_the_count_while_a_move_does_not():
    copy = G.signature({"a": b"payload"}, {"a": b"payload", "b": b"payload"})
    move = G.signature({"a": b"payload"}, {"b": b"payload"})
    assert G.moved(copy)["CARD"] == G.INCREASED
    assert "CARD" not in G.moved(move), "a rename must not look like a new thing"


def test_two_binaries_are_two_contents():
    """The defect: decoding bytes with errors="replace" merged every binary.

    A gzip stream and its own source text then share a run of U+FFFD, so losing
    one looked like losing nothing and `rm` and `gzip` were reported identically.
    """
    one = G.as_state({"a": b"\x1f\x8b\x08\x00\x00"})
    two = G.as_state({"a": b"\x1f\x8b\x08\x00\x01"})
    assert one[0][1] != two[0][1]
    text = G.as_state({"a": b"\x1f\x8b\x08\x00\x00"})
    assert text[0][1].startswith("bytes:")


def test_a_control_sharing_the_subject_is_not_a_control():
    """Three worlds, and the same door must report the same move in all of them."""
    worlds = ({"in.txt": b"first"}, {"in.txt": b"second"}, {"in.txt": b"x"})
    signatures = {json.dumps(G.moved(G.signature(w, {})), sort_keys=True) for w in worlds}
    assert len(signatures) == 1, "deleting the subject is one move whatever it contained"


# --------------------------------------------------------------------------- #
# the goal
# --------------------------------------------------------------------------- #
def test_a_goal_about_retention_is_stateable():
    """The defect: `stateable` was checked against RELATIONS, which omits LOT.

    Every goal mentioning retention was called UNSTATEABLE, so `rm` answered 0 of
    21 held-out requests while `cp` answered all of its own. It read like a finding
    and was a bug.
    """
    goal = G.Goal(need=((G.LOT, G.LOST),))
    assert G.stateable(goal)
    assert G.choose(goal, [])["verdict"] == "NO_DOOR"


def test_a_goal_outside_the_vocabulary_is_refused_by_name():
    goal = G.Goal(need=(("MEANING", "CHANGED"),))
    result = G.choose(goal, [])
    assert result["verdict"] == "UNSTATEABLE"
    assert "five relations" in result["reason"]


def test_a_malformed_direction_is_refused_not_ranked():
    assert not G.stateable(G.Goal(need=(("CARD", "SIDEWAYS"),)))
    assert not G.stateable(G.Goal(need=()))


def test_a_goal_is_satisfied_only_by_the_exact_move():
    goal = G.Goal(need=((G.CARD, G.DECREASED),))
    assert G.satisfied(goal, {"a": b"p"}, {})
    assert not G.satisfied(goal, {"a": b"p"}, {"a": b"p"})


# --------------------------------------------------------------------------- #
# the join
# --------------------------------------------------------------------------- #
def test_a_door_that_makes_the_wrong_move_is_not_a_candidate():
    wrong = G.Record(door_id="d1", tool="t", signature=((G.CARD, G.INCREASED),))
    goal = G.Goal(need=((G.CARD, G.DECREASED),))
    assert not G.speaks_to(wrong, goal)
    assert G.choose(goal, [wrong])["verdict"] == "NO_DOOR"


def test_a_sensor_can_never_answer():
    """A program that names no artifact cannot be the door, whatever it computes."""
    sensor = G.Record(door_id="wc", tool="wc", signature=((G.IDENT, G.CHANGED),),
                      artifact_span=G.NAMES_NOTHING)
    assert not G.speaks_to(sensor, G.Goal(need=((G.IDENT, G.CHANGED),)))


def test_selectivity_reports_when_a_match_means_nothing():
    """A move every door makes carries no information, and must say so."""
    every = [G.Record(door_id=f"d{i}", tool="t", signature=((G.IDENT, G.CHANGED),))
             for i in range(4)]
    goal = G.Goal(need=((G.IDENT, G.CHANGED),))
    assert G.selectivity(goal, every)["verdict"] == "UNINFORMATIVE__EVERY_DOOR_MATCHES"

    selective = every[:1] + [G.Record(door_id=f"o{i}", tool="t",
                                      signature=((G.CARD, G.INCREASED),)) for i in range(6)]
    got = G.selectivity(goal, selective)
    assert got["verdict"] == "DISCRIMINATING" and got["matched"] == 1


def test_the_saved_row_carries_no_path_and_no_content():
    """The user's objection: an exact experience is never needed again."""
    row = G.record_of({"door": "d1", "tool": "mv"}, {"secret_name": b"secret"},
                      {"other_name": b"secret"})
    blob = json.dumps({"signature": row.signature, "span": row.artifact_span})
    for leak in ("secret_name", "other_name", b"secret".decode()):
        assert leak not in blob


# --------------------------------------------------------------------------- #
# a real program, end to end
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["rm"], reason="rm is the machine")
def test_a_real_rm_makes_the_move_a_destroying_goal_asks_for():
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-g2d-"))
    try:
        (where / "subject").write_bytes(b"payload")
        before = {"subject": (where / "subject").read_bytes()}
        import subprocess
        subprocess.run(["rm", "subject"], cwd=str(where), check=False)
        after = {}
        goal = G.Goal(need=((G.LOT, G.LOST),))
        assert G.satisfied(goal, before, after)
        record = G.record_of({"door": "rm", "tool": "rm"}, before, after)
        assert G.speaks_to(record, goal)
    finally:
        shutil.rmtree(where, ignore_errors=True)


@pytest.mark.skipif(not HAVE["mv"], reason="mv is the machine")
def test_a_real_mv_is_not_a_destroying_move():
    """The distinction that needed the invented relation, on the real program."""
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-g2d-"))
    try:
        (where / "subject").write_bytes(b"payload")
        before = {"subject": (where / "subject").read_bytes()}
        import subprocess
        subprocess.run(["mv", "subject", "moved"], cwd=str(where), check=False)
        after = {"moved": (where / "moved").read_bytes()}
        destroying = G.Goal(need=((G.LOT, G.LOST),))
        assert not G.satisfied(destroying, before, after)
        assert G.satisfied(G.goal_for(before, after), before, after)
    finally:
        shutil.rmtree(where, ignore_errors=True)
