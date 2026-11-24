"""Does one experience make the next task cheaper? The answer decides the whole strategy.

The owner's bet: the agent does something once, learns it permanently, and the world already
publishes a guide for everything, so one demonstration per environment should total computer
use. This module tests that against the only recorded numbers that can answer it, and the
answer is that it does not compound at this size -- measured, not argued.

The tests below hold three things that would each let a false answer through:

  1. A RATIO IS NOT A COMPOUNDING CLAIM. "1.55x reuse" sounds like compounding and is not.
     The cost per unseen task is what matters, and it must be walked IN ORDER, weighted by
     the steps actually taken, or "experience helped" cannot be told from "the second half
     held easier pages".
  2. A LEVER THAT DOES NOT LOWER THE BILL IS NOT A LEVER. The tree's own note says a smaller
     description language would lower the price. Measured: the language is already minimal
     and 90% of the bill sits in three attributes that each name an element, so removing one
     removes the ability to say what a step targets.
  3. THE COST IS PAGE-SHAPED, NOT LEARNER-SHAPED. It is log2 of the candidates that still
     fit. If most real steps face more than 30 of them, no amount of experience lowers it.

Every number here is read from the recorded receipt; no episode is invented.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import does_experience_compound_v1 as D  # noqa: E402


@pytest.fixture(scope="module")
def record():
    if not D.RECORDED.exists():
        pytest.skip("the recorded one-success run is not in this tree")
    return json.loads(D.RECORDED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def answer(record):
    return D.verdict(record)


def test_the_receipt_is_read_not_invented(record, answer):
    assert answer["read_from"].endswith(".json")
    assert answer["model_calls"] == 0 and answer["parameters"] == 0
    assert D.steps_of(record), "no steps with a measured descriptions_left were found"


def test_one_step_costs_several_bits_and_an_experience_pays_about_one(email=None):
    """The prior this round inherits, re-measured rather than assumed: a step costs about
    five bits, so a single demonstration cannot identify a program."""
    record = json.loads(D.RECORDED.read_text(encoding="utf-8"))
    values = [int(s["descriptions_left"]) for s in D.steps_of(record)]
    mean_bits = sum(D.bits(v) for v in values) / len(values)
    assert 4.0 < mean_bits < 6.5, f"mean cost per step was {mean_bits:.2f} bits"
    share_over_one_bit = sum(1 for v in values if D.bits(v) > 1.0) / len(values)
    assert share_over_one_bit > 0.9, "most steps should need more than the one bit an experience pays"


# --------------------------------------------------------------------------- #
# the claim under test
# --------------------------------------------------------------------------- #
def test_experience_does_not_compound_at_this_size(answer):
    """THE CENTRAL RESULT, and it is negative.

    If experience compounded, the second half of the run -- the part that comes after the
    learning -- would be measurably cheaper. It moves by -0.10 bits per step over the whole
    run, which is flat within what this measurement can resolve. The threshold is stated so
    that a later round cannot quietly call a 0.1-bit drift compounding.
    """
    compound = answer["does_experience_compound"]
    assert compound["verdict"] == D.FLAT, compound["verdict"]
    assert abs(compound["change_bits_per_step"]) < compound["threshold_bits_per_step"]


def test_a_ratio_is_not_evidence_of_compounding(answer):
    """The vocabulary does grow and reuse is real -- and neither is compounding. This asserts
    both facts together, because quoting the first as if it were the second is exactly the
    mistake the module exists to prevent."""
    compound = answer["does_experience_compound"]
    assert compound["distinct_descriptions"] > 50, "expected real vocabulary"
    assert compound["share_of_descriptions_added_in_second_half"] > 0.3, (
        "the vocabulary should still be growing in the second half; if it has started to "
        "saturate, the FLAT verdict needs revisiting")
    assert compound["verdict"] == D.FLAT


def test_the_cost_is_spread_over_necessary_attributes(answer):
    """The lever the tree named -- a smaller description language -- measured and found
    already spent: three attributes that each name an element carry 90% of the bill."""
    bill = answer["where_the_cost_lives"]
    assert bill["language_is_already_small"] is True
    assert bill["top_three_share"] >= 0.8
    assert bill["conjunctions"] == 0, "a conjunction would mean there was room to drop an atom"
    total = sum(row["bits"] for row in bill["by_attribute"].values())
    assert total == pytest.approx(bill["total_bits"], abs=1.0)


def test_the_cost_is_page_shaped_not_learner_shaped(answer):
    """log2 of the candidates that still fit. Most real steps face more than thirty."""
    spread = answer["is_the_cost_page_shaped"]
    assert spread["share_above_30_candidates"] > 0.5
    assert spread["max"] > spread["median"] > spread["min"]
    assert sum(band["steps"] for band in spread["bands"]) == spread["steps"]


# --------------------------------------------------------------------------- #
# the module must not overclaim
# --------------------------------------------------------------------------- #
def test_it_refuses_to_call_the_bits_irreducible_or_one_experience_useless(answer):
    refused = " ".join(answer["what_this_refuses_to_claim"])
    assert "irreducible" in refused
    assert "useless" in refused
    assert "generalises beyond MiniWoB" in refused


def test_the_verdict_moves_if_the_curve_does():
    """A guard against a hard-coded answer: synthesise a receipt whose second half IS cheaper
    and require the verdict to change. If this passes with FLAT, the verdict is a constant."""
    cheap_late = {"tasks": [
        {"task": f"t{i}", "arms": {"version_space": {"learning": {"skills": {"per_program": [
            {"steps": [{"descriptions_left": (200 if i < 4 else 2), "first": f"d{i}"}]}]}}}}}
        for i in range(8)]}
    changed = D.compounding(cheap_late)
    assert changed["bits_per_step_second_half"] < changed["bits_per_step_first_half"]
    assert changed["verdict"] == D.COMPOUNDS, (
        "the verdict did not follow the data; it is a constant and not a measurement")


def test_an_anti_compounding_receipt_is_also_detected():
    worse_late = {"tasks": [
        {"task": f"t{i}", "arms": {"version_space": {"learning": {"skills": {"per_program": [
            {"steps": [{"descriptions_left": (2 if i < 4 else 200), "first": f"d{i}"}]}]}}}}}
        for i in range(8)]}
    changed = D.compounding(worse_late)
    assert changed["verdict"] == D.ANTI_COMPOUNDS
