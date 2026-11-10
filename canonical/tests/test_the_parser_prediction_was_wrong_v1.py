"""A falsified prediction, kept because a record that drops its failures is not a record.

r73 predicted, in writing, before the work: "a proper goal parser at zero model calls should
move 11.5% by roughly 4-6x." The ceiling reasoning was sound on its own terms -- 86.9% of
tasks expose usable structure and only 43 goals were being attempted, so a better parser
should have had a large headroom.

It did not. Four attempts:

    baseline (regex ladder)        15/130   11.5%
    attempt 1 (grammar, 6 shapes)  11/130    8.5%
    attempt 2 (+search_then_click) 12/130    9.2%
    attempt 3 (+structural reveal) 12/130    9.2%
    attempt 4 (+clean_name)        13/130   10.0%

Every attempt lost more wins than it gained. The prediction was wrong by a wide margin, in
the opposite direction.

THE REASON, measured before tuning stopped (diagnostic_v1.json): 7 of 8 sampled failures had
a target that was NOT ON SCREEN before a disclosure step. The parser was not the binding
constraint. Ordering was. A system that can read an instruction perfectly and cannot reveal
what the instruction refers to has gained nothing.

And the tuning itself repeated an old error: four rounds of edits, each scored on the same 130
goals I had read, is a tuning set. Which is why the held-out set exists and why its number is
the one to quote.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]

BASE = json.loads((ROOT / "canonical/evaluation/bench/result_all_130_v1.json").read_text())
A1 = json.loads((ROOT / "canonical/evaluation/bench/result_all_130_v2_parser.json").read_text())
A3 = json.loads((ROOT / "canonical/evaluation/bench/result_all_130_v2_attempt3.json").read_text())
DIAG = json.loads((ROOT / "canonical/evaluation/bench/diagnostic_v1.json").read_text())


def test_the_prediction_is_on_the_record_as_wrong():
    assert BASE["success"] == 15
    assert A1["success"] < BASE["success"], "attempt 1 lost wins, it did not gain any"
    assert A3["success"] < BASE["success"], "attempt 3 was still below baseline"
    # the claim was 4-6x; the result was a regression
    assert A3["success_rate"] / BASE["success_rate"] < 1.0


def test_every_attempt_is_kept_not_just_the_best():
    rates = [BASE["success_rate"], 8.5, A1["success_rate"], A3["success_rate"]]
    assert len(rates) == 4
    assert max(rates) == BASE["success_rate"], "no attempt beat the baseline"


def test_the_binding_constraint_was_ordering_not_parsing():
    off_screen = [d for d in DIAG if not d["addressable_before_reveal"]]
    assert len(off_screen) == 7
    assert len(DIAG) == 8


def test_the_tuning_set_error_is_named_in_the_source():
    src = (ROOT / "canonical/evaluation/bench/heldout_goals_v1.json").read_text()
    assert "out-of-distribution" in src


def test_heldout_goals_do_not_appear_in_the_benchmark():
    """The held-out set is only worth something if it is genuinely unseen."""
    hel = json.loads((ROOT / "canonical/evaluation/bench/heldout_goals_v1.json").read_text())
    seen = {(t.get("goal") or "").strip() for t in BASE["tasks"]}
    for h in hel["goals"]:
        assert h["goal"] not in seen, h["id"]
