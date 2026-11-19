"""Tests for the round that stops taking the fact vocabulary as an input.

The round's claim is narrow and checkable: a real program's own refusals select
which generic properties are conditions of an action, and the resulting rule
predicts joint states that were never executed. Its fourth gate is honestly NOT
MET and pinned here so it cannot quietly pass later.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/an_actions_vocabulary_is_its_refusal_surface_v1.py"
RECEIPT = ROOT / "canonical/verification/AN_ACTIONS_VOCABULARY_IS_ITS_REFUSAL_SURFACE_20261119_V1.json"

MET_GATES = [
    "K1_the_refusal_surface_is_finite_and_one_execution_per_property_enumerates_it",
    "K2_the_words_fix_the_grain_of_the_conditions",
    "K3_the_surface_learned_precondition_predicts_unexecuted_joint_mutations",
    "K5_one_experience_is_not_enough_and_one_execution_per_property_is",
    "K6_zero",
]
NOT_MET_GATES = ["K4_the_words_are_load_bearing_item_granularity_breaks"]


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_AN_ACTIONS_VOCABULARY_IS_ITS_REFUSAL_SURFACE_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", MET_GATES + NOT_MET_GATES)
def test_every_gate_has_a_verdict(receipt: dict, gate: str) -> None:
    assert gate in receipt["verdict"]


@pytest.mark.parametrize("gate", MET_GATES)
def test_declared_gates_are_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


@pytest.mark.parametrize("gate", NOT_MET_GATES)
def test_the_negative_result_is_pinned_and_must_not_flip_silently(receipt: dict, gate: str) -> None:
    row = receipt["verdict"][gate]
    assert row["MET"] is False
    assert "why_the_declaration_failed" in row


def test_acceptance_was_declared_before_the_run(receipt: dict) -> None:
    assert set(receipt["declared_acceptance_before_the_receipt_run"]) == {"K1", "K2", "K3", "K4", "K5", "K6"}


def test_the_world_is_real_binaries_not_synthetic_states(receipt: dict) -> None:
    assert receipt["verdict"]["K1_the_refusal_surface_is_finite_and_one_execution_per_property_enumerates_it"][
        "actions"] == 8
    assert receipt["verdict"]["K1_the_refusal_surface_is_finite_and_one_execution_per_property_enumerates_it"][
        "all_base_states_applicable"] is True


def test_one_execution_per_property_and_not_per_state(receipt: dict) -> None:
    k5 = receipt["verdict"]["K5_one_experience_is_not_enough_and_one_execution_per_property_is"]
    assert k5["cost"]["executions"] == 98
    assert k5["cost"]["joint_states_never_executed"] > 500_000
    assert k5["cost"]["ratio"] > 5000


def test_one_experience_is_wrong_not_merely_undecided(receipt: dict) -> None:
    k5 = receipt["verdict"]["K5_one_experience_is_not_enough_and_one_execution_per_property_is"]
    assert k5["once"]["wrong"] == 123
    assert k5["once"]["undecided"] == 0
    assert k5["class"] == {"exact": 160, "undecided": 0, "wrong": 0}
    assert k5["held_out_total"] == 160


def test_the_learned_precondition_is_exact_on_unexecuted_joint_states(receipt: dict) -> None:
    k3 = receipt["verdict"]["K3_the_surface_learned_precondition_predicts_unexecuted_joint_mutations"]
    assert k3["false_accepts"] == 0
    assert k3["wrong"] == 0
    assert all(v["held_out_states"] == 20 for v in receipt["per_action"].values())


def test_tar_does_not_require_the_payload_to_be_an_archive(receipt: dict) -> None:
    """Continuity with the previous round, now structural rather than argued.

    `tar -xzf` exits zero on a gzip whose payload is not an archive, so that
    condition is absent from tar's refusal surface and therefore absent from the
    learned precondition. The earlier round's "unsound column" was never unsound.
    """
    required = [u["name"] for u in receipt["per_action"]["tar_x"]["class_explanation"]["units"]]
    assert any("not in gzip format" in name for name in required)
    assert not any("does not look like a tar archive" in name for name in required)
    assert "wrapped_garbage" in receipt["per_action"]["tar_x"]["mutations_that_did_not_refuse"]


def test_an_action_with_a_nearly_empty_surface_is_named(receipt: dict) -> None:
    rm = receipt["per_action"]["rm_f"]
    assert rm["refusals"] == 1
    assert len(rm["class_explanation"]["units"]) == 1


def test_zero_house_of_knowledge(receipt: dict) -> None:
    assert receipt["verdict"]["K6_zero"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_a_fresh_run_reproduces_the_committed_receipt(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "receipt.json"
    completed = subprocess.run([sys.executable, str(TOOL), "--receipt", str(out)],
                               capture_output=True, text=True, timeout=900, check=False)
    assert completed.returncode in (0, 1), completed.stderr[-3000:]
    fresh = json.loads(out.read_text())
    committed = json.loads(RECEIPT.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert {n: v["class_behaviour"] for n, v in fresh["per_action"].items()} == \
           {n: v["class_behaviour"] for n, v in committed["per_action"].items()}
