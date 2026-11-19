"""Tests for the round that asks whether the rejected value's producer localises the fix."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/the_value_that_was_rejected_had_a_producer_v1.py"
RECEIPT = ROOT / "canonical/verification/THE_VALUE_THAT_WAS_REJECTED_HAD_A_PRODUCER_20261119_V1.json"

GATES = [
    "K1_the_refused_state_is_executed_under_a_tracer",
    "K2_a_producer_of_the_rejected_value_is_found",
    "K3_the_producer_localises_the_fix",
    "K4_the_gain_is_the_failures_the_traceback_cannot_localise",
    "K5_zero",
]


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("producer_round", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_THE_VALUE_THAT_WAS_REJECTED_HAD_A_PRODUCER_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_declared_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_the_rejected_operand_is_read_from_the_checker(tool) -> None:
    assert tool.rejected_value("E       assert 2 == 3\n") == "2"
    assert tool.rejected_value("E       assert 'a' != 'b'\n") == "'a'"
    assert tool.rejected_value("E       assert f(x) == 3\n") == "f(x)"


def test_a_bare_assertion_rejects_no_value_and_says_so(tool) -> None:
    assert tool.rejected_value("E       assert False\n") is None
    assert tool.rejected_value("E       assert True\n") is None
    assert tool.rejected_value("E       TypeError: nope\n") is None


def test_the_fix_functions_come_from_the_fixed_state(tool) -> None:
    after = "def a():\n    x = 1\n    return x\n\ndef b():\n    return 2\n"
    assert tool.fix_functions(after, [5]) == {"b"}
    assert tool.fix_functions(after, [2, 5]) == {"a", "b"}
    assert tool.fix_functions("def broken(:\n", [1]) == set()


def test_the_receipt_counts_are_internally_consistent(receipt: dict) -> None:
    rows = receipt["per_task"]
    v = receipt["verdict"]
    failed = [r for r in rows if r.get("ran") and r.get("failed")]
    k1 = v["K1_the_refused_state_is_executed_under_a_tracer"]
    k2 = v["K2_a_producer_of_the_rejected_value_is_found"]
    k3 = v["K3_the_producer_localises_the_fix"]
    k4 = v["K4_the_gain_is_the_failures_the_traceback_cannot_localise"]
    assert k1["tasks"] == len(rows)
    assert k1["failed"] == len(failed)
    assert k2["producer_found"] == sum(1 for r in failed if r.get("produced"))
    assert k3["producer_is_a_function_the_fix_changed"] == sum(
        1 for r in failed if r.get("producer_is_a_function_the_fix_changed"))
    no_frame = [r for r in failed if not r.get("traceback_points_into_the_source")]
    assert k4["failures_without_a_source_frame"] == len(no_frame)
    assert k4["of_those_where_a_function_the_fix_changed_was_on_the_path"] == sum(
        1 for r in no_frame if r.get("fix_function_on_the_path"))


def test_nothing_unrunnable_is_scored(receipt: dict) -> None:
    for row in receipt["per_task"]:
        if not row.get("ran"):
            assert row.get("reason")


def test_the_honest_reading_is_recorded_not_flattered(receipt: dict) -> None:
    """Provenance is a weak precise localiser and a strong reachability one; both are counted."""
    k4 = receipt["verdict"]["K4_the_gain_is_the_failures_the_traceback_cannot_localise"]
    assert k4["fraction"] is not None and k4["fraction"] < 0.2
    assert k4["fraction_on_the_path"] is not None and k4["fraction_on_the_path"] > 0.5


def test_zero_model_and_parameters(receipt: dict) -> None:
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    source = TOOL.read_text()
    for forbidden in ("import requests", "from openai", "import anthropic"):
        assert forbidden not in source
