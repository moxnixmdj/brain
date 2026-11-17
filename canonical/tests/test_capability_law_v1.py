"""The composed law, and the property that makes it usable: it refuses to compute without receipts.

The load-bearing assertions are the two the decision rests on:

  * at the operating point the two slopes are equal (0.5445 and 0.5469) and only the observation has
    leverage, because determinacy is trace-bounded;
  * the law raises -- not defaults -- when a receipt is missing or has changed.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import capability_law_v1 as law  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "CAPABILITY_LAW_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_the_law_is_reproducible_and_pins_its_receipts(report: dict) -> None:
    live = law.compose(pins=law.pins_from(report))
    assert live["terms"] == report["terms"]
    assert live["operating_point"] == report["operating_point"]
    assert live["leverage"] == report["leverage"]
    assert set(report["receipts"]) == {"determinacy", "value", "memory", "observation", "permanence",
                                       "computer", "projection", "contract", "facts"}


def test_the_terms_are_the_published_numbers(report: dict) -> None:
    terms = report["terms"]
    assert terms["determined"]["value"] == 0.5469
    assert terms["determined_value"]["value"] == 0.2143
    assert terms["check_density"]["value"] == 0.6788
    assert terms["check_strength"]["value"] == 0.8021
    assert terms["seen"]["value"] == 0.5445
    assert terms["memory_exact"]["value"] == 0.0481
    assert terms["silent_corruption"]["value"] == 0.3114


def test_the_operating_point_is_the_product_it_claims(report: dict) -> None:
    terms, point = report["terms"], report["operating_point"]
    assert point["p_correct"] == round(terms["determined"]["value"] * terms["seen"]["value"], 4)
    assert point["p_correct_value_bearing"] == round(
        terms["determined_value"]["value"] * terms["seen"]["value"], 4)


def test_leverage_is_slope_times_controllability_not_slope(report: dict) -> None:
    lev = report["leverage"]
    # the slopes are within 0.003 of each other: slope alone would say "spend anywhere"
    assert abs(lev["determined"]["slope"] - lev["check_density"]["slope"]) < 0.01
    assert lev["determined"]["controllable"] is False
    assert lev["determined"]["leverage"] == 0.0
    assert lev["check_density"]["controllable"] is True
    assert lev["check_density"]["leverage"] == 0.5469


def test_observability_is_a_multiplier_and_has_a_ceiling(report: dict) -> None:
    ceiling = report["ceiling"]
    assert ceiling["determinacy_ceiling"] == 0.70
    # even at density 1.0 the induction cap binds
    assert ceiling["p_correct_at_full_observability"] == 0.5469
    scenarios = report["scenarios"]
    assert [cell["check_density"] for cell in scenarios] == [0.6788, 0.8, 0.9, 1.0]
    assert scenarios[-1]["p_correct"] == 0.4387


def test_computer_use_carries_a_receipt_instead_of_an_assumption(report: dict) -> None:
    cell = report["computer_use"]
    assert cell["status"] == "MEASURED_ON_A_SHELL_ENVIRONMENT"
    assert cell["receipt"].endswith("COMPUTER_USE_CHECK_DENSITY_20261116_V1.json")
    # replay is complete, novelty is not: that asymmetry is the point of the receipt
    assert cell["replay"]["density"] == 1.0
    assert cell["novel"]["density"] == 0.5
    assert cell["observation_sensitivity"]["listing"] == 0.7647
    assert cell["invisible_with_a_name_level_view"] == 0.2353
    # what is not measured is still named, not defaulted
    assert "GUI" in cell["what_remains_unmeasured"]
    # the constructive half: the oracle is synthesised, and stability throws the timestamp out
    synthesis = cell["oracle_synthesis"]
    assert synthesis["cover_size_histogram"] == {"1": 9}
    assert synthesis["tasks_where_content_alone_suffices"] == synthesis["tasks"] == 9
    assert "mtime" in synthesis["features_rejected_by_stability"]
    prospective = cell["prospective"]
    assert prospective["arms"] == {"no_recorded_consequence": 0.5, "frame_only": 0.9706,
                                   "frame_plus_intervention": 0.9706, "full": 1.0}
    assert prospective["false_alarms_on_correct_novel_actions"] == 0
    assert prospective["content_only_errors"]["frame_only"] < prospective["content_only_errors"]["full"]
    horizon = cell["horizon"]
    assert horizon["chains"] == 3
    assert horizon["every_step_legal_and_passing"] == 3
    assert horizon["standing_fact_ledger_detected"] == 3
    assert horizon["false_invalidations_on_controls"] == 0
    assert horizon["lead_in_steps"] == 2
    assert "OSWorld" in cell["external_context"]


def test_a_missing_receipt_raises_instead_of_defaulting(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(law, "ROOT", tmp_path)
    with pytest.raises(law.CapabilityLawIncomplete):
        law.compose()


def test_a_changed_receipt_raises_instead_of_being_used(tmp_path, monkeypatch, report: dict) -> None:
    for name, path in law.RECEIPTS.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(law, "ROOT", tmp_path)
    pins = {name: "deadbeefdeadbeef" for name in law.RECEIPTS}
    with pytest.raises(law.CapabilityLawIncomplete):
        law.compose(pins=pins)
