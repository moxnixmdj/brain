"""Tests for the contract-veto repair round on two real QuixBugs programs.

The public corpus is not needed to run these tests: the receipt carries the
measured rows, and the pure Python parts (mutation grammar, contract selection,
control patch, zero-cost declarations) are checked directly here.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import canonical.tools.contract_veto_repair_v1 as tool  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_test_guided_patch_search_v1 as patch)

RECEIPT = ROOT / "canonical/verification/CONTRACT_VETO_REPAIR_20261121_V1.json"


def test_receipt_criteria_are_all_met() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["schema"] == tool.SCHEMA
    assert receipt["criteria_were_declared_before_the_receipt_run"] is True
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    assert all(row["MET"] for row in receipt["verdict"].values())
    assert {row["task"] for row in receipt["rows"]} == set(tool.TASKS)
    for row in receipt["rows"]:
        assert row["status"].startswith("PASS__")
        assert row["accepted_edit_count"] == 1
        assert row["candidates"] <= 100
        assert row["fresh_published_rc"] == 0
        assert row["fresh_contract_rc"] == 0
        assert all(p["applied"] for p in row["fresh_patch_applied"])
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_control_patch_passed_published_but_was_refused_by_the_contract() -> None:
    receipt = json.loads(RECEIPT.read_text())
    control = receipt["verdict"]["S3_contract_refutes_the_published_only_patch"]["control"]
    assert control["applied"] is True
    assert control["published_rc"] == 0
    assert control["contract_rc"] != 0
    assert "binsearch(mid, start)" in tool.PUBLISHED_ONLY_PATCH
    assert "binsearch(mid + 1, end)" in tool.PUBLISHED_ONLY_PATCH


def test_structural_mutations_are_opt_in_and_contain_the_measured_edits() -> None:
    gcd = "def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(a % b, b)\n"
    midpoint = ("def f(arr, x):\n"
                "    mid = start + (end - start) // 2\n"
                "    return binsearch(mid, end)\n")
    for source, expected in ((gcd, "gcd:args 0<->1"), (midpoint, "mid->mid+1")):
        tree = ast.parse(source)
        default = list(patch._candidate_specs(tree, [], []))
        extended = list(patch._candidate_specs(tree, [], [], structural=True))
        assert len(extended) > len(default)
        assert all(d["family"] not in ("structural_call", "structural_index")
                   for _, d, _ in default)
        assert any(d["family"] in ("structural_call", "structural_index") and
                   d["detail"] == expected for _, d, _ in extended)


def test_contract_is_selected_from_the_output_sentence_not_an_answer_key() -> None:
    assert "index" in tool.INDEX_CONTRACT.lower()
    assert "if r == -1" in tool.INDEX_CONTRACT
    assert "assert x not in arr" in tool.INDEX_CONTRACT
    assert "gcd" in tool.GCD_CONTRACT and "math.gcd" in tool.GCD_CONTRACT
    assert "a % r == 0" in tool.GCD_CONTRACT and "b % r == 0" in tool.GCD_CONTRACT
    assert "return gcd(b, a % b)" not in tool.GCD_CONTRACT
    assert "return binsearch(mid + 1, end)" not in tool.INDEX_CONTRACT
    assert tool.contract_from_docstring.__name__ == "contract_from_docstring"
