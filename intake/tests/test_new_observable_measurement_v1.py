"""Pin the positive: a trace-computed observable split all four cells without a verdict error."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "intake" / "RECEIPT_NEW_OBSERVABLE_20261121_V1.json"


def test_a_new_observable_splits_a_cell_and_lowers_the_worst_case_bill() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    best = report["verdict"]["N4_cell_bill_improves"]
    assert report["all_criteria_met"] is True
    assert best["split_cells"] >= 1
    assert best["refined_cells"] > best["base_cells"]
    assert best["worst_case_bill_after"] < best["worst_case_bill_before"]


def test_the_refined_table_is_exact_on_untouched_runs() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    held = report["verdict"]["N4_cell_bill_improves"]["held_out"]
    assert held["undecided"] == 0
    assert held["false_accepts"] == 0
    assert held["false_rejects"] == 0


def test_no_candidate_was_named_from_a_label() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = report["all_candidates"]
    assert rows
    assert all("label" not in row["observable"] for row in rows)
    assert any(row["exact"] for row in rows)
