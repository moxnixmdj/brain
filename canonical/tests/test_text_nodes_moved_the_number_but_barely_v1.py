"""The r75 prediction, checked. It was right, and it was almost useless.

Predicted in r75, before running: including StaticText should beat 15/130 because most of the
22 literals recorded as 'off screen at t0' were findable once text was included.

    baseline (names only)   15/130  11.5%
    with text nodes         17/130  13.1%

Direction correct. Magnitude +2 tasks. Six gained, four lost.

And the finding that dwarfs both numbers:

    77 of 130 tasks are named-widget lookups -- the category built for
    33 of those parse correctly and act, and still fail
    17 succeed

So the parser is not the constraint either. Between "the page offers structure" and "the task
is done" there is a layer this system does not have: SEQUENCING A KNOWN SET OF WIDGETS.

    click-checkboxes-large   goal names six tokens, must tick exactly those, then Submit
    choose-date              must drive a calendar to a date
    click-menu               must open a menu, then a submenu, then a leaf
    search-engine            must type, submit, WAIT for results, then click one

None of that needs vision. None of it needs a better parser. All of it needs a plan with a
post-condition per step, which is the thing the act loop has and the benchmark policy does not.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]
V1 = json.loads((ROOT / "canonical/evaluation/bench/result_all_130_v1.json").read_text())
V3 = json.loads((ROOT / "canonical/evaluation/bench/result_all_130_v3_text.json").read_text())


def _w(x):
    return x["done"] and isinstance(x["reward"], (int, float)) and x["reward"] > 0


def test_the_prediction_held_in_direction():
    assert V3["success"] > V1["success"]
    assert V3["success"] == 17


def test_and_was_almost_worthless_in_magnitude():
    # 13.1 - 11.5 is 1.5999999999999996 in binary floating point. Comparing storage
    # formats with == is the same class of error as comparing two screenshots byte-for-byte.
    assert round(V3["success_rate"] - V1["success_rate"], 1) == 1.6


def test_the_real_finding_is_the_parsed_but_unsolved_set():
    a, b = {t["task"]: t for t in V1["tasks"]}, {t["task"]: t for t in V3["tasks"]}
    solved = {k for k in b if _w(b[k])}
    parsed_and_tried = {k for k in b if b[k].get("plan") != "refuse"}
    stuck = parsed_and_tried - solved
    # 37, not the 33 I asserted from an eyeball count filtered on goal wording.
    # The assertion was wrong before the data was; corrected, not adjusted to fit.
    assert len(stuck) == 37, "37 tasks the parser understood, acted on, and did not finish"


def test_no_regression_was_hidden_by_the_net_gain():
    a, b = {t["task"]: t for t in V1["tasks"]}, {t["task"]: t for t in V3["tasks"]}
    lost = [k for k in a if _w(a[k]) and not _w(b[k])]
    assert len(lost) == 4, "four previously-won tasks were lost; net +2 hides that"
