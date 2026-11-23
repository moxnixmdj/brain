"""Tests for `canonical/tools/the_environment_answers_the_question_v1.py`.

Plain-tree tests: no conftest, no patched loaders, no historical git reads, no pins. Every
execution below runs a real program. The receipt test is a regression guard against overclaiming,
not a new capability claim.
"""
from __future__ import annotations

import inspect
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
import the_environment_answers_the_question_v1 as tool  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.json"


def test_the_two_new_machines_execute_real_commands(tmp_path):
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    for name, builder in (("copy_two", tool.build_copy_two), ("tee_copy", tool.build_tee_copy)):
        root = tmp_path / name
        machine = builder(root)
        machine.reset()
        initial = tuple(machine.read())
        bulk = next(atom for atom in machine.atoms if atom.ident.endswith("A3"))
        result = env.execute(bulk, machine, args)
        after = tuple(machine.read())
        assert result["all_exit_zero"] is True
        assert sum(1 for _ident, content in after if content == env.PROBE_NEW) == 2
        assert after != initial
    # a new environment really arrives with different identities
    left = tool.build_copy_two(tmp_path / "copy_two")
    right = tool.build_tee_copy(tmp_path / "tee_copy")
    left.reset()
    right.reset()
    assert tuple(left.read()) != tuple(right.read())


def test_one_judgment_on_one_run_collapses_the_class_and_the_judge_sees_no_statement():
    candidates = tool.gate.from_predicates([
        ("statement_A", lambda trace: len(trace[-1]) > 1),
        ("statement_B", lambda trace: len(trace[-1]) > 3),
    ])
    # one run separates A from B; the user rejects that run
    separating = ((("f", "x"), ("g", "x")), (("f", "x"), ("g", "x"), ("h", "x")))
    seen = []

    def judge(trace):
        seen.append(trace)
        return False

    answer = tool.ask_the_environment(candidates, [separating], judge)
    assert answer["action"] == "COLLAPSED"
    assert answer["separating_runs"] == 1
    assert answer["judgments_on_runs"] == 1
    assert answer["questions_about_statements"] == 0
    assert answer["survivors"] == ["statement_B"]
    assert seen == [separating]  # the judge saw exactly one run and no statement text
    source = inspect.getsource(tool.ask_the_environment)
    assert "judge(chosen)" in source
    assert "judge(candidate" not in source


def test_no_separating_run_refuses_to_ask():
    candidates = tool.gate.from_predicates([
        ("same_A", lambda trace: True),
        ("same_B", lambda trace: True),
    ])
    answer = tool.ask_the_environment(candidates, [(("f", "x"),)], lambda trace: True)
    assert answer["action"] == "NO_QUESTION"
    assert answer["judgments_on_runs"] == 0
    assert answer["questions_about_statements"] == 0
    assert answer["class"] == 2


def test_replay_recomputes_the_vocabulary_and_unlearning_is_a_file_delete(tmp_path):
    store = tmp_path / "relation.json"
    fit = tool.Fit(terms=[], combos=[()], texts=["unused"], runs=0, hypotheses=0,
                   behaviours=0, truth=0, seconds=0.0)
    record = tool.save_relation(store, fit, (),
                                {"evidence_sha256": "x", "judgment_on_the_run": False,
                                 "chosen_run_steps": 1})
    assert record["schema"] == tool.STORE_SCHEMA
    # a term that this machine's own executed runs cannot express is refused, not trusted
    record["relation"]["texts"] = ["term_that_does_not_exist"]
    store.write_text(json.dumps(record), encoding="utf-8")
    trace = ((("seed", env.PROBE_OLD),),)
    refused = tool.replay(store, [trace], lambda t: False)
    assert refused["status"] == "REFUSED__VOCABULARY_NOT_RECOMPUTED"
    store.unlink()
    assert tool.replay(store, [trace], lambda t: False)["status"] == "REFUSED__NO_CARRIED_RELATION"


def test_exact_experience_abstains_where_the_relation_does_not():
    select = [((("seed", env.PROBE_NEW),),)]
    held = [((("alpha", env.PROBE_NEW),),)]
    raw = tool.raw_experience_control(select, held, lambda trace: True)
    assert raw["abstentions"] == 1
    assert raw["exact_action_transfer"] == "NOT_APPLICABLE__ACTION_VOCABULARY_DIFFERS"


def test_receipt_keeps_the_pre_registered_criteria_and_never_overclaims():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["all_criteria_met"] is True
    verdict = data["verdict"]
    assert all(row["MET"] is True for row in verdict.values())
    assert data["fit"]["residual_class"] == 2
    assert len(data["fit"]["residual_texts"]) == 2
    assert data["question"]["questions_about_statements"] == 0
    assert data["question"]["judgments_on_runs"] == 1
    assert data["question"]["class"] == 1
    h3 = verdict["H3_held_out_prediction"]["prediction"]
    assert h3["false_accepts"] == 0 and h3["false_rejects"] == 0
    assert h3["abstentions"] == 0
    assert verdict["H3_held_out_prediction"]["discarded_statement_wrong_on"] > 0
    assert verdict["H4_no_contrast_refuses"]["gate_action"] == "NO_QUESTION"
    assert verdict["H6_what_to_save"]["raw_experience"]["abstentions"] > 0
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0
    assert data["cost"]["seconds"] > 0
    assert verdict["H7_zeros_and_real_execution"]["guide"]["decided_the_choice"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
