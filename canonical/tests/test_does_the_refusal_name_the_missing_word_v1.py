"""Tests for the round that asks whether a refusal names the missing word.

The dangerous failure mode here is a harness that reports a failure it did not cause --
a missing pytest was once read as a failing test. So one test builds a real repository
with a real failing test and requires the harness to see exactly that failure.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/does_the_refusal_name_the_missing_word_v1.py"
RECEIPT = ROOT / "canonical/verification/DOES_THE_REFUSAL_NAME_THE_MISSING_WORD_20261119_V1.json"

GATES = [
    "K1_the_measurement_runs_real_suites_at_the_parent_commit",
    "K2_refusals_name_a_word_the_fix_adds",
    "K3_the_outcome_is_reported_per_shape_not_as_a_score",
    "K4_zero",
]


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("refusal_names", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_schema_and_authority(receipt: dict) -> None:
    assert receipt["schema"] == "BRAIN_DOES_THE_REFUSAL_NAME_THE_MISSING_WORD_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


@pytest.mark.parametrize("gate", GATES)
def test_every_declared_gate_is_met(receipt: dict, gate: str) -> None:
    assert receipt["verdict"][gate]["MET"] is True


def test_the_harness_separates_cannot_run_from_failed(tmp_path: pathlib.Path, tool) -> None:
    repo = tmp_path / "r"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pkg" / "__init__.py").write_text("def f(x):\n    return x + 2\n")
    (repo / "tests" / "test_f.py").write_text("from pkg import f\n\ndef test_f():\n    assert f(1) == 3\n")
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "fix"], check=True)
    sha = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True).stdout.strip()
    broken = "def f(x):\n    return x + 1\n"       # the pre-fix state: f(1) == 2
    result = tool.run_node(repo, sha, broken, "pkg/__init__.py", "tests/test_f.py::test_f")
    assert result["ran"] is True
    assert result["returncode"] == 1
    spoken = tool.refusal_text(result["output"])
    assert "assert 2 == 3" in spoken
    # and the fixed state passes, which is what makes the failure the bug and not the harness
    fixed = tool.run_node(repo, sha, "def f(x):\n    return x + 2\n", "pkg/__init__.py",
                          "tests/test_f.py::test_f")
    assert fixed["returncode"] == 0


def test_refusal_text_excludes_the_code_it_echoes(tool) -> None:
    output = ("        def test_f():\n            assert f(1) == 3\n"
              "E       assert 2 == 3\nE        +  where 2 = f(1)\n"
              "=========================== short test summary info ===========================\n"
              "FAILED tests/test_f.py::test_f - assert 2 == 3\n")
    spoken = tool.refusal_text(output)
    assert "assert 2 == 3" in spoken
    assert "def test_f()" not in spoken


def test_new_words_are_the_fixs_own_new_words(tool) -> None:
    before = "import pickle\n\ndef f(x):\n    return x\n"
    after = "import copyreg\n\ndef f(x):\n    return copyreg.__reduce_ex__(x, 'tag')\n"
    words = tool.new_words(before, after)
    assert "copyreg" in words["names"]
    assert "__reduce_ex__" in words["names"]
    assert "pickle" not in words["names"]
    assert "tag" in words["strings"]


def test_naming_is_a_whole_word_not_a_substring(tool) -> None:
    assert tool.named_in("state", "the object has no state here", is_name=True) is True
    assert tool.named_in("state", "statement about estates", is_name=True) is False


def test_the_receipt_counts_are_internally_consistent(receipt: dict) -> None:
    k1 = receipt["verdict"]["K1_the_measurement_runs_real_suites_at_the_parent_commit"]
    k2 = receipt["verdict"]["K2_refusals_name_a_word_the_fix_adds"]
    rows = receipt["per_task"]
    assert k1["tasks"] == len(rows)
    assert k1["ran"] == sum(1 for r in rows if r.get("ran"))
    assert k1["could_not_run"] == k1["tasks"] - k1["ran"]
    assert k1["failed_at_parent_as_recorded"] == sum(
        1 for r in rows if r.get("ran") and r.get("failed_at_parent"))
    assert k2["named_any_new_word"] == sum(
        1 for r in rows if r.get("failed_at_parent") and r.get("refusal_names_a_new_word"))
    assert k2["fixes_with_a_new_word"] == sum(
        1 for r in rows if r.get("failed_at_parent") and (r.get("new_names") or r.get("new_strings")))
    shapes = receipt["verdict"]["K3_the_outcome_is_reported_per_shape_not_as_a_score"]["shapes"]
    assert sum(b["tasks"] for b in shapes.values()) == k1["failed_at_parent_as_recorded"]


def test_a_task_that_could_not_run_is_never_counted_as_evidence(receipt: dict) -> None:
    for row in receipt["per_task"]:
        if not row.get("ran"):
            assert row.get("reason"), row
            assert not row.get("refusal_names_a_new_word")


def test_zero_model_and_parameters(receipt: dict) -> None:
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    source = TOOL.read_text()
    for forbidden in ("import requests", "from openai", "import socket"):
        assert forbidden not in source


def test_the_result_is_far_from_total_and_is_not_reported_as_success(receipt: dict) -> None:
    """The honest reading: the refusal grades, and names the word only sometimes."""
    k2 = receipt["verdict"]["K2_refusals_name_a_word_the_fix_adds"]
    assert k2["fraction_any"] is not None
    assert k2["fraction_any"] < 1.0
    assert k2["named_any_new_word"] > 0
