"""Tests for the-computed-vocabulary round.

The tests do not trust the receipt. They build the two namings themselves on the real machines and pin the
three things the round rests on: that a hand name stands for two different transitions, that one of those
cells is a move named INERT, and that the derived name is a function of the transition, computed.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402
import the_vocabulary_must_be_computed_not_written_v1 as vc  # noqa: E402

RECEIPT = (pathlib.Path(__file__).resolve().parents[1] / "verification"
           / "THE_VOCABULARY_MUST_BE_COMPUTED_20261119_V1.json")
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    return vc.measure_machine("FILESYSTEM", tmp_path_factory.mktemp("vocab"))


def cell(measured, atom: str, state_class: str) -> dict:
    return next(row for row in measured["cells"]
                if row["atom"] == atom and row["state_class"] == state_class)


# ------------------------------------------------------------------------------------------------------
# the two namings, on the same measured transition
# ------------------------------------------------------------------------------------------------------

def test_the_derived_name_is_a_function_of_the_transition(measured):
    seen = {}
    for row in measured["cells"]:
        seen.setdefault(row["derived"], set()).add(tuple(row["signature"]))
    assert all(len(sigs) == 1 for sigs in seen.values()), "a derived name must not merge two transitions"


def test_the_hand_name_merges_two_transitions(measured):
    grouped = vc.collisions(measured["cells"])
    assert grouped["merged_names"], grouped
    persist = grouped["merged"].get("PERSIST")
    assert persist and persist["distinct_transitions"] == 2


def test_writing_and_copying_are_the_same_hand_name_and_different_signatures(measured):
    write = cell(measured, "FS_A1", "TARGET_ABSENT")
    copy = cell(measured, "FS_A4", "TARGET_EXISTS")
    assert write["hand_effect"] == copy["hand_effect"] == env.PERSIST
    assert write["arrived"] == ["ARG"] and copy["arrived"] == ["OLD"]
    assert write["derived"] != copy["derived"]


def test_a_move_is_named_inert_and_the_signature_says_the_world_moved(measured):
    moves = [row for row in measured["cells"]
             if row["hand_effect"] == env.INERT and (row["appeared"] or row["vanished"])]
    assert len(moves) == 1
    assert moves[0]["derived"] == "ARRIVE[-];DEPART[-];CARD+0;IDS+1-1"


def test_the_hand_vocabulary_is_not_a_consistent_abstraction(measured):
    """The identity coordinate is recorded in some hand cells and dropped in others -- for the same atom."""
    per_atom = vc._effects_per_atom(measured["cells"])
    assert any(len(names) > 1 for names in per_atom.values())
    express = vc.hand_model_can_express_identity(measured["cells"])
    assert express["operators_that_change_identity"] > 0


# ------------------------------------------------------------------------------------------------------
# the goal, and the one step that achieves it
# ------------------------------------------------------------------------------------------------------

def test_the_moved_goal_is_achieved_by_a_single_real_command(tmp_path):
    moved = vc.moved_step("FILESYSTEM", tmp_path)
    chosen = moved["atom_that_achieves_the_moved_goal"]
    assert chosen is not None
    assert chosen["hand_effect"] == env.INERT
    assert chosen["derived"].endswith("IDS+1-1")


def test_a_machine_without_a_move_atom_reports_none_rather_than_a_guess(tmp_path):
    assert vc.moved_step("SORT", tmp_path)["atom_that_achieves_the_moved_goal"] is None


def test_the_judge_really_does_reject_a_copy_and_accept_a_move(tmp_path):
    machine = vocab.MACHINES["FILESYSTEM"](tmp_path / "judge")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    before = tuple(machine.read())
    env.execute(machine.atoms[3], machine, ARGS)          # FS_A4: cp
    after_copy = tuple(machine.read())
    assert quotient.moved_judge([before, after_copy]) is False
    machine.reset()
    before = tuple(machine.read())
    env.execute(machine.atoms[2], machine, ARGS)          # FS_A3: mv
    after_move = tuple(machine.read())
    assert quotient.moved_judge([before, after_move]) is True


# ------------------------------------------------------------------------------------------------------
# the measurement and the committed receipt
# ------------------------------------------------------------------------------------------------------

def test_the_measurement_meets_every_claim(tmp_path):
    receipt = vc.measure(tmp_path / "receipt.json")
    assert [key for key, value in receipt["verdict"].items() if not value["MET"]] == []
    assert receipt["verdict"]["K1_the_hand_vocabulary_merges_transitions"]["cells"] == 44
    assert receipt["verdict"]["K5_the_refinement_is_free"]["extra_trials_for_the_derived_vocabulary"] == 0


def test_the_committed_receipt_meets_every_claim():
    receipt = json.loads(RECEIPT.read_text())
    verdict = receipt["verdict"]
    assert [key for key, value in verdict.items() if not value["MET"]] == []
    k1 = verdict["K1_the_hand_vocabulary_merges_transitions"]
    assert k1["cells"] == 44
    assert k1["witnesses"]["creation versus duplication"] and k1["witnesses"]["creation versus duplication (copy)"]
    assert k1["witnesses"]["a command that did nothing"] and k1["witnesses"]["a command that moved the world"]
    assert verdict["K3_the_hand_model_refuses_what_one_command_achieves"][
        "the_hand_name_of_that_atom"]["FILESYSTEM"] == env.INERT
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["limits"]


def test_the_producer_has_no_model_no_parameters_no_network():
    source = pathlib.Path(vc.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import urllib", "import socket", "import torch",
                      "import openai", "from openai", "http://", "https://"):
        assert forbidden not in source, forbidden
