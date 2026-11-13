"""Pins `weight_space_fuel_v1.py` and the three corrections that made it honest.

The gauge is only useful if it cannot quietly over- or under-count. Two of its first versions were
wrong in opposite directions -- one said "nothing to train on" because it never opened the only file
kind with an event stream, the other reported a 45% failure rate because it counted terminal `finish`
steps as failures. Both are pinned here.

Run: python3 -m pytest canonical/tests/test_weight_space_fuel_v1.py -q
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

record_path = ROOT / "canonical/verification/WEIGHT_SPACE_FUEL_20261113_V1.json"


def measure():
    from canonical.tools import weight_space_fuel_v1 as gauge

    return gauge


@pytest.fixture(scope="module")
def result():
    return measure().measure()


# ---------------------------------------------------------------- 1. the sources it must not miss


def test_the_gauge_looks_at_controller_checkpoints(result):
    """The first version reported 'nothing to train on' because it never opened these files."""
    assert "controller_checkpoints" in result["sources"]
    row = result["sources"]["controller_checkpoints"]
    assert row["records"] > 0
    assert row["units"] > 0, "the only source with a real event stream reported zero"
    assert row["verdict"] == "THIN_BUT_REAL"


def test_terminal_steps_are_excluded_from_the_units_not_counted_as_failures(result):
    """The second version reported a 45% failure rate by counting `finish` steps as failures."""
    row = result["sources"]["controller_checkpoints"]
    assert row["terminal_steps_excluded"] > 0
    assert row["units"] < row["units"] + row["terminal_steps_excluded"]
    assert 0 <= row["failure_rate"] < 0.2, (
        "a failure rate this high means terminal steps leaked into the denominator again: "
        f"{row['failure_rate']}")


def test_the_event_stream_carries_a_natural_label_split(result):
    """A store with one outcome class cannot teach a policy where to stop."""
    row = result["sources"]["controller_checkpoints"]
    assert row["passed"] > 0, "no passing events: the stream has no positives"
    assert row["failure_rate"] > 0, "no failing events: the stream has no negatives"


def test_the_hand_seeded_store_is_reported_as_no_signal(result):
    row = result["sources"]["trajectory_store"]
    assert row["verdict"] == "NO_SIGNAL"
    assert row["verified_units"] == 0
    assert row["outcomes_seen"] == ["success"], row["outcomes_seen"]


def test_receipts_are_reported_as_no_signal_with_a_reason(result):
    row = result["sources"]["execution_receipts"]
    assert row["verdict"] == "NO_SIGNAL"
    assert row["units"] == 0
    assert row["why"], "a zero with no reason is indistinguishable from a bug"


# ---------------------------------------------------------------- 2. the conclusion it may not overstate


def test_the_repo_is_not_yet_ready_to_train(result):
    assert result["ready_to_train"] is False
    assert result["total_verified_units"] < result["minimum_units_to_try"]


def test_the_conclusion_says_fuel_is_thin_rather_than_absent(result):
    assert "THIN" in result["conclusion"]
    assert "NOTHING_TO_TRAIN_ON" not in result["conclusion"]


def test_the_gauge_carries_no_spend_and_no_model_call(result):
    assert result["incremental_spend_usd"] == 0
    assert result["model_calls"] == 0
    assert result["authority"].startswith("NONE__")


# ---------------------------------------------------------------- 3. the record


def test_the_committed_record_matches_a_fresh_measurement(result):
    if not record_path.is_file():
        pytest.skip("the record is not on this branch")
    recorded = json.loads(record_path.read_text(encoding="utf-8"))
    assert recorded["conclusion"] == result["conclusion"]
    assert recorded["total_units"] == result["total_units"]
    assert recorded["total_verified_units"] == result["total_verified_units"]
    assert set(recorded["sources"]) == set(result["sources"])
