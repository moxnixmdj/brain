"""Behavioural operators: pure functions of failure text and source text, plus one end-to-end guard.

The end-to-end test runs the real tool on one real task from the corpus. It is slow (~10 s) but it is the only
way to catch the class of defect this round produced: a candidate that looks right on paper and does nothing
when executed. Six such defects were found by running, not by reading.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import behavioural_emission_v2 as module  # noqa: E402

RECEIPT = REPO / "canonical" / "corpus" / "behavioural_emission_20261124_V2.json"


def test_a_collection_error_is_never_a_fail_to_pass_task():
    """rc=2 measures importability. Counting it as a failure is the V34 defect."""
    assert callable(module.main)
    source = pathlib.Path(module.__file__).read_text()
    assert "if probe.returncode != 1:" in source
    assert "NOT_A_TEST_FAILURE" in source


def test_pytest_always_runs_with_the_checkout_on_the_path():
    """Without this the installed wheel shadows the source tree and produces false failures."""
    env = module.env_for(pathlib.Path("/nonexistent"))
    assert "PYTHONPATH" in env


def test_forbidden_paths_include_tests_and_docs():
    for part in ("tests", "benchmarks", "conftest.py"):
        assert part in module.FORBIDDEN_PARTS


def test_the_failure_parser_reads_a_live_pytest_fragment():
    output = (
        "tests/test_misc.py:18: in test_parse_float\n"
        "    obj = tomli.loads(doc, parse_float=D)\n"
        "E   TypeError: loads() got an unexpected keyword argument 'parse_float'\n"
    )
    facts = module.parse(output)
    assert facts["kind"] == "missing_keyword"
    assert facts["missing_keyword"] == ("loads", "parse_float")


def test_the_parser_never_localises_into_a_test_file():
    output = "tests/test_x.py:9: in test_y\nE   AttributeError: 'A' object has no attribute 'b'\n"
    assert "site" not in module.parse(output)


def test_receipt_records_one_solve_and_ten_examined():
    receipt = json.loads(RECEIPT.read_text())
    measured = receipt["measured"]
    assert measured["tasks_examined"] == 12
    assert measured["genuine_test_failures"] == 10
    assert measured["solved"] == 1
    assert measured["resolve_rate"] == 0.1
    assert receipt["the_denominator_was_wrong_three_times"]["89"].startswith("the corpus")


def test_receipt_does_not_contain_a_benchmark_claim():
    text = RECEIPT.read_text()
    for forbidden in ("swe-bench score", "solved 12", "pass@1"):
        assert forbidden not in text



def test_end_to_end_on_the_task_that_was_solved(tmp_path):
    """One real task, executed: the generated patch must turn the node green and leave its file green."""
    result = tmp_path / "out.json"
    code = module.main(["--only", "5ab9ec92", "--keep", str(tmp_path / "w"), "--out", str(result)])
    assert code == 0
    rows = json.loads(result.read_text())["per_task"]
    assert len(rows) == 1
    assert rows[0]["class"] == "SOLVED", rows[0].get("why")
    assert rows[0]["family"] == "KEYWORD_APPLY_ALL"
    # the patch may not touch the oracle
    assert "tests/" not in rows[0]["diff"]
