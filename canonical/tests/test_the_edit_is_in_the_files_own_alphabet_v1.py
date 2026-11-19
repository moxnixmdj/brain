"""Tests for the round that measures what a real fix is made of.

The tool can return a zero. A zero from a mechanism that never fires is
indistinguishable from a broken one, so the synthetic tests here make each origin
class fire at least once before the corpus numbers are trusted.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/the_edit_is_in_the_files_own_alphabet_v1.py"
RECEIPT = ROOT / "canonical/verification/WHAT_A_REAL_FIX_IS_MADE_OF_20261119_V1.json"
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"

GATES = [
    "K1_a_real_fix_is_measured_in_tokens",
    "K2_containment_versus_k_is_exact",
    "K3_when_the_edit_is_one_token_the_missing_word_is_priced_by_origin",
    "K4_the_price_of_blind_generate_and_verify",
    "K5_the_corpus_is_real_history_and_the_run_is_offline",
    "K6_zero",
]


def load_tool():
    spec = importlib.util.spec_from_file_location("real_fix_measure", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return load_tool()


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


@pytest.fixture(scope="module")
def corpus() -> dict:
    return json.loads(CORPUS.read_text())


def task_of(tool, before: str, after: str) -> dict:
    return tool.measure_task({"repo": "x/y", "sha": "0" * 40, "source": "m.py",
                              "before": before, "after": after},
                             machine=tool.machine_alphabet())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_WHAT_A_REAL_FIX_IS_MADE_OF_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_declared_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_the_corpus_is_real_history_with_both_states(corpus: dict) -> None:
    assert corpus["schema"] == "BRAIN_REAL_FIX_PAIRS_V1"
    tasks = corpus["tasks"]
    assert len(tasks) == 87
    assert len({t["repo"] for t in tasks}) == 3
    assert all(t["before"] != t["after"] for t in tasks)
    assert all(len(t["sha"]) == 40 and len(t["parent"]) == 40 for t in tasks)
    assert sum(len(t["before"]) + len(t["after"]) for t in tasks) > 3_000_000


def test_line_count_split_sums_to_the_corpus(receipt: dict) -> None:
    k1 = receipt["verdict"]["K1_a_real_fix_is_measured_in_tokens"]
    assert k1["line_count_preserved"] + k1["line_count_changed"] == k1["tasks"]


def test_containment_is_monotone_in_k(receipt: dict) -> None:
    k2 = receipt["verdict"]["K2_containment_versus_k_is_exact"]
    assert 0 <= k2["contained_at_1"] <= k2["contained_at_2"] <= k2["contained_at_3"]
    assert k2["contained_at_3"] <= k2["contained_at_5"] <= k2["contained_at_all"]
    assert k2["contained_at_all"] == receipt["verdict"]["K1_a_real_fix_is_measured_in_tokens"][
        "line_count_preserved"]


def test_every_task_is_classified_and_shapes_sum(receipt: dict) -> None:
    rows = receipt["per_task"]
    shapes: dict[str, int] = {}
    for row in rows:
        shapes[row["shape"]] = shapes.get(row["shape"], 0) + 1
    assert shapes == receipt["verdict"]["K5_the_corpus_is_real_history_and_the_run_is_offline"]["shapes"]
    assert sum(shapes.values()) == len(rows)
    known = {"line_count_changed", "no_change", "untokenisable", "one_token_from_the_file",
             "one_token_from_the_machine", "one_token_inside_a_literal", "one_token_from_nowhere",
             "multi_token_within_the_lines", "one_token_inserted_or_deleted"}
    assert set(shapes) <= known


def test_the_one_token_census_sums(receipt: dict) -> None:
    k3 = receipt["verdict"]["K3_when_the_edit_is_one_token_the_missing_word_is_priced_by_origin"]
    parts = (k3["from_the_files_own_alphabet"] + k3["from_the_machines_own_alphabet"]
             + k3["inside_a_string_literal"] + k3["from_nowhere_in_the_environment"]
             + k3["inserted_or_deleted_rather_than_substituted"])
    assert parts == k3["one_token_edits"]
    assert parts == receipt["verdict"]["K2_containment_versus_k_is_exact"]["contained_at_1"]


# --- the mechanism must fire, or its zero means nothing -----------------------

def test_a_word_the_file_already_contains_is_classified_from_the_file(tool) -> None:
    before = ("def f(x):\n    return x + 1\n\ndef g(y):\n    return y * 2\n\n"
              "def h(z):\n    return z - 1\n")
    after = before.replace("return x + 1", "return x - 1")
    row = task_of(tool, before, after)
    assert row["distance"] == 1
    assert row["shape"] == "one_token_from_the_file"
    assert row["witnesses"][0]["was"] == "+" and row["witnesses"][0]["became"] == "-"


def test_a_word_only_the_machine_has_is_classified_from_the_machine(tool) -> None:
    before = 'def f(s):\n    return s.split(",", 1)\n'
    after = 'def f(s):\n    return s.rsplit(",", 1)\n'
    row = task_of(tool, before, after)
    assert row["distance"] == 1
    assert row["shape"] == "one_token_from_the_machine"
    assert "rsplit" in tool.machine_alphabet()["name"]
    assert "rsplit" not in before


def test_a_change_inside_a_literal_is_its_own_class(tool) -> None:
    before = 'PATTERN = re.compile(r"(\\\\d+)(.*)")\n'
    after = 'PATTERN = re.compile(r"(\\\\d+)(.*)\\\\Z")\n'
    row = task_of(tool, before, after)
    assert row["shape"] == "one_token_inside_a_literal"


def test_a_word_nowhere_in_the_environment_is_named_as_such(tool) -> None:
    before = "def f(x):\n    return frobnicate(x)\n"
    after = "def f(x):\n    return defenestrate(x)\n"
    row = task_of(tool, before, after)
    assert row["shape"] == "one_token_from_nowhere"


def test_a_line_added_is_not_a_vocabulary_miss_but_its_own_class(tool) -> None:
    before = "def f(x):\n    return x\n"
    after = "def f(x):\n    x = abs(x)\n    return x\n"
    row = task_of(tool, before, after)
    assert row["shape"] == "line_count_changed"
    assert row["distance"] is None


def test_distance_is_exact_not_estimated(tool) -> None:
    before = "def f(a, b):\n    return a + b\n"
    after = "def f(a, b):\n    return b - a\n"
    row = task_of(tool, before, after)
    assert row["distance"] == 3  # one op, and two names swapped


def test_price_is_counted_per_candidate_program(receipt: dict) -> None:
    k4 = receipt["verdict"]["K4_the_price_of_blind_generate_and_verify"]
    price = k4["candidates_for_a_one_token_edit"]
    assert price["median"] is not None and price["max"] is not None
    assert 0 < price["median"] <= price["max"]
    rows = [r for r in receipt["per_task"] if r["distance"] == 1]
    assert all(sum(r["candidates_per_changed_line"]) > 0 for r in rows)


def test_zero_model_parameters_network(receipt: dict, tool) -> None:
    assert receipt["cost"] == {"model_calls": 0, "parameters_stored": 0,
                               "network_calls_at_run_time": 0}
    source = TOOL.read_text()
    for forbidden in ("import requests", "import socket", "urllib.request", "http.client"):
        assert forbidden not in source


def test_the_receipt_reproduces_exactly(tmp_path: pathlib.Path) -> None:
    committed = json.loads(RECEIPT.read_text())["verdict"]
    out = tmp_path / "receipt.json"
    run = subprocess.run([sys.executable, str(TOOL), "--receipt", str(out)],
                         capture_output=True, text=True, check=True)
    assert run.returncode == 0
    fresh = json.loads(out.read_text())["verdict"]
    assert json.dumps(fresh, sort_keys=True) == json.dumps(committed, sort_keys=True)
    assert json.dumps(load_tool().measure()["verdict"], sort_keys=True) == json.dumps(
        committed, sort_keys=True)
