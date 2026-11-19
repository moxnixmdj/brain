"""Tests for the round that falsifies the path-restriction prediction."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/the_path_narrows_the_search_but_not_the_shape_v1.py"
RECEIPT = ROOT / "canonical/verification/THE_PATH_NARROWS_THE_SEARCH_BUT_NOT_THE_SHAPE_20261119_V1.json"

GATES = ["K1_the_executed_path_is_measured_on_real_refusals",
         "K2_the_prediction_about_token_search_is_tested",
         "K3_structural_generation_from_the_files_own_text_is_measured",
         "K4_the_union_and_its_cost", "K5_containment_is_confirmed_by_execution", "K6_zero"]


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("path_round", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_gates(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_THE_PATH_NARROWS_THE_SEARCH_BUT_NOT_THE_SHAPE_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    for gate in GATES:
        assert receipt["verdict"][gate]["MET"] is True


def test_a_statement_copied_from_the_file_is_contained(tool) -> None:
    before = "def f(x):\n    y = 1\n    return x\n\ndef g(z):\n    return z\n"
    after = "def f(x):\n    y = 1\n    return x\n\ndef g(z):\n    y = 1\n    return z\n"
    hit = tool.exact_statement_hit(before, after, [("g", 5, 6)])
    assert hit["contained"] is True and hit["lines_added"] == 1


def test_a_statement_the_file_does_not_contain_is_not_contained(tool) -> None:
    before = "def f(x):\n    return x\n"
    after = "def f(x):\n    qq = 99\n    return x\n"
    hit = tool.exact_statement_hit(before, after, [("f", 1, 3)])
    assert hit["contained"] is False
    assert hit["reused_from_the_file"] == 0


def test_the_same_text_outside_the_executed_path_is_not_contained(tool) -> None:
    before = "def f(x):\n    y = 1\n    return x\n\ndef g(z):\n    return z\n"
    after = "def f(x):\n    y = 1\n    return x\n\ndef g(z):\n    y = 1\n    return z\n"
    hit = tool.exact_statement_hit(before, after, [("f", 1, 3)])
    assert hit["contained"] is False
    assert hit["inserted_inside_an_executed_function"] == 0


def test_an_inline_element_at_a_slot_is_contained(tool) -> None:
    before = "def f():\n    return [1, 2]\n"
    after = "def f():\n    return [1, 2, 3]\n"
    hit = tool.exact_structure_hit(before, after, [("f", 1, 2)])
    assert hit["contained"] is True


def test_the_counts_are_internally_consistent(receipt: dict) -> None:
    rows, v = receipt["per_task"], receipt["verdict"]
    failed = [r for r in rows if r.get("ran") and r.get("failed")]
    assert v["K1_the_executed_path_is_measured_on_real_refusals"]["failed"] == len(failed)
    for key, field in (("s1_contained", "s1_contained"), ("s2_contained", "s2_contained"),
                       ("s3_contained", "s3_contained")):
        assert sum(1 for r in failed if r.get(field)) == sum(
            1 for r in failed if r.get(field))
    k2 = v["K2_the_prediction_about_token_search_is_tested"]
    assert k2["s1_contained"] == sum(1 for r in failed if r.get("s1_contained"))
    k3 = v["K3_structural_generation_from_the_files_own_text_is_measured"]
    assert k3["inline_element_added_to_a_literal_or_call"] == sum(
        1 for r in failed if r.get("s2_contained"))
    assert k3["statement_inserted_whose_text_the_file_already_contains"] == sum(
        1 for r in failed if r.get("s3_contained"))


def test_the_prediction_is_recorded_as_falsified(receipt: dict) -> None:
    k2 = receipt["verdict"]["K2_the_prediction_about_token_search_is_tested"]
    assert "high tens of percent" in k2["predicted"]
    assert k2["fraction"] is not None and k2["fraction"] < 0.2
    assert k2["of_those_the_path_excludes"] == 8 - k2["of_those_inside_the_executed_path"]


def test_containment_is_confirmed_by_execution(receipt: dict) -> None:
    k5 = receipt["verdict"]["K5_containment_is_confirmed_by_execution"]
    assert k5["candidates_executed"] >= 1
    assert k5["confirmed_by_the_real_suite"] == k5["candidates_executed"]


def test_zero_model_and_parameters(receipt: dict) -> None:
    assert receipt["cost"]["model_calls"] == 0 and receipt["cost"]["parameters_stored"] == 0
    for forbidden in ("import requests", "from openai", "import anthropic"):
        assert forbidden not in TOOL.read_text()
