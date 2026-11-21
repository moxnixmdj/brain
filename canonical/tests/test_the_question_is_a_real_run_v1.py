"""Membership questions on real runs: negation, held-out depth, and a computed refusal.

The pool is executed once per module; the tests do not re-run the 68-step search for every
assertion. No published fix, model output, or hand-solved answer is used as an oracle.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_question_is_a_real_run_v1 as q  # noqa: E402

RECEIPT = ROOT / "canonical/verification/THE_QUESTION_IS_A_REAL_RUN_20261121_V1.json"
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "backup"}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("real-run") / "filesystem"
    root.mkdir(parents=True)
    machine = env.build_filesystem(root)
    pool = runs.traces_for(machine, ARGS, depth=3)
    literals = q.ground_literals(pool)
    space = q.hypotheses(literals)
    held = [trace for trace in runs.traces_for(machine, ARGS, depth=4) if trace not in pool]
    terms = runs.run_terms(held + pool)
    by_text = {term.text: term.holds for term in list(terms[0]) + list(terms[1])}
    return machine, pool, literals, space, held, by_text


def test_literals_are_grounded_nonconstant_and_come_in_pairs(world):
    _machine, pool, literals, _space, _held, _by_text = world
    assert all(0 < literal.mask < (1 << len(pool)) for literal in literals)
    assert any(literal.negated for literal in literals)
    assert any(not literal.negated for literal in literals)


def test_moved_goal_needs_negation_on_the_real_pool(world):
    _machine, pool, _literals, space, _held, _by_text = world
    moved = sum(1 << index for index, trace in enumerate(pool) if quotient.moved_judge(trace))
    assert moved not in q.positive_only(q.ground_literals(pool))
    assert moved in space


def test_a_question_names_an_executed_situation(world):
    _machine, pool, _literals, _space, _held, _by_text = world
    text = q.render_run(pool[0])
    assert text.startswith("start: ")
    assert "Is the goal already achieved in this situation?" in text
    assert "step 1:" in text
    assert pool[0] in pool  # identity: the rendered object came from the executed pool


def test_portable_goal_is_identified_within_the_bit_budget(world):
    _machine, pool, _literals, space, _held, _by_text = world
    result = q.learn(space, pool, q.User(quotient.portable_judge))
    assert result["status"] == "IDENTIFIED"
    assert result["questions_asked"] <= result["budget"]
    assert all(0 <= row["run"] < len(pool) for row in result["questions"])


def test_moved_goal_is_identified_with_a_negated_literal(world):
    _machine, pool, _literals, space, _held, _by_text = world
    result = q.learn(space, pool, q.User(quotient.moved_judge))
    assert result["status"] == "IDENTIFIED"
    assert q.NEGATION in result["sentence"]


def test_both_sentences_predict_deeper_runs_never_asked_about(world):
    machine, pool, literals, space, held, by_text = world
    for judge in (quotient.portable_judge, quotient.moved_judge):
        result = q.learn(space, pool, q.User(judge))
        predicted = q.evaluate(result["sentence"], by_text, held)
        assert all(value == bool(judge(trace)) for value, trace in zip(predicted, held))


def test_computed_out_of_class_goal_fails_closed(world):
    machine, pool, literals, space, held, by_text = world
    full = (1 << len(pool)) - 1
    control = next(first.mask ^ second.mask
                   for first, second in itertools.combinations(literals, 2)
                   if 0 < first.mask ^ second.mask < full
                   and (first.mask ^ second.mask) not in space)
    index_of = {trace: index for index, trace in enumerate(pool)}
    judge = lambda t: bool((control >> index_of[t]) & 1)  # noqa: E731
    result = q.learn(space, pool, q.User(judge))
    # A finite membership-query budget can end on a sentence that fits every *asked* run.
    # Verification against every executed run is what turns that into a refusal.
    terms = runs.run_terms(pool)
    pool_by_text = {term.text: term.holds for term in list(terms[0]) + list(terms[1])}
    predicted = q.evaluate(result["sentence"], pool_by_text, pool)
    mismatches = [index for index, (trace, guess) in enumerate(zip(pool, predicted))
                  if guess != bool(judge(trace))]
    assert len(mismatches) > 0
    assert "sentence" in result  # the learner itself did not know; the verifier caught it


def test_receipt_records_six_criteria_and_zero_runtime_dependencies():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert all(row["MET"] for row in receipt["verdict"].values())
    assert receipt["verdict"]["D2_negation_is_necessary"]["positive_representations"] == 0
    assert receipt["verdict"]["D4_deeper_held_out"]["rows"]["moved"]["agreement"] == 1.0
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    source = (TOOLS / "the_question_is_a_real_run_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import openai", "import anthropic", "import requests", "import torch"):
        assert forbidden not in source
