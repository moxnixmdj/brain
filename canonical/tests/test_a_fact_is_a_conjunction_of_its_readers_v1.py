"""Tests for the round that asks whether two readers may arbitrate a fact.

The round's own claim is deliberately refutable: if consensus were the right
arbiter, the audited column would beat the primary one. It does not, and these
tests pin the measurement rather than the intention.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/a_fact_is_a_conjunction_of_its_readers_v1.py"
RECEIPT = ROOT / "canonical/verification/A_FACT_IS_A_CONJUNCTION_OF_ITS_READERS_20261119_V1.json"

GATES = [
    "K1_a_second_independent_reader_surfaces_a_divergence",
    "K2_the_divergence_does_not_convict_the_column_the_action_does",
    "K3_reading_costs_nothing",
    "K4_the_collapse_has_one_direction_and_a_measured_cost",
    "K5_every_abstention_left_by_the_previous_round_is_coverage_not_an_unsound_column",
    "K6_zero",
]


@pytest.fixture(scope="module")
def receipt() -> dict:
    assert RECEIPT.exists(), "the receipt must be committed beside the tool"
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_A_FACT_IS_A_CONJUNCTION_OF_ITS_READERS_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_acceptance_was_declared_before_the_run(receipt: dict) -> None:
    declared = receipt["declared_acceptance_before_the_receipt_run"]
    assert set(declared) == {"K1", "K2", "K3", "K4", "K5", "K6"}


def test_the_divergence_is_one_fact_at_one_state(receipt: dict) -> None:
    k1 = receipt["verdict"][GATES[0]]
    assert k1["facts_with_a_disagreement"] == {"btgz_valid": [36]}
    witness = k1["witness"]
    assert witness["primary_reader_says"] is True
    assert witness["second_reader_says"] is False


def test_a_third_reading_confirms_the_file_is_not_an_archive(receipt: dict) -> None:
    third = receipt["verdict"][GATES[0]]["witness"]["third_reading"]
    assert third["gzip_members_inflate"] is True
    assert third["tar_tzf_exit"] == 0
    assert third["python_tarfile_says"] is False
    assert "not a tar" in third["payload_head"]


def test_the_action_not_the_readers_settles_it(receipt: dict) -> None:
    """The load-bearing measurement: the action is as permissive as the check.

    GNU tar treats a gzip whose payload is garbage as an empty archive and exits
    zero, so `tar -tzf` is a faithful predictor of `tar -xzf` even though the
    file is not a tar archive. A consensus audit therefore removes a column that
    the action actually needed.
    """
    k2 = receipt["verdict"][GATES[1]]
    assert k2["witness"]["the_action_tar_x_succeeded_there"] is True
    assert k2["the_action_is_as_permissive_as_the_check"] is True
    assert k2["columns_conforming_to_their_action"]["tar_x"] is True
    assert k2["columns_conforming_after_the_consensus_audit"]["tar_x"] is False


def test_consensus_costs_and_only_costs(receipt: dict) -> None:
    k2 = receipt["verdict"][GATES[1]]
    assert k2["held_out_accuracy_primary"]["tar_x"] == pytest.approx(0.923, abs=5e-4)
    assert k2["held_out_accuracy_consensus"]["tar_x"] == pytest.approx(0.846, abs=5e-4)
    assert k2["consensus_is_worse_on"] == ["tar_x"]
    for name, accuracy in k2["held_out_accuracy_primary"].items():
        assert k2["held_out_accuracy_consensus"][name] <= accuracy + 1e-9


def test_no_column_needed_replacing(receipt: dict) -> None:
    k5 = receipt["verdict"][GATES[4]]
    assert k5["columns_that_do_not_conform"] == []
    assert all(receipt["verdict"][GATES[1]]["columns_conforming_to_their_action"].values())


def test_the_collapse_only_turns_facts_false(receipt: dict) -> None:
    k4 = receipt["verdict"][GATES[3]]
    assert k4["facts_turned_true_by_the_conjunction"] == []
    assert k4["facts_turned_false_by_the_conjunction"] == ["btgz_valid"]
    assert k4["states_where_audited_differs_from_primary"] == [36]
    assert k4["cost_of_the_conservative_direction"]["tar_x"] == pytest.approx(-0.077, abs=5e-4)


def test_reading_costs_nothing(receipt: dict) -> None:
    k3 = receipt["verdict"][GATES[2]]
    assert k3["states"] == 37
    assert k3["states_unchanged_after_all_readings"] == 37
    assert k3["world_trials_added_by_the_second_reader"] == 0
    assert k3["readers"] == 34


def test_zero_house_of_knowledge(receipt: dict) -> None:
    assert receipt["verdict"][GATES[5]]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_a_fresh_run_reproduces_the_committed_receipt(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "receipt.json"
    completed = subprocess.run(
        [sys.executable, str(TOOL), "--receipt", str(out)],
        capture_output=True, text=True, timeout=600, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    fresh = json.loads(out.read_text())
    committed = json.loads(RECEIPT.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["per_action"] == committed["per_action"]
    assert fresh["pool"] == committed["pool"]
