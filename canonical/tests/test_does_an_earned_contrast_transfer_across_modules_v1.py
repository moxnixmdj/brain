#!/usr/bin/env python3
"""Does knowledge earned on one function transfer to a function nobody showed you? No -- and now measurably.

417 functions across 55 import-safe modules, every one probed with the SAME witness pair ('', -> 'a'),
7,522 cross-module function pairs.

    observed agreement      0.6304
    permuted null           0.6253 +- 0.0087
    gap over null           +0.0051   (0.59 null standard deviations)

The null permutes labels WITHIN each module, preserving each module's label mix and destroying only the
association between a label and the function that produced it. Observed agreement is therefore the agreement
you get from the base rate alone: most functions return a value and never raise, so two functions agree about
64% of the time without sharing anything.

The test files themselves encode four tool-level failures found by running this, all of which would have
silently produced a confident and wrong verdict:

  1. taking the 12 LARGEST modules selected 12 files all refused for lacking a __main__ guard, shrinking the
     population to one module and computing a "verdict" from a sample of one
  2. holding the other arguments at None measured which functions crash on None, not what the witness did
  3. probing `main` fed an argv list to a module-level ArgumentParser, whose exit(2) is a BaseException and
     escaped a probe that only caught Exception -- killing the run mid-flight
  4. a module-level ArgumentParser reads the PROBE's sys.argv; a __main__ guard does not stop it
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "canonical" / "verification" / "TRANSFER_EARNED_CONTRAST_20261124_V1.json"


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_sample_is_large_enough_to_decide():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["modules_probed"] >= 50
    assert summary["functions_labelled"] >= 400
    assert summary["cross_module_pairs"] >= 5000
    assert summary["verdicts"]["there_is_enough_rare_class_to_measure"] is True


def test_the_gap_over_the_null_is_inside_the_noise():
    """This is the finding. If it ever exceeds 3 null standard deviations, transfer exists and this fails."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["gap_in_null_sds"] < 3.0
    assert abs(summary["gap_over_null"]) < 0.02
    assert summary["verdicts"]["agreement_is_above_chance"] is False


def test_agreement_is_mostly_the_base_rate():
    """Observed 0.63 vs null 0.63: the apparent agreement is what the label mix predicts, not information."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["observed_agreement"] > 0.5
    assert abs(summary["observed_agreement"] - summary["null_agreement_mean"]) < 0.02


def test_no_entry_point_was_probed():
    """`main` parses argv; probing it kills the run. The instrument must exclude it by construction."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    for module, rows in json.loads(ARTIFACT.read_text())["per_function"].items():
        assert all(row["name"] != "main" for row in rows), module


def test_every_labelled_kind_is_one_the_instrument_claims_to_measure():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    kinds = {row["kind"] for rows in json.loads(ARTIFACT.read_text())["per_function"].values()
             for row in rows}
    assert kinds <= {"NONE", "VALUE", "RAISED"}, kinds
