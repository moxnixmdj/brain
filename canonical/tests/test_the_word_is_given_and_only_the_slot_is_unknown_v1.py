"""Tests for the round that measures the two preconditions of parameter-free repair."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/the_word_is_given_and_only_the_slot_is_unknown_v1.py"
RECEIPT = ROOT / "canonical/verification/THE_WORD_IS_GIVEN_AND_ONLY_THE_SLOT_IS_UNKNOWN_20261119_V1.json"

GATES = [
    "K1_the_machine_points_into_the_source_only_sometimes",
    "K2_the_word_is_supplied_by_the_check_or_the_refusal",
    "K3_the_slot_is_local_to_the_function_that_refused",
    "K4_the_ceiling_of_parameter_free_repair_is_counted_not_claimed",
    "K5_zero",
]

TRACEBACK = """\
tests/test_ranges.py:2987: in test_copy
    range.copy()
/usr/lib/python3.11/copy.py:102: in copy
    return cls.__new__(cls)
src/packaging/ranges.py:1133: TypeError
"""


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("slot_round", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_THE_WORD_IS_GIVEN_AND_ONLY_THE_SLOT_IS_UNKNOWN_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_declared_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_the_site_is_the_innermost_source_frame(tool) -> None:
    assert tool.site_line(TRACEBACK, "src/packaging/ranges.py") == 1133
    # an assertion failure leaves no source frame at all: that is the finding, not a bug
    assertion = ("tests/test_f.py:12: in test_f\n    assert f(1) == 3\n"
                 "E       assert 2 == 3\n")
    assert tool.site_line(assertion, "src/pkg/mod.py") is None


def test_the_refusing_function_is_the_innermost_enclosing_one(tool) -> None:
    source = "def a():\n    def b():\n        pass\n    return b\n\ndef c():\n    pass\n"
    assert tool.enclosing_function(source, 3) == ("b", 2, 3)
    assert tool.enclosing_function(source, 7) == ("c", 6, 7)
    assert tool.enclosing_function("def a():\n    pass\n", 99) is None


def test_a_change_is_attributed_to_the_function_it_lands_in(tool) -> None:
    before = "def a():\n    x = 1\n    return x\n\ndef b():\n    return 2\n"
    after = "def a():\n    x = 1\n    return x\n\ndef b():\n    return 3\n"
    lines = tool.changed_lines(before, after)
    assert tool.lands_in_function(after, "b", lines) is True
    assert tool.lands_in_function(after, "a", lines) is False


def test_supply_reads_the_check_not_the_fix(tool) -> None:
    names, strings = tool.vocabulary("import bisect\nassert tag == 'wheel-1.0'\n")
    assert "bisect" in names and "import" in names
    assert "wheel-1.0" in strings
    assert tool.supplied("bisect", is_name=True, names=names, strings=strings, text="") is True
    assert tool.supplied("copyreg", is_name=True, names=names, strings=strings, text="") is False
    assert tool.supplied("wheel-1.0", is_name=False, names=set(), strings=strings,
                         text="") is True


def test_the_receipt_counts_are_internally_consistent(receipt: dict) -> None:
    k1 = receipt["verdict"]["K1_the_machine_points_into_the_source_only_sometimes"]
    k2 = receipt["verdict"]["K2_the_word_is_supplied_by_the_check_or_the_refusal"]
    k3 = receipt["verdict"]["K3_the_slot_is_local_to_the_function_that_refused"]
    k4 = receipt["verdict"]["K4_the_ceiling_of_parameter_free_repair_is_counted_not_claimed"]
    rows = receipt["per_task"]
    failed = [r for r in rows if r.get("ran") and r.get("failed")]
    assert k1["tasks"] == len(rows)
    assert k1["failed"] == len(failed)
    assert k1["failures_with_a_source_frame"] == sum(1 for r in failed if r.get("site"))
    assert k2["fixes_with_a_new_word"] == sum(1 for r in failed if r.get("words"))
    assert k2["all_new_words_supplied"] == sum(
        1 for r in failed if r.get("words") and r.get("all_words_supplied"))
    assert k3["change_lands_in_the_refusing_function"] == sum(
        1 for r in failed if r.get("change_lands_in_that_function"))
    assert k4["word_supplied_and_slot_local"] == sum(
        1 for r in failed if r.get("all_words_supplied") and r.get("change_lands_in_that_function"))


def test_nothing_unrunnable_is_scored(receipt: dict) -> None:
    for row in receipt["per_task"]:
        if not row.get("ran"):
            assert row.get("reason")
            assert not row.get("site") and not row.get("words")


def test_the_ceiling_is_small_and_is_not_sold_as_success(receipt: dict) -> None:
    """The honest reading of this round: the mechanism's ceiling is a few percent."""
    k4 = receipt["verdict"]["K4_the_ceiling_of_parameter_free_repair_is_counted_not_claimed"]
    assert k4["fraction_of_failed"] is not None
    assert k4["fraction_of_failed"] < 0.2
    k2 = receipt["verdict"]["K2_the_word_is_supplied_by_the_check_or_the_refusal"]
    assert (k2["fraction_all"] or 0) < (k2["fraction_any"] or 1)


def test_zero_model_and_parameters(receipt: dict) -> None:
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    source = TOOL.read_text()
    for forbidden in ("import requests", "from openai", "import anthropic"):
        assert forbidden not in source
