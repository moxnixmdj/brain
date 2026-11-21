"""Pin the measured cell price: wider conjunctions did not buy a coarser table."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "intake" / "RECEIPT_CELL_PRICE_20261121_V1.json"


def test_wider_conjunction_search_did_not_reduce_cells() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    cells = report["verdict"]["R3_coarsest_statistics"]
    assert cells["size2_projection"] == cells["size3_projection"]
    assert cells["cells_saved"] == 0
    assert report["all_criteria_met"] is True


def test_held_out_verdicts_are_exact() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    held = report["verdict"]["R4_held_out_soundness"]
    for row in (held["size2"], held["size3"]):
        assert row["false_accepts"] == 0
        assert row["false_rejects"] == 0
        assert row["undecided"] == 0


def test_the_pool_was_split_before_fitting() -> None:
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    split = report["verdict"]["R1_real_split_pool"]
    assert split["train"] + split["held_out"] == split["distinct_runs"]
    assert split["held_out"] > 0
