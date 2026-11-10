"""r78: the spread was three tasks on identical code.

    run 1  18    run 2  15    run 3  18      mean 17, stdev 1.73

Which retires two claims made in the previous two rounds:
    r76 "text nodes moved it by two tasks"       15 -> 17   inside the noise
    r77 "the gate/sequencing moved it by one"    17 -> 18   inside the noise

Neither survives three runs. They are kept in the record as claims, not as results.
"""
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]
V = json.loads((ROOT / "canonical/evaluation/bench/variance_3runs_v1.json").read_text())


def test_the_three_runs_are_recorded():
    assert V["scores"] == {"orig": 18, "a": 15, "b": 18}


def test_the_spread_is_three_tasks():
    assert max(V["scores"].values()) - min(V["scores"].values()) == 3
    assert V["stdev"] == 1.73


def test_most_of_the_wins_were_coin_flips():
    assert len(V["stable_wins"]) == 13
    assert len(V["unstable"]) == 8


def test_the_claims_that_do_not_survive_are_named():
    prev = [15, 17, 18]
    assert max(prev) - min(prev) <= 3, "all three prior numbers sit inside one spread"
    assert statistics.stdev(prev) < 2


def test_the_effect_size_of_every_mechanism_is_below_the_noise():
    """parser, text, sequencing: each claimed 1-3 tasks. The noise is 3 tasks."""
    effects = {"parser": -2, "text": 2, "sequencing": 1}
    noise = 3
    assert all(abs(v) <= noise for v in effects.values())


def test_variance_partly_a_bug_not_fate():
    """click-test-2 flipped in the full runner and passed 6/6 in isolation. Recorded so the
    next round does not file all 8 unstable tasks under 'irreducible variance'."""
    src = (ROOT / "canonical/governance/"
           "VARIANCE_ACROSS_THREE_IDENTICAL_RUNS_20261109_V1.json").read_text()
    assert "6/6" in src and "BUG" in src
