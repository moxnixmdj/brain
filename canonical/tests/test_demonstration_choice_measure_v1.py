"""Which demonstration is handed over is a decision that can be made before any outcome is known.

The measured claim in `canonical/tools/demonstration_choice_measure_v1.py` is narrow and stated
before it was run: the *reach* of a candidate demonstration's own lesson -- how many of the other
candidate files that lesson fits -- predicts, without consulting any outcome, how much of the work
the people on that task actually did the demonstration will recover.

These tests pin the three things that could quietly make that claim false:

* the reach is computed without the outcome. If it ever reads a target's "after" text, the number
  is a peek at the answer and the whole result is void;
* the choice rule is deterministic and independent of the order `gh` returned the files in, so a
  different listing cannot manufacture a better number;
* the summary refuses to report a "choice" on a task where every candidate ties, because there a
  choice is trivially both the best and the worst and counting it inflates the score.

The recorded runs are checked too, but only for shape: the tests do not assert a correlation value,
because a value is a measurement of one corpus on one day and pinning it would turn a result into a
tolerance. What is pinned is that the record says which arm it used, which organ hash it used, and
that its own pre-registered prediction is reported rather than "corrected" afterwards.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import demonstration_choice_measure_v1 as choice  # noqa: E402

VERIFICATION = ROOT / "canonical" / "verification"
STRICT = VERIFICATION / "DEMONSTRATION_CHOICE_STRICT_20261112_V1.json"
CEILING = VERIFICATION / "DEMONSTRATION_CHOICE_CEILING_20261112_V1.json"

#: One task with three candidates. Only the second is a lesson that generalises: the first changes
#: a name nobody else uses, the third does not change anything a rule can learn.
TASK = [
    {"path": "a.py", "before": "def f(x):\n    return x == None\n",
     "after": "def f(x):\n    return x is None\n"},
    {"path": "b.py", "before": "def g(y):\n    return y.k == None\n    \n\ndef h(z):\n    return z == None\n",
     "after": "def g(y):\n    return y.k is None\n    \n\ndef h(z):\n    return z is None\n"},
    # A statement added: the learner refuses this outright, which is its documented ceiling.
    {"path": "c.py", "before": "def f(a):\n    return a\n",
     "after": "def f(a):\n    b = a\n    return b\n"},
]


def test_reach_counts_the_siblings_a_lesson_fits():
    reach = choice.reach_of(1, TASK)
    assert reach["learned"] is True
    # b.py's lesson is about `== None` in general, so it fits a.py. c.py holds no such code.
    assert reach["reach"] == 1
    assert reach["fits_itself"] is True


def test_a_lesson_about_one_name_reaches_nothing_else():
    reach = choice.reach_of(0, TASK)
    # `x == None` is a rule about the name `x`; nothing else in the task has that form.
    assert reach["reach"] == 0


def test_a_candidate_that_cannot_be_learned_has_no_reach():
    reach = choice.reach_of(2, TASK)
    assert reach["learned"] is False
    assert reach["reach"] == 0


def test_reach_never_reads_the_answering_text(monkeypatch):
    """The reach must be computable from the files as they are, with every "after" erased."""
    stripped = []
    for entry in TASK:
        poisoned = dict(entry)
        poisoned["after"] = "raise AssertionError('the reach read the answer')\n"
        stripped.append(poisoned)
    # Learning needs the example's own after; only the SIBLINGS' after texts may never be read.
    # So poison everything except the candidate under test and confirm the count is unchanged.
    for index in range(len(TASK)):
        for_reach = [dict(entry) for entry in TASK]
        for other in range(len(TASK)):
            if other != index:
                for_reach[other]["after"] = "raise AssertionError('read the answer')\n"
        assert choice.reach_of(index, for_reach)["reach"] == choice.reach_of(index, TASK)["reach"]


def test_the_choice_does_not_depend_on_the_order_the_files_arrived_in():
    forwards = choice.one_task("t", TASK, measure_outcome=True)
    backwards = choice.one_task("t", list(reversed(TASK)), measure_outcome=True)
    assert forwards["chosen_by_reach"] == backwards["chosen_by_reach"]


def test_ties_are_broken_by_specificity_then_path_and_not_by_luck():
    # The same shape twice, at the same name: two equally general lessons, a genuine tie.
    left = {"path": "m.py", "before": "def f(p):\n    return p == None\n",
            "after": "def f(p):\n    return p is None\n"}
    right = {"path": "n.py", "before": "def f(p):\n    return p == None\n",
             "after": "def f(p):\n    return p is None\n"}
    row = choice.one_task("tie", [left, right], measure_outcome=False)
    reaches = [candidate["reach"] for candidate in row["candidates"]]
    assert reaches == [1, 1], "each lesson fits the other; the test's tie is real"
    picked = choice.one_task("tie", [left, right], measure_outcome=True)["chosen_by_reach"]
    assert picked == "m.py", "the first path wins a tie, whatever order the files came in"


def test_a_task_where_every_candidate_ties_reports_no_choice_as_a_win():
    left = {"path": "m.py", "before": "def f(p):\n    return p == None\n",
            "after": "def f(p):\n    return p is None\n"}
    right = {"path": "n.py", "before": "def f(p):\n    return p == None\n",
             "after": "def f(p):\n    return p is None\n"}
    row = choice.one_task("tie", [left, right], measure_outcome=True)
    assert row["candidates_differ"] is False
    summary = choice.summarise([row])
    assert summary["tasks_where_candidates_differ"] == 0
    assert summary["tasks_where_the_choice_was_the_best_possible"] == 0
    assert summary["tasks_where_the_choice_was_the_worst_possible"] == 0


def test_a_summary_with_no_variation_refuses_to_report_a_correlation():
    flat = choice.pearson([1.0, 1.0, 1.0], [0.0, 0.5, 1.0])
    assert flat["r"] is None
    assert flat["reason"] == "NO_VARIATION_IN_ONE_AXIS"


def test_the_arm_is_the_recorded_instruments_own_entry_point():
    from canonical.tools import repeated_change_one_example_measure_v1 as measure
    for arm, name in choice.ARMS.items():
        assert callable(getattr(measure, name)), (arm, name)


@pytest.mark.parametrize("record", [STRICT, CEILING], ids=["strict", "every_try_kept"])
def test_the_recorded_runs_say_what_they_are_and_keep_the_prediction(record):
    if not record.is_file():
        pytest.skip("the recorded run is not in this tree")
    held = json.loads(record.read_text(encoding="utf-8"))
    assert held["authority"].startswith("NONE")
    assert held["terminal_authority"] is False
    assert held["model_calls"] == 0
    assert held["incremental_spend_usd"] == 0
    assert held["arm"] in choice.ARMS
    # the organ that was measured is named by hash, so a later change to it is visible
    assert held["code_sha256"][choice.ORGAN] != "ABSENT"
    prediction = held["summary"]["pre_registered_prediction"]
    assert prediction, "the prediction must be on the record"
    assert held["summary"]["prediction_held"] == all(prediction.values())
    # a failure is allowed; a failure that is not reported is not
    for key, value in held["summary"].items():
        assert not (key.startswith("prediction") and value is None)
    # the honest reading must be on the record, not only the flattering one
    honest = held["summary"]["honest_capture"]
    assert "capture_where_the_rule_decided_mean" in honest
    assert honest["tasks_where_the_rule_actually_decided"] + honest["tasks_where_the_top_reach_was_tied"] \
        == held["summary"]["tasks_where_candidates_differ"]


def test_a_tie_broken_by_path_is_not_counted_as_a_decision_the_rule_made():
    """The path is whatever `gh` called the file. Crediting it would be crediting luck.

    Built from the recorded run rather than a fixture, because the interesting case -- candidates
    that share the greatest reach but do NOT recover the same amount -- is what the real corpus
    contains and a two-file fixture cannot be made to show.
    """
    if not STRICT.is_file():
        pytest.skip("the recorded run is not in this tree")
    held = json.loads(STRICT.read_text(encoding="utf-8"))
    honest = held["summary"]["honest_capture"]
    if not honest["tasks_where_the_top_reach_was_tied"]:
        pytest.skip("no ties at the greatest reach in this run")
    tied = [row for row in honest["per_task"] if row["group"] > 1]
    assert tied, "a tie is a group larger than one"
    # for a tied task the rule is credited with the group's mean, never with its best member
    for row in tied:
        assert row["capture_expected"] <= row["capture_best_in_group"]
    assert honest["capture_where_the_top_reach_was_tied_mean"] <= \
        st.mean([row["capture_best_in_group"] for row in tied])
    # and the flattering path-tie-broken figure is the larger of the two, by construction
    assert held["summary"]["share_of_best_captured_mean"] >= \
        honest["honest_capture_all_differing_tasks_mean"] - 1e-9


def test_a_unique_top_reach_is_counted_as_a_decision():
    decided = choice.honest_capture([choice.one_task("t", TASK, measure_outcome=True)])
    assert decided["tasks_where_the_rule_actually_decided"] == 1
    assert decided["tasks_where_the_top_reach_was_tied"] == 0


def test_the_train_and_held_out_split_can_be_made_before_the_outcome_is_read():
    """The choice rule may be fitted on one half of the tasks and scored on the other."""
    tasks = [choice.one_task(f"t{index}", [dict(entry) for entry in TASK], measure_outcome=True)
             for index in range(4)]
    fitted, scored = tasks[:2], tasks[2:]
    summary = choice.summarise(scored)
    assert summary["tasks"] == 2
    assert "pre_registered_prediction" in summary
    for task in fitted:
        assert "chosen_by_reach" in task
