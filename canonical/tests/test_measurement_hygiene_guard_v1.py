#!/usr/bin/env python3
"""A metric that looks finished is the recurring defect. This tests the guard against that defect.

The guard policed 33 of 2,986 receipts, flagged 17, and resolved each one in an explicit ledger naming what
was missing and whether it changes that receipt's conclusion. One of the 17 is marked PARTLY material (V24's
cross-codebase accuracy claim has no base-rate comparator).

The tests below prove the guard can FAIL -- a guard that cannot fail is decoration.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "canonical" / "tools"), str(REPO)]
import measurement_hygiene_guard_v1 as guard  # noqa: E402

ARTIFACT = REPO / "canonical" / "verification" / "MEASUREMENT_HYGIENE_20261124_V1.json"


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_it_catches_a_receipt_that_reports_accuracy_without_a_baseline(tmp_path):
    """The V25/V28 shape: a bare accuracy that could be the majority class."""
    bad = tmp_path / "BAD_RECEIPT.json"
    bad.write_text(json.dumps({
        "summary": {"accuracy": 0.99, "predictions": 10, "wrong": 1,
                    "verdicts": {"works": True}},
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0}}))
    cell = guard.check_receipt(bad)
    assert "MAJORITY_CLASS_WITHOUT_BASELINE" in cell["findings"]
    assert "ACCURACY_WITHOUT_SENSITIVITY" in cell["findings"]


def test_it_catches_a_summary_line_carrying_a_wall_clock(tmp_path):
    """The V27 shape: the compared value changes every run."""
    bad = tmp_path / "TIMED.json"
    bad.write_text(json.dumps({
        "summary": {"baseline": "11 passed in 1.34s", "verdicts": {"works": True},
                    "majority_class_accuracy": 0.5, "accuracy": 0.5, "sensitivity": 0.5,
                    "n": 4, "wrong": 0},
        "cost": {"model_calls": 0}}))
    assert "TIMING_IN_COMPARATOR" in guard.check_receipt(bad)["findings"]


def test_it_catches_missing_cost_disclosures(tmp_path):
    clean_but_undisclosed = tmp_path / "NOCOST.json"
    clean_but_undisclosed.write_text(json.dumps({
        "summary": {"accuracy": 0.5, "majority_class_accuracy": 0.5, "sensitivity": 0.5,
                    "n": 4, "wrong": 0, "verdicts": {"x": True}}}))
    assert "INSTRUMENT_WITHOUT_COST" in guard.check_receipt(clean_but_undisclosed)["findings"]


def test_a_receipt_that_obeys_every_rule_passes_cleanly(tmp_path):
    good = tmp_path / "GOOD.json"
    good.write_text(json.dumps({
        "summary": {"accuracy": 0.9, "majority_class_accuracy": 0.5, "sensitivity": 0.8,
                    "n": 10, "wrong": 1, "verdicts": {"x": True}},
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0}}))
    assert guard.check_receipt(good)["findings"] == []


def test_every_flagged_receipt_in_the_repo_is_resolved_or_the_guard_fails():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    ledger = summary["defect_ledger"]
    assert ledger["unresolved"] == [], "an unresolved finding must fail the run, not be waived"
    assert ledger["flagged"] == ledger["resolved"]
    assert ledger["flagged"] >= 17, "the guard must have found real defects, not zero by construction"


def test_the_partly_material_finding_is_named_not_buried():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    assert _summary()["defect_ledger"]["material"] == [
        "PRICE_A_REFUSAL_ON_REAL_CODE_20261124_V2.json"]
