"""Portability of a learned goal across private names, with no change to the learner.

The source and target machines are both executed; the published answer is never used as an
oracle, and neither test nor tool calls a model.
"""
from __future__ import annotations

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
import the_question_is_a_real_run_v1 as prior  # noqa: E402
import the_role_is_portable_v1 as role  # noqa: E402

RECEIPT = ROOT / "canonical/verification/THE_ROLE_IS_PORTABLE_20261121_V1.json"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    source_root = tmp_path_factory.mktemp("role-source") / "source"
    source_root.mkdir(parents=True)
    source = env.build_filesystem(source_root)
    source.reset()
    args = env.probe_args(source.read(), "TARGET_EXISTS")
    pool = runs.traces_for(source, args, depth=3)
    terms = role.surface_neutral_terms(pool)
    literals = prior.ground_literals(pool, terms=terms)
    space = prior.hypotheses(literals)
    goals = {"portable": quotient.portable_judge, "moved": quotient.moved_judge}
    learned = {name: prior.learn(space, pool, prior.User(judge))
               for name, judge in goals.items()}
    target_root = tmp_path_factory.mktemp("role-target") / "renamed"
    target = role.renamed_filesystem(target_root)
    target_args = env.probe_args(target.read(), "TARGET_EXISTS")
    target_traces = runs.traces_for(target, target_args, depth=3)
    return pool, terms, space, learned, target_traces, role.by_text_for(target_traces)


def test_vocabulary_has_no_private_identity_and_has_a_computed_role(world):
    pool, terms, _space, _learned, _target, _by_text = world
    idents = role.private_identities(pool)
    assert idents
    for term in terms:
        assert not any(f"[{ident}]" in term.text or f"has {ident}" in term.text
                       for ident in idents)
    assert any(term.text == f"holders_changed[{env.PROBE_OLD}]" for term in terms)


def test_holder_change_is_computed_from_each_machines_own_reading(world):
    pool, _terms, _space, _learned, _target, _by_text = world
    values = {role.holder_change(trace, env.PROBE_OLD) for trace in pool}
    assert values == {True, False}


def test_both_goals_have_a_role_representation(world):
    pool, _terms, space, _learned, _target, _by_text = world
    for judge in (quotient.portable_judge, quotient.moved_judge):
        mask = sum(1 << index for index, trace in enumerate(pool) if judge(trace))
        assert 0 < mask < (1 << len(pool))
        assert mask in space


def test_moved_sentence_is_learned_without_a_private_name(world):
    pool, _terms, _space, learned, _target, _by_text = world
    result = learned["moved"]
    assert result["status"] == "IDENTIFIED"
    assert "[seed]" not in result["sentence"] and "has[seed]" not in result["sentence"]
    assert "holders_changed" in result["sentence"]


def test_old_identity_sentence_cannot_be_evaluated_on_the_renamed_machine(world):
    _pool, _terms, _space, _learned, _target, by_text = world
    with pytest.raises(ValueError, match="UNGROUNDED_LITERAL"):
        prior.evaluate(role.OLD_SENTENCE, by_text, [world[4][0]])


def test_both_learned_sentences_are_correct_on_the_renamed_machine(world):
    pool, _terms, _space, learned, target, by_text = world
    for name, judge in (("portable", quotient.portable_judge), ("moved", quotient.moved_judge)):
        predicted = prior.evaluate(learned[name]["sentence"], by_text, target)
        assert sum(bool(judge(trace)) for trace in target) > 0
        assert all(value == bool(judge(trace)) for value, trace in zip(predicted, target))


def test_receipt_records_transfer_and_zero_runtime_dependencies():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert all(row["MET"] for row in receipt["verdict"].values())
    assert "¬two_copies[probe_seed_content]" in receipt["learned"]["moved"]["sentence"]
    assert receipt["verdict"]["E4_transfer_to_renamed_machine"]["rows"]["moved"]["agreement"] == 1.0
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    source = (TOOLS / "the_role_is_portable_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import openai", "import anthropic", "import requests", "import torch"):
        assert forbidden not in source
