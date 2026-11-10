"""The link is not a node. It is a word inside one, and opening a section MOVES the others.

Isolated debugging on click-collapsible-2, 12 trials per iteration:

    start                                   2/8
    + per-word StaticText nodes exist       2/8   (heuristic picked the longest run)
    + word-boundary matching                8/10
    + exact word node beats phrase node     9/12
    + normalise ALL punctuation            10/12

THE BUG THAT MATTERED MOST was not matching at all -- it was STALE COORDINATES. Opening
Section #1 moves Section #2 from y=76 to y=147. A loop that clicks tab boxes it read BEFORE
opening anything clicks paragraph text. Measured directly:

    before opening S1:  S1 y0=56   S2 y0=76    S3 y0=96
    after  opening S1:  S1 y0=56   S2 y0=147   S3 y0=167

So the rule is not "read the page" but "re-read the page before every single action".
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from canonical.runtime import text_locate_v1 as T


def _node(name, x, y, w=60, h=11, role="StaticText"):
    return {"role": role, "name": name,
            "box": {"x0": x, "y0": y, "x1": x + w, "y1": y + h, "w": w, "h": h}}


def test_a_one_word_node_beats_a_phrase_containing_the_word():
    nodes = [_node("odio quis", 6, 75), _node("Quis", 70, 75, 20)]
    assert T.best_run(nodes, "Quis")["name"] == "Quis"


def test_punctuation_does_not_defeat_an_exact_match():
    nodes = [_node("neque,.", 6, 75), _node("odio quis", 6, 90)]
    assert T.best_run(nodes, "neque")["name"] == "neque,."


def test_a_substring_of_a_longer_word_is_not_a_match():
    """'nec' is inside 'donec'; choosing that node scored 0.000 while the real node scored 0.85."""
    nodes = [_node("donec risus", 6, 75)]
    assert T.best_run(nodes, "nec") is None


def test_the_instruction_and_the_benchmark_clock_are_not_content():
    nodes = [_node('Expand the sections below, to find and click on the link "x".', 3, 3),
             _node("9 / 10sec", 242, 62)]
    assert T.best_run(nodes, "x") is None
    assert T.best_run(nodes, "10sec") is None


def test_geometry_inside_a_phrase_is_reported_as_an_estimate_not_a_fact():
    run = _node("Et blandit libero", 6, 75, 84)
    loc = T.locate_word(run, "blandit")
    assert loc["found"] and loc["confidence"] == "GEOMETRIC_ESTIMATE"
    assert 6 < loc["x"] < 90
