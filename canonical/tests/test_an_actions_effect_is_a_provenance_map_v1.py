"""Tests for the round that stops designing the effect vocabulary.

`compose_measured_effects_v1` can only use effects its three-effect vocabulary can
name, so `cp` was unusable. This round derives the vocabulary from provenance and
one execution, then predicts whole trees it never ran.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/an_actions_effect_is_a_provenance_map_v1.py"
RECEIPT = ROOT / "canonical/verification/AN_ACTIONS_EFFECT_IS_A_PROVENANCE_MAP_20261119_V1.json"

GATES = [
    "K1_one_execution_yields_a_localised_delta_inside_a_derivable_support",
    "K2_provenance_explains_every_change",
    "K3_one_execution_predicts_unexecuted_states_whole_tree",
    "K4_the_effect_vocabulary_now_names_what_it_could_not",
    "K5_two_actions_compose_when_the_second_precondition_is_the_firsts_effect",
    "K6_zero",
]


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_AN_ACTIONS_EFFECT_IS_A_PROVENANCE_MAP_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_acceptance_was_declared_before_the_run(receipt: dict) -> None:
    assert set(receipt["declared_acceptance_before_the_receipt_run"]) == {"K1", "K2", "K3", "K4", "K5", "K6"}


def test_timestamps_are_excluded_from_the_state(receipt: dict) -> None:
    assert receipt["state_definition"]["excluded"] == ["mtime", "atime", "owner"]


def test_one_execution_predicts_every_unexecuted_state_whole_tree(receipt: dict) -> None:
    k3 = receipt["verdict"][GATES[2]]
    assert k3["held_out_states"] == 24
    assert k3["content_and_kind_exact"] == 24
    assert k3["whole_tree_exact_including_mode"] == 24
    assert all(r["variant"] in (1, 2, 3) for rows in k3["per_action"].values() for r in rows)


def test_the_shape_varying_variant_is_included(receipt: dict) -> None:
    """Variant 3 changes the argument shape: an extra member one level deeper and an
    input in a nested directory. It must be predicted, not re-learned."""
    for name in ("tar_x", "gzip_d"):
        rows = receipt["per_action"][name]["held_out"]
        assert any(r["variant"] == 3 and r["whole_tree_exact_including_mode"] for r in rows)


def test_every_change_cites_the_actions_own_argument(receipt: dict) -> None:
    k2 = receipt["verdict"][GATES[1]]
    assert all(not paths for paths in k2["unexplained"].values())
    for rules in k2["rules"].values():
        for rule in rules:
            value = rule["value"]
            if value.get("relation") in ("identity", "gunzip", "sort_lines"):
                assert isinstance(value.get("source_arg"), int) or value.get("relation") == "empty"
            if value.get("relation") == "tar_member":
                assert isinstance(value.get("container_arg"), int)


def test_the_old_vocabulary_failure_is_proved_by_counterexample(receipt: dict) -> None:
    k4 = receipt["verdict"][GATES[3]]
    assert k4["counterexample"]["indistinguishable_to_a_presence_only_vocabulary"] is True
    assert k4["counterexample"]["the_goal_differs_between_them"] is True
    assert k4["presence_only_vocabulary_expressible"] is False
    assert k4["provenance_names_it"] is True


def test_composition_needs_both_layers(receipt: dict) -> None:
    k5 = receipt["verdict"][GATES[4]]
    assert k5["second_step_alone_rc"] != 0          # the precondition is genuinely absent
    assert (k5["first_step_rc"], k5["second_step_rc"]) == (0, 0)
    assert k5["composed_goal_reached"] is True
    assert k5["reachable_under_presence_only"] is False


def test_zero_house_of_knowledge(receipt: dict) -> None:
    assert receipt["verdict"][GATES[5]]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_a_fresh_run_reproduces_the_committed_receipt(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "receipt.json"
    completed = subprocess.run([sys.executable, str(TOOL), "--receipt", str(out)],
                               capture_output=True, text=True, timeout=900, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    fresh = json.loads(out.read_text())
    committed = json.loads(RECEIPT.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert {n: v["held_out"] for n, v in fresh["per_action"].items()} == \
           {n: v["held_out"] for n, v in committed["per_action"].items()}
