"""The ceiling measurement: six one-to-four-line fixes that the operator family cannot reach.

If the operators cannot solve fixes of four lines or fewer, no claim about harder tasks can be made by
extrapolation upwards. This file keeps that result and the parser defect it exposed from being lost.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import behavioural_emission_v2 as generate  # noqa: E402

RECEIPT = REPO / "canonical" / "corpus" / "ceiling_measurement_20261124_V1.json"


def test_did_not_raise_is_parsed_in_both_pytest_forms():
    """`DID NOT RAISE <class 'X'>` and `Failed: DID NOT RAISE X` are different lines and only one was read."""
    bare = generate.parse("E   Failed: DID NOT RAISE <class 'ValueError'>\n")
    with_block = generate.parse("E       Failed: DID NOT RAISE InvalidRequirement\n")
    assert bare["kind"] == "did_not_raise"
    assert bare["expected_exception"] == "ValueError"
    assert with_block["kind"] == "did_not_raise"
    assert with_block["expected_exception"] == "InvalidRequirement"


def test_the_ceiling_subset_solves_zero():
    receipt = json.loads(RECEIPT.read_text())
    subset = receipt["the_ceiling_subset"]
    assert subset["count"] == 6
    assert subset["solved"] == 0
    assert subset["resolve_rate"] == 0.0


def test_the_six_are_described_by_what_they_change():
    receipt = json.loads(RECEIPT.read_text())
    changes = receipt["what_the_six_actually_are"]
    assert len(changes) == 6
    text = json.dumps(changes)
    assert "regex" in text
    assert "guard" in text or "early return" in text


def test_the_syntax_versus_difficulty_error_is_recorded():
    receipt = json.loads(RECEIPT.read_text())
    correction = receipt["the_error_i_corrected_this_round"]
    assert "dunder" in correction["claim"]
    assert "API redesigns" in correction["reality"]
    assert "Ninth" in correction["correction"]


def test_the_receipt_makes_no_benchmark_claim():
    receipt = json.loads(RECEIPT.read_text())
    assert "benchmark row exists or is claimed" in json.dumps(receipt)
    for forbidden in ("pass@1", "resolved_rate"):
        assert forbidden not in json.dumps(receipt)
