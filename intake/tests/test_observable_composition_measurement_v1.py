"""Pin the composition result: inner validation avoids overfitting but does not pay the bill."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTAKE = ROOT / "intake"
RECEIPTS = (
    "RECEIPT_OBSERVABLE_COMPOSITION_20261121_V1.json",
    "RECEIPT_OBSERVABLE_COMPOSITION_DIAGNOSTIC6_20261121_V1.json",
    "RECEIPT_OBSERVABLE_COMPOSITION_UNCORRECTED_20261121_V1.json",
)


def _load(name: str) -> dict:
    return json.loads((INTAKE / name).read_text(encoding="utf-8"))


def test_all_composition_runs_keep_the_pre_registered_failure() -> None:
    for name in RECEIPTS:
        report = _load(name)
        assert report["declared_before_the_runs"]["M3"].startswith("the chosen composition lowers")
        assert report["all_criteria_met"] is False
        assert report["verdict"]["M3_bill_below_one_hundred"]["MET"] is False or (
            report["verdict"]["M4_held_out_exactness"]["MET"] is False)


def test_inner_validation_prevented_the_large_overfit() -> None:
    corrected = _load(RECEIPTS[0])["verdict"]["M4_held_out_exactness"]
    uncorrected = _load(RECEIPTS[2])["verdict"]["M4_held_out_exactness"]
    assert corrected["undecided"] < uncorrected["undecided"]
    assert corrected["false_accepts"] == uncorrected["false_accepts"] == 0
    assert _load(RECEIPTS[0])["verdict"]["M1_selection_uses_only_training_labels"]["inner_validation"] > 0


def test_more_observables_did_not_fix_the_bill() -> None:
    three = _load(RECEIPTS[0])["verdict"]
    six = _load(RECEIPTS[1])["verdict"]
    assert six["M3_bill_below_one_hundred"]["worst_case_bill"] >= 100
    assert six["M4_held_out_exactness"]["undecided"] > 0
    assert six["M4_held_out_exactness"]["MET"] is False
    assert three["M4_held_out_exactness"]["MET"] is False
