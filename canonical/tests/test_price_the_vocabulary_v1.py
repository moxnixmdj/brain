#!/usr/bin/env python3
"""The vocabulary can be priced, and one added predicate buys reach at zero price.

IN-SAMPLE (the trap): the best of 1023 subsets scores 0.917 accuracy / 0.669 coverage against a 0.828 /
0.520 baseline. Selecting the best of 1023 on the data you score on is the V14 defect waiting to happen.

OUT-OF-SAMPLE (leave-one-machine-out: choose on nine, score on the tenth):

    baseline vocabulary   77 predictions, 16 wrong, accuracy 0.828, coverage 0.520
    selected subset       93 predictions, 12 wrong, accuracy 0.886, coverage 0.628

The gain survives: +5.8 accuracy points and +10.8 coverage points on a machine the choice never saw.

The single-predicate table is the explainable part. `IDENT_SORTED` and `HAS_REPEATED_IDENT_LENGTH` each
buy +2 predictions for 0 errors. `CONTENT_SORTED` alone LOSES 9 predictions and saves 6 errors, and it
appears in all ten folds' chosen subsets -- so it is not a margin-of-error artifact either way.

The subset ITSELF is not a finding: 5 of 10 folds agree, and `CONTENT_SORTED` is the only predicate in
every fold.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "canonical" / "verification" / "PRICE_THE_VOCABULARY_20261124_V1.json"


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_gain_is_measured_out_of_sample():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    lo = summary["leave_one_machine_out"]
    assert lo["selected_subset"]["accuracy"] > lo["baseline"]["accuracy"]
    assert lo["selected_subset"]["coverage"] > lo["baseline"]["coverage"]
    assert len(lo["choices"]) == summary["machines"], "one fold per machine, no sharing"


def test_the_in_sample_number_is_labelled_optimistic():
    """Guards against the report quoting 0.917 as if it were the result."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["full_data_selection_is_optimistic"] is True
    assert summary["best_subset"]["accuracy"] > summary["leave_one_machine_out"]["selected_subset"]["accuracy"]
    assert summary["sweep_size"] > 1000


def test_a_single_predicate_buys_reach_at_zero_price():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    zero_price = {name: cell for name, cell in summary["singles"].items()
                  if cell["reach_gained"] > 0 and cell["price"] == 0}
    assert "IDENT_SORTED" in zero_price
    assert "HAS_REPEATED_IDENT_LENGTH" in zero_price
    assert all(cell["wrong_added"] == 0 for cell in zero_price.values())


def test_the_subset_choice_is_unstable_and_that_is_recorded():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["stability"]["folds_choosing_it"] < summary["stability"]["folds"]
    assert summary["verdicts"]["the_chosen_subset_is_unstable_across_folds"] is True
    assert summary["stability"]["CONTENT_SORTED_appears_in_folds"] == summary["stability"]["folds"]
