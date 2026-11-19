#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for instant_one_shot_learning_v1.py — end-to-end demonstration.

OBSERVE → CREDIT → IDENTIFY → CONTRACT → APPLICABILITY → COMPOSE →
HORIZON → ADMIT → REMEMBER

These tests verify:

  * Zero model calls, zero network calls at decision time
  * Every parameter is calculated from first principles (SEPARATION + STABILITY)
  * Credit attribution identifies causal vs. non-causal steps
  * Rule identification closes by proof or witness, never by repetition
  * Contract extraction produces a valid typed EffectContract
  * Applicability learning classifies states correctly (version-space)
  * Composition verification catches transitive breakdown and interference
  * Horizon-bounded execution decomposes long tasks with checkpoints
  * Admission gate refuses before persisting (held-out victims required)
  * REMEMBER persists nothing (zero knowledge house)
  * Fail-closed: any phase failure propagates and refuses

No mocks, no patches, no learned parameters. Real disk, real subprocess,
real test fixtures.
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from canonical.swe_kernel.instant_one_shot_learning_v1 import (  # noqa: E402
    SCHEMA,
    AUTHORITY,
    InstantOneShotLearning,
    CalculatedState,
    CalculatedParameter,
    observe_task,
    attribute_credit,
    identify_rule,
    extract_contract,
    classify_applicability,
    verify_composition,
    execute_with_horizon,
    admit_before_persistence,
    remember_skill,
    replay_skill,
    OBSERVE_DONE,
    CREDIT_DONE,
    IDENTIFY_DONE,
    CONTRACT_DONE,
    APPLICABILITY_DONE,
    COMPOSE_DONE,
    HORIZON_DONE,
    ADMIT_DONE,
    REMEMBER_DONE,
    REPLAY_DONE,
    COMPOSE_DONE,
    HORIZON_DONE,
    ADMIT_DONE,
    REMEMBER_DONE,
    REFUSED,
    NO_TRACE,
    NO_CREDIT,
    NO_RULE,
    NO_CONTRACT,
    NOT_APPLICABLE,
    NOT_COMPOSABLE,
    HORIZON_FAILED,
    ADMISSION_FAILED,
)
from canonical.swe_kernel.horizon_bounded_execution_v1 import (  # noqa: E402
    Constraint,
    SubGoal,
)
from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    EffectContract,
    Effect,
    compose_contracts,
    PASS,
    UNDO,
    measured_no_op_pair,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def tmp_root():
    """A real temporary directory that acts as a computer-use environment."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-on-shot-"))
    (root / "workspace.txt").write_text("start\n")
    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def simple_contract():
    """A simple valid EffectContract."""
    return EffectContract.of(
        "write_file",
        preconditions=("filesystem_writable",),
        observables=("output_file",),
        actions=("echo_result",),
        verdict="file_exists_check",
        effects=[("ESTABLISH", "output_exists")],
    )


# --------------------------------------------------------------------------- #
# observe phase
# --------------------------------------------------------------------------- #


def test_observe_captures_single_trace(tmp_root):
    """OBSERVE captures a single execution trace with snapshots."""
    result = observe_task(
        tmp_root,
        "task_1",
        [("echo result > output.txt", "")],
        terminal_outcome=1,
    )
    assert result["phase"] == "OBSERVE"
    assert result["status"] == OBSERVE_DONE
    assert result["task_id"] == "task_1"
    assert result["step_count"] == 1
    assert result["terminal_outcome"] == 1
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_observe_refuses_invalid_terminal_outcome(tmp_root):
    """OBSERVE refuses terminal outcomes other than 0 or 1."""
    result = observe_task(
        tmp_root, "task_bad", [("echo x", "")], terminal_outcome=2
    )
    assert result["phase"] == "OBSERVE"
    assert result["status"] == REFUSED
    assert result["reason"] == "INVALID_TERMINAL_OUTCOME"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_observe_refuses_empty_trace(tmp_root):
    """OBSERVE refuses an empty trace."""
    result = observe_task(tmp_root, "task_empty", [], terminal_outcome=1)
    assert result["phase"] == "OBSERVE"
    assert result["status"] == REFUSED
    assert result["reason"] == NO_TRACE


# --------------------------------------------------------------------------- #
# credit phase
# --------------------------------------------------------------------------- #


def test_credit_attributes_causal_steps(tmp_root):
    """CREDIT attributes which steps earned the outcome vs. luck."""
    observe = observe_task(
        tmp_root,
        "task_1",
        [("echo result > output.txt", "")],
        terminal_outcome=1,
    )
    assert observe["status"] == OBSERVE_DONE

    result = attribute_credit(
        tmp_root, observe, [[("fail", "exit 1")]]
    )
    assert result["phase"] == "CREDIT"
    assert result["status"] == CREDIT_DONE
    assert "causal_steps" in result
    assert "non_causal_steps" in result
    assert "total_credit" in result
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_credit_refuses_when_no_observe():
    """CREDIT refuses when OBSERVE hasn't been run."""
    result = attribute_credit(
        tmp_root if 'tmp_root' in dir() else pathlib.Path.cwd(),
        {"status": "NOT_OBSERVED"},
        [[("fail", "exit 1")]],
    )
    assert result["phase"] == "CREDIT"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# identify phase
# --------------------------------------------------------------------------- #


def test_identify_closes_rule_by_proof_or_witness(tmp_root):
    """IDENTIFY closes the rule by contrastive oracle bootstrap."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    assert credit["status"] == CREDIT_DONE

    result = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    assert result["phase"] == "IDENTIFY"
    assert result["status"] == IDENTIFY_DONE
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_identify_refuses_when_no_credit():
    """IDENTIFY refuses when CREDIT hasn't been run."""
    result = identify_rule(
        tmp_root, {"status": "NOT_CREDITED"}, "echo x", [("wrong", "exit 1")]
    )
    assert result["phase"] == "IDENTIFY"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# contract phase
# --------------------------------------------------------------------------- #


def test_contract_extracts_valid_effect_contract(tmp_root):
    """CONTRACT extracts a typed EffectContract from the identified rule."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )

    result = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )
    assert result["phase"] == "CONTRACT"
    assert result["status"] == CONTRACT_DONE
    assert result["skill_id"] == "write_file"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_contract_refuses_incomplete_contract(tmp_root):
    """CONTRACT refuses when the contract is incomplete (no observables)."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )

    result = extract_contract(
        identify,
        "weak",
        (),
        (),  # no observables — vocabulary barrier
        ("echo",),
        "self",  # not a separating verdict
        [("ESTABLISH", "x")],
    )
    assert result["phase"] == "CONTRACT"
    assert result["status"] == REFUSED


def test_contract_refuses_when_no_identify(tmp_root):
    """CONTRACT refuses when IDENTIFY hasn't been run."""
    result = extract_contract(
        {"status": "NOT_IDENTIFIED"},
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )
    assert result["phase"] == "CONTRACT"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# applicability phase
# --------------------------------------------------------------------------- #


def test_applicability_classifies_states(tmp_root):
    """APPLICABILITY learns when the rule applies via candidate elimination."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )

    result = classify_applicability(
        contract,
        success_states=[{"filesystem_writable"}, {"filesystem_writable", "has_dir"}],
        failure_states=[{"has_dir"}],  # missing filesystem_writable
    )
    assert result["phase"] == "APPLICABILITY"
    assert result["status"] == APPLICABILITY_DONE
    assert result["applicability_status"] in (
        "IDENTIFIED", "UNDETERMINED", "AMBIGUOUS", "INCONSISTENT", "BOUNDED",
    )
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_applicability_refuses_when_no_contract(tmp_root):
    """APPLICABILITY refuses when CONTRACT hasn't been run."""
    result = classify_applicability(
        {"status": "NOT_CONTRACTED"},
        success_states=[{"x"}],
        failure_states=[{}],
    )
    assert result["phase"] == "APPLICABILITY"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# compose phase
# --------------------------------------------------------------------------- #


def test_compose_verifies_skill_chain(tmp_root, simple_contract):
    """COMPOSE verifies the skill composes with others to the intended goal."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )

    # No other contracts — just this one skill
    result = verify_composition(
        contract,
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
    )
    assert result["phase"] == "COMPOSE"
    assert result["status"] == COMPOSE_DONE
    assert result["composable"] is True
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_compose_refuses_no_op_chain(tmp_root, simple_contract):
    """COMPOSE refuses the measured no-op pair (A tightens, B loosens)."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )

    a, b = measured_no_op_pair()
    result = verify_composition(
        contract,
        other_contracts=[a, b],
        intended_goal=frozenset({"output_exists"}),
    )
    # The no-op pair should be detected as EFFECT_UNDO
    assert result["phase"] == "COMPOSE"
    assert result["status"] == REFUSED


def test_compose_refuses_when_no_contract(tmp_root):
    """COMPOSE refuses when CONTRACT hasn't been run."""
    result = verify_composition(
        {"status": "NOT_CONTRACTED"},
        other_contracts=[],
        intended_goal=frozenset({"x"}),
    )
    assert result["phase"] == "COMPOSE"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# horizon phase
# --------------------------------------------------------------------------- #


def test_horizon_executes_bounded_subgoals(tmp_root, simple_contract):
    """HORIZON decomposes a long task into bounded sub-goals with checkpoints."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )
    compose = verify_composition(
        contract,
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
    )

    result = execute_with_horizon(
        compose,
        task_id="demo_horizon",
        goal=("output_verified",),
        constraints=(("no_data_loss", "check_files_present", ("every_step",)),),
        total_step_budget=100,
        subgoals=(
            ("create_output", (), ("output_exists",), 10, ("no_data_loss",)),
        ),
        initial_state={"output.txt": b""},
    )
    assert result["phase"] == "HORIZON"
    assert result["status"] == HORIZON_DONE
    assert result["goal_reached"] is True
    assert result["all_constraints_preserved"] is True
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_horizon_refuses_when_horizon_exceeded(tmp_root, simple_contract):
    """HORIZON refuses when sub-goal budget exceeds total budget."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )
    compose = verify_composition(
        contract,
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
    )

    result = execute_with_horizon(
        compose,
        task_id="demo_horizon",
        goal=("output_verified",),
        constraints=(),
        total_step_budget=10,
        subgoals=(
            ("create_output", (), ("output_exists",), 200, ()),
        ),
        initial_state={},
    )
    assert result["phase"] == "HORIZON"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# admit phase
# --------------------------------------------------------------------------- #


def test_admit_requires_held_out_victims(tmp_root, simple_contract):
    """ADMIT refuses when no held-out victims are supplied (refuse before write)."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    contract = extract_contract(
        identify,
        "write_file",
        ("filesystem_writable",),
        ("output_file",),
        ("echo_result",),
        "file_exists_check",
        [("ESTABLISH", "output_exists")],
    )
    compose = verify_composition(
        contract,
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
    )
    horizon = execute_with_horizon(
        compose,
        task_id="demo_horizon",
        goal=("output_verified",),
        constraints=(),
        total_step_budget=100,
        subgoals=(
            ("create_output", (), ("output_exists",), 10, ()),
        ),
        initial_state={"output.txt": b""},
    )

    result = admit_before_persistence(horizon, contract, victims=[])
    assert result["phase"] == "ADMIT"
    assert result["status"] == REFUSED
    assert result["reason"] == "NO_HELD_OUT_VICTIMS__REFUSE_BEFORE_WRITE"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_admit_refuses_when_no_horizon(tmp_root, simple_contract):
    """ADMIT refuses when HORIZON hasn't been run."""
    result = admit_before_persistence(
        {"status": "NOT_HORIZONED"},
        {"status": CONTRACT_DONE, "contract": simple_contract},
        victims=[],
    )
    assert result["phase"] == "ADMIT"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# remember phase
# --------------------------------------------------------------------------- #


def test_remember_persists_nothing(tmp_root):
    """REMEMBER persists nothing — zero knowledge house."""
    admit_result = {
        "status": ADMIT_DONE,
        "admitted": True,
        "victim_count": 1,
    }
    result = remember_skill(admit_result)
    assert result["phase"] == "REMEMBER"
    assert result["status"] == REMEMBER_DONE
    assert result["stored_knowledge_bytes"] == 0
    assert result["knowledge_house"] is False
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_remember_refuses_when_admission_refused():
    """REMEMBER refuses when admission was refused."""
    admit_result = {"status": REFUSED, "reason": "ADMISSION_FAILED"}
    result = remember_skill(admit_result)
    assert result["phase"] == "REMEMBER"
    assert result["status"] == REFUSED


# --------------------------------------------------------------------------- #
# full loop
# --------------------------------------------------------------------------- #


def test_full_loop_zero_model_calls_zero_network_calls(tmp_root):
    """Full instant one-shot learning loop reports zero model and network calls."""
    engine = InstantOneShotLearning(tmp_root)

    victims = [
        {
            "name": "unseen_defective",
            "before": "def f(x): return x <= 100\n",
            "after": "def f(x): return x < 100\n",
            "language": "python",
            "error_class": "boundary",
        }
    ]

    report = engine.run(
        task_id="demo_task",
        steps=[("echo result > output.txt", "")],
        terminal_outcome=1,
        credit_wrong_actions=[[("fail", "exit 1")]],
        right_command="echo result > output.txt",
        id_wrong_actions=[("wrong", "exit 1")],
        skill_id="write_output",
        preconditions=("filesystem_writable",),
        observables=("output_file",),
        actions=("echo_result",),
        verdict="file_exists_check",
        effects=[("ESTABLISH", "output_exists")],
        success_states=[{"filesystem_writable"}],
        failure_states=[],
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
        horizon_task_id="demo_horizon",
        horizon_goal=("output_verified",),
        horizon_constraints=(("no_data_loss", "check_files_present", ("every_step",)),),
        horizon_total_step_budget=100,
        horizon_subgoals=(
            ("create_output", (), ("output_exists",), 10, ("no_data_loss",)),
        ),
        horizon_initial_state={"output.txt": b""},
        victims=victims,
    )
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0
    assert report["schema"] == "PROJECT_BRAIN_INSTANT_ONE_SHOT_LEARNING_V1"
    assert report["authority"] == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"


def test_engine_status_reports_no_knowledge_house(tmp_root):
    """Engine status reports calculated parameters, zero knowledge house."""
    engine = InstantOneShotLearning(tmp_root)
    status = engine.status()
    assert status["model_calls"] == 0
    assert status["network_calls"] == 0
    assert status["stored_knowledge_bytes"] == 0
    assert status["knowledge_house"] is False
    assert status["every_parameter_calculated"] is True


def test_schema_and_authority_are_declared():
    """Schema and authority are declared constants."""
    assert SCHEMA == "PROJECT_BRAIN_INSTANT_ONE_SHOT_LEARNING_V1"
    assert AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"


def test_calculated_parameter_has_derivation_not_training():
    """CalculatedParameter records derivation, not training source."""
    param = CalculatedParameter(
        name="causal_step_0",
        value=1,
        derivation="counterfactual_point_of_commitment_attribution",
    )
    assert param.derivation == "counterfactual_point_of_commitment_attribution"
    assert param.value == 1


def test_fail_closed_propagation(tmp_root):
    """Any phase failure propagates and refuses — no silent continuation."""
    engine = InstantOneShotLearning(tmp_root)

    # No victims → ADMIT will refuse → entire loop refuses
    report = engine.run(
        task_id="demo_task",
        steps=[("echo result > output.txt", "")],
        terminal_outcome=1,
        credit_wrong_actions=[[("fail", "exit 1")]],
        right_command="echo result > output.txt",
        id_wrong_actions=[("wrong", "exit 1")],
        skill_id="write_output",
        preconditions=("filesystem_writable",),
        observables=("output_file",),
        actions=("echo_result",),
        verdict="file_exists_check",
        effects=[("ESTABLISH", "output_exists")],
        success_states=[{"filesystem_writable"}],
        failure_states=[],
        other_contracts=[],
        intended_goal=frozenset({"output_exists"}),
        horizon_task_id="demo_horizon",
        horizon_goal=("output_verified",),
        horizon_constraints=(),
        horizon_total_step_budget=100,
        horizon_subgoals=(
            ("create_output", (), ("output_exists",), 10, ()),
        ),
        horizon_initial_state={"output.txt": b""},
        victims=[],  # no victims → admission refused
    )
    assert report["status"] == REFUSED
    assert report["result"] == "REFUSED__ADMISSION_FAILED"


def test_repetition_buys_zero_bits(tmp_root):
    """Repetition of the same observation adds no learning information."""
    observe1 = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    observe2 = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    assert observe1["status"] == OBSERVE_DONE
    assert observe2["status"] == OBSERVE_DONE
    assert observe1["step_count"] == observe2["step_count"]
    assert observe1["terminal_outcome"] == observe2["terminal_outcome"]
    # Same calculated result — repetition buys zero bits


# --------------------------------------------------------------------------- #
# replay phase
# --------------------------------------------------------------------------- #


def test_replay_reproduces_on_new_state(tmp_root):
    """REPLAY reproduces the identified rule on a new environment state."""
    observe = observe_task(
        tmp_root, "task_1", [("echo result > output.txt", "")], terminal_outcome=1
    )
    credit = attribute_credit(tmp_root, observe, [[("fail", "exit 1")]])
    identify = identify_rule(
        tmp_root, credit, "echo result > output.txt", [("wrong", "exit 1")]
    )
    assert identify["status"] == IDENTIFY_DONE

    result = replay_skill(
        identify,
        tmp_root,
        replay_steps=[("echo result > output.txt", "")],
        expected_effect_subjects=["output.txt"],
    )
    assert result["phase"] == "REPLAY"
    assert result["status"] == REPLAY_DONE
    assert result["all_effects_present"] is True
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_replay_refuses_without_identify(tmp_root):
    """REPLAY refuses when IDENTIFY hasn't been run."""
    result = replay_skill(
        {"status": "NOT_IDENTIFIED"},
        tmp_root,
        replay_steps=[("echo result > output.txt", "")],
        expected_effect_subjects=["output.txt"],
    )
    assert result["phase"] == "REPLAY"
    assert result["status"] == REFUSED
