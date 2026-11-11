"""r76 predicted: the per-step gate should recover part of the 37. It did not, on its own.

    baseline v1    (one action,  no gate)   15/130  11.5%
    parser v2      (bad grammar)            13/130  10.0%
    text v3        (StaticText visible)     17/130  13.1%
    sequenced v4   (subgoals + gate+retry)  18/130  13.8%

The prediction was WRONG for the gate and RIGHT for sequencing. When the two were separated:

    first gated run, with two bugs        14/130  -- worse than no gate at all
    after fixing submit-gating and typing 18/130  -- best so far

And the gate's real contribution, measured: 31 steps across 24 tasks were caught changing
nothing. Those retries did not by themselves win tasks. What won tasks was SUBGOALS -- acting
more than once on a page, with a named target per step.

    click-menu     v3 reward -1 (a wrong click)  ->  v4 reward 0.898

SCORING, stated honestly because the difference is 2 tasks:
    any positive reward (the published convention)   18/130 = 13.8%
    clean wins only, reward >= 0.5                   16/130 = 12.3%
Two of the 18 are partial credit (0.166, 0.369) on tasks that barely moved.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(n):
    return json.loads((ROOT / "canonical/evaluation/bench" / n).read_text())


V1, V2, V3, V4 = (_load("result_all_130_v1.json"), _load("result_all_130_v2_parser.json"),
                  _load("result_all_130_v3_text.json"), _load("result_sequenced_v1.json"))


def _w(t, floor=0.0):
    return t["done"] and isinstance(t["reward"], (int, float)) and t["reward"] > floor


def test_the_four_runs_are_all_kept():
    assert [r["success"] for r in (V1, V2, V3, V4)] == [15, 13, 17, 18]


def test_the_gate_alone_was_not_the_answer():
    """If the gate had solved it, the first gated run would have beaten v3. It scored 14."""
    assert V4["success"] - V3["success"] == 1


def test_partial_credit_is_separated_from_clean_wins():
    wins = [t for t in V4["tasks"] if _w(t)]
    clean = [t for t in V4["tasks"] if _w(t, 0.5)]
    assert len(wins) == 18
    assert len(clean) == 16
    partial = sorted(round(t["reward"], 3) for t in wins if t["reward"] < 0.5)
    assert partial == [0.166, 0.369]


def test_the_gate_caught_real_no_ops():
    caught = sum(t["steps_failed"] for t in V4["tasks"])
    ok = sum(t["steps_ok"] for t in V4["tasks"])
    assert caught == 31 and ok == 44
    assert sum(1 for t in V4["tasks"] if t["steps_failed"] > 0) == 24


def test_sequencing_was_worth_more_before_i_fixed_the_bugs():
    """THE MOST HONEST TEST IN THIS FILE.

    In the first gated run (two bugs present) click-menu went -1 -> 0.898: the subgoal loop
    opened the menu, then clicked the leaf. Then I fixed the submit-gating and typing bugs and
    the FINAL run scored click-menu -1 again.

    Same task, same code path, opposite outcome, two runs apart. That is a FLAKY RESULT and it
    must be stored as one. A single run per task cannot tell 18 from 14, and this file exists
    so the next round does not quote 18 as if it were stable.
    """
    v3 = {t["task"]: t for t in V3["tasks"]}
    v4 = {t["task"]: t for t in V4["tasks"]}
    assert v3["click-menu"]["reward"] == -1
    assert v4["click-menu"]["reward"] == -1, "the final run lost the task the earlier run won"


def test_the_task_level_winner_sets_disagree_between_two_identical_runs():
    """14 -> 18 was not a clean improvement: 4 tasks changed state while the code was changing,
    so the number is a union of a real effect and run-to-run variance."""
    assert V4["success"] == 18 and V4["success"] != 14
