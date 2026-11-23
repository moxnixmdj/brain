"""Regression guard for a FAILED round. Do not turn this receipt into a success by editing it.

`THE_RELATION_REFUSES_THE_UNSTATABLE_20261123_V1.json` falsifies the round's own expectation:
the grammar CAN state the holder-history goal, and the carried relation refuses because its terms
do not recompute on the new machine. The tests pin that honest failure.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(TOOLS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_relation_refuses_the_unstatable_v1 as tool  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_RELATION_REFUSES_THE_UNSTATABLE_20261123_V1.json"


def test_a_real_move_and_a_real_copy_then_delete_end_in_the_same_state(tmp_path):
    machine = tool.build_move(tmp_path / "move")
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    traces = runs.traces_for(machine, args, depth=3)
    pairs = tool.final_state_pairs(traces)
    assert pairs, "no real move / copy-then-delete pair was executed"
    move, copy_then_delete = pairs[0]
    assert move[-1] == copy_then_delete[-1]
    assert quotient.moved_judge(move) is True
    assert quotient.moved_judge(copy_then_delete) is False


def test_receipt_pins_the_falsification_and_refuses_to_overclaim():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["all_criteria_met"] is False
    verdict = data["verdict"]
    assert verdict["N1_carried_relation_does_not_travel_here"]["MET"] is True
    assert verdict["N1_carried_relation_does_not_travel_here"]["carried"]["status"] == \
        "REFUSED__VOCABULARY_NOT_RECOMPUTED"
    assert verdict["N2_no_false_accept_when_unstatable"]["verdict"] == "VOID__THE_GOAL_WAS_STATABLE"
    assert verdict["N3_grammar_cannot_state_the_goal"]["MET"] is False
    assert verdict["N3_grammar_cannot_state_the_goal"]["goal_minimal_statements"] == 2
    assert "FALSIFIED" in verdict["N3_grammar_cannot_state_the_goal"]["reason"]
    assert all(row["identical_final_state"]
               for row in verdict["N4_same_final_state_real_runs"]["pairs"])
    assert data["falsified_expectation"]
    assert "re-fit" in data["next_bottleneck"]
    assert "measurement defect" in data["evaluated_after_the_run"]
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
