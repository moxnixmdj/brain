"""The computed language intake: a witness question, a measured falsification, a repaired sentence.

These tests run real machines for the falsifier and the fifth-environment check. They do not
re-run the 555 fitted runs -- that receipt is an input, not something to re-litigate here.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_witness_is_the_question_v1 as w  # noqa: E402

UPSTREAM = (ROOT / "canonical/verification/"
            "BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.json")
RECEIPT = (ROOT / "canonical/verification/"
           "THE_WITNESS_IS_THE_QUESTION_20261121_V1.json")


def residual():
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    return list(upstream["verdict"]["B3_the_residual_survives_every_machine"]["texts"])


def grounded():
    situations = w.synthetic_traces()
    return situations, w.build_statements(residual(), situations)


def test_residual_is_two_and_grounded_in_the_existing_receipt():
    situations, statements = grounded()
    assert len(statements) == 2
    for statement in statements:
        truths = {statement.holds(trace) for trace in situations}
        assert truths == {True, False}


def test_witness_is_a_pre_existing_copy_and_splits_the_class():
    situations, statements = grounded()
    witness = w.find_witness(statements, situations)
    assert witness is not None and witness.split
    assert w.render_question(witness.trace).counts[0] == 1
    assert set(witness.truth) == {True, False}


def test_question_is_a_situation_not_a_hypothesis_name():
    situations, statements = grounded()
    question = w.render_question(w.find_witness(statements, situations).trace)
    assert "Is the goal already achieved in this situation?" in question.text
    assert "one copy" in question.text
    assert "step 1:" in question.text


def test_one_verdict_closes_the_two_sentence_class():
    situations, statements = grounded()
    result = w.intake(statements, situations, w.User(quotient.portable_judge))
    assert result["status"] == "CLOSED"
    assert result["questions_asked"] == 1 == result["budget"]
    assert result["chosen"] == "created_once[probe_new_content]"


def test_equivalent_class_refuses_without_guessing():
    situations, statements = grounded()
    result = w.intake([statements[0], statements[0]], situations,
                      w.User(quotient.portable_judge))
    assert result["status"] == "NO_SEPARATING_WITNESS"
    assert "chosen" not in result


def test_non_boolean_verdict_refuses():
    situations, statements = grounded()
    result = w.intake(statements, situations, w.User(lambda _trace: None))
    assert result["status"] == "INVALID_ANSWER"


def test_fourth_machine_falsifies_the_one_bit_sentence(tmp_path):
    situations, statements = grounded()
    chosen = w.intake(statements, situations, w.User(quotient.portable_judge))["chosen"]
    machine = w.preloaded_filesystem(tmp_path / "audit")
    args = env.probe_args(machine.read(), "TARGET_ABSENT")
    traces = runs.traces_for(machine, args, depth=2)
    statement = next(s for s in statements if s.text == chosen)
    false_accepted = [t for t in traces
                      if statement.holds(t) and not quotient.portable_judge(t)]
    assert len(false_accepted) > 0


def test_counterexample_repair_adds_a_user_confirmed_grounded_term(tmp_path):
    situations, statements = grounded()
    user = w.User(quotient.portable_judge)
    chosen_text = w.intake(statements, situations, user)["chosen"]
    chosen = next(s for s in statements if s.text == chosen_text)
    machine = w.preloaded_filesystem(tmp_path / "audit")
    args = env.probe_args(machine.read(), "TARGET_ABSENT")
    traces = runs.traces_for(machine, args, depth=2)
    terms = runs.run_terms(traces)
    repaired = w.repair_from_user(chosen, list(terms[0]) + list(terms[1]), traces, user)
    assert repaired["status"] == "REPAIRED"
    assert "final:count[probe_new_content]==1" in repaired["text"]
    assert any(row["answer"] is False for row in repaired["questions"])


def test_repaired_sentence_holds_on_a_fifth_machine_never_used_in_fitting(tmp_path):
    situations, statements = grounded()
    user = w.User(quotient.portable_judge)
    chosen_text = w.intake(statements, situations, user)["chosen"]
    chosen = next(s for s in statements if s.text == chosen_text)
    audit = w.preloaded_filesystem(tmp_path / "audit")
    args = env.probe_args(audit.read(), "TARGET_ABSENT")
    audit_traces = runs.traces_for(audit, args, depth=2)
    audit_terms = runs.run_terms(audit_traces)
    repaired = w.repair_from_user(chosen, list(audit_terms[0]) + list(audit_terms[1]),
                                  audit_traces, user)
    repaired_statement = w.statement_from_text(
        repaired["text"], {t.text: t for t in list(audit_terms[0]) + list(audit_terms[1])})

    held = w.two_atom_filesystem(tmp_path / "held")
    held_traces = runs.traces_for(held, env.probe_args(held.read(), "TARGET_ABSENT"), depth=3)
    labels = [quotient.portable_judge(t) for t in held_traces]
    assert sum(labels) > 0
    assert all(repaired_statement.holds(t) == label for t, label in zip(held_traces, labels))


def test_receipt_records_the_falsification_and_all_declared_criteria():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert all(row["MET"] for row in receipt["verdict"].values())
    assert receipt["verdict"]["C4_one_bit_sentence_is_falsified"]["over_accepted_runs"] > 0
    assert receipt["declared_criteria"]["C4"].startswith("the one-bit sentence is FALSIFIED")
    assert receipt["verdict"]["C6_fifth_machine_prediction"]["all_candidates_agree"] is True
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_tool_has_no_model_or_network_dependency_in_its_source():
    source = (TOOLS / "the_witness_is_the_question_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import openai", "import anthropic", "import requests",
                      "from transformers", "import torch", "urllib.request"):
        assert forbidden not in source
