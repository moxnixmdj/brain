"""Regression guard for a round whose P3 FAILED. Pin the failure and its named cause.

`THE_LOOP_REPEATS_ON_A_SECOND_GOAL_20261123_V1.json` shows the same loop closing a second residual
on a second goal, then failing held-out because the grammar cannot state "the holder of THIS
content changed". Editing that receipt into a success would be a defect.
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
import the_loop_repeats_on_a_second_goal_v1 as tool  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_LOOP_REPEATS_ON_A_SECOND_GOAL_20261123_V1.json"


def test_the_two_new_machines_are_real_and_the_overwrite_changes_only_content(tmp_path):
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    extra = tool.build_extra(tmp_path / "extra")
    extra.reset()
    before = tuple(extra.read())
    fourth = extra.atoms[3]
    assert env.execute(fourth, extra, args)["all_exit_zero"] is True
    after = tuple(extra.read())
    assert len(after) == len(before) - 1
    assert all(content == env.PROBE_OLD for _i, content in after if content == env.PROBE_OLD)

    overwrite = tool.build_overwrite(tmp_path / "overwrite")
    overwrite.reset()
    before = tuple(overwrite.read())
    assert env.execute(overwrite.atoms[3], overwrite, args)["all_exit_zero"] is True
    after = tuple(overwrite.read())
    assert len(after) == len(before)  # cardinality unchanged
    assert not any(content == env.PROBE_OLD for _i, content in after)  # probe content gone


def test_a_real_move_with_a_recreated_identity_is_the_named_failure(tmp_path):
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machine = tool.build_overwrite(tmp_path / "overwrite")
    traces = runs.traces_for(machine, args, depth=3)
    whole, end_only = runs.run_terms(traces)
    available = {term.text: term for term in list(whole) + list(end_only)}
    survivors = [trace for trace in traces
                 if quotient.moved_judge(trace)
                 and not (available["monotone[probe_seed_content]"].holds(trace)
                          and available["present_then_absent[seed]"].holds(trace))]
    assert survivors, "the named grammar failure disappeared"
    assert all(any(ident == "seed" and content != env.PROBE_OLD
                   for ident, content in trace[-1]) for trace in survivors)


def test_receipt_pins_p3_as_failed_and_the_cause_as_named():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["all_criteria_met"] is False
    verdict = data["verdict"]
    assert verdict["P1_second_goal_has_a_residual"]["MET"] is True
    assert verdict["P2_one_run_collapses_it"]["MET"] is True
    assert verdict["P3_exact_on_held_out"]["MET"] is False
    assert verdict["P3_exact_on_held_out"]["prediction"]["false_rejects"] == 4
    assert verdict["P3_exact_on_held_out"]["prediction"]["false_accepts"] == 0
    assert verdict["P3_exact_on_held_out"]["discarded_wrong"] == 9
    assert verdict["P4_what_to_save"]["MET"] is True
    assert verdict["P5_zeros_and_no_cross_goal_smuggling"]["old_relation_status"] == \
        "REFUSED__VOCABULARY_NOT_RECOMPUTED"
    diag = data["diagnostics_of_the_p3_failure"]
    assert diag["false_reject_witnesses"] == 4
    assert diag["witnesses_with_seed_recreated_under_different_content"] == 4
    assert "holder of THIS content changed" in diag["named_cause"]
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
