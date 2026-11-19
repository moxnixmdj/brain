"""Tests for the round that measures the one shape the census calls memorisable."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/a_new_literal_in_an_existing_construct_v1.py"
RECEIPT = ROOT / "canonical/verification/A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_20261119_V1.json"

GATES = ["K1_the_insertion_shape_is_decided_exactly",
         "K2_a_new_literal_in_an_existing_construct_is_counted",
         "K3_the_check_names_the_literal_that_fills_the_hole",
         "K4_the_class_is_confirmed_by_execution", "K5_zero"]


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("value_added", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_gates(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    for gate in GATES:
        assert receipt["verdict"][gate]["MET"] is True


def test_an_inserted_line_is_read(tool) -> None:
    before = "X = [\n    1,\n]\n"
    after = "X = [\n    1,\n    2,\n]\n"
    ins = tool.insertion(before, after)
    assert ins and ins["kind"] == "insert" and ins["text"].strip() == "2,"


def test_an_appended_element_is_the_same_act(tool) -> None:
    before = "X = [\n    1]\n"
    after = "X = [\n    1, 2]\n"
    ins = tool.insertion(before, after)
    assert ins and ins["kind"] == "append" and ins["text"].strip() == ", 2"


def test_the_enclosing_construct_must_span_lines(tool) -> None:
    multi = "X = [\n    1,\n    2,\n]\n"
    single = "X = [1, 2]\n"
    assert tool.enclosing_construct(multi, 2) == "List"
    assert tool.enclosing_construct(single, 1) is None


def test_a_dict_entry_yields_its_literal(tool) -> None:
    node = tool.element_node('"URL": re.compile(r"\\S+"),')
    assert "\\S+" in tool.literals(node)


def test_the_receipt_counts_are_consistent(receipt: dict) -> None:
    rows, v = receipt["per_task"], receipt["verdict"]
    added = [r for r in rows if r.get("value_added")]
    named = [r for r in added if r.get("literal_in_the_check")]
    assert v["K2_a_new_literal_in_an_existing_construct_is_counted"]["value_added"] == len(added)
    assert v["K3_the_check_names_the_literal_that_fills_the_hole"][
        "literal_already_in_the_check"] == len(named)
    assert v["K1_the_insertion_shape_is_decided_exactly"]["tasks"] == len(rows)


def test_the_empty_class_is_recorded_as_empty_not_as_success(receipt: dict) -> None:
    k2 = receipt["verdict"]["K2_a_new_literal_in_an_existing_construct_is_counted"]
    assert k2["fraction_of_corpus"] is not None
    assert k2["fraction_of_corpus"] < 0.05


def test_zero_model_and_parameters(receipt: dict) -> None:
    assert receipt["cost"]["model_calls"] == 0 and receipt["cost"]["parameters_stored"] == 0
    for forbidden in ("import requests", "from openai", "import anthropic"):
        assert forbidden not in TOOL.read_text()
