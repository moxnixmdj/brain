"""The oracle is synthesised, and it is only admissible if it is both separating and stable.

Pinned: the receipt. Live: the two-sided soundness property that must hold on any machine -- a projection
that fails stability may not be admitted, and an action that cannot be separated must be reported rather
than certified.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import distinguishing_projection_v1 as synth  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "DISTINGUISHING_PROJECTION_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_absence_is_a_value_in_every_projection(tmp_path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello")
    before = {feature: synth.project(tmp_path, feature) for feature in synth.FEATURES}
    (tmp_path / "b.txt").write_bytes(b"hello")
    after = {feature: synth.project(tmp_path, feature) for feature in synth.FEATURES}
    for feature in synth.FEATURES:
        assert before[feature] != after[feature], feature


def test_the_cover_is_minimal_and_refuses_when_no_cover_exists() -> None:
    separates = {"name": {"m1"}, "content": {"m1", "m2"}, "size": {"m2"}}
    assert synth._cover(separates, {"m1", "m2"}) == ["content"]
    assert synth._cover(separates, {"m1"}) == ["content"] or synth._cover(separates, {"m1"}) == ["name"]
    assert synth._cover({"name": {"m1"}}, {"m1", "m2"}) is None


def test_the_receipt_numbers(report: dict) -> None:
    assert report["tasks"] == 9
    assert report["mutants"] == 34
    assert report["cover_size_histogram"] == {"1": 9}
    assert len(report["content_alone_suffices_for"]) == 9
    assert report["features_rejected_by_stability"]["mtime"] == 8


def test_every_wrong_action_in_the_space_is_separated(report: dict) -> None:
    for task in report["per_task"]:
        assert task["every_mutant_separable"] is True, task["task"]
        assert task["inseparable_mutants"] == []
        assert task["minimal_cover"] == ["content"]
        assert "mtime" not in task["minimal_cover"]


def test_stability_is_tested_against_a_delay_not_a_clock_tick(report: dict) -> None:
    assert "never instantaneous" in report["soundness_tests"]["stability"]
    assert "%.2f" % synth.STABILITY_DELAY_SECONDS in report["soundness_tests"]["stability"]
    # the timestamp is admitted by separation and thrown out by stability: the two tests disagree,
    # which is exactly why one test is not enough
    assert report["features_rejected_by_stability"], "no feature was rejected: stability did nothing"


def test_the_limit_of_the_method_is_stated(report: dict) -> None:
    assert "hypothesis space" in report["limit"]
    assert "no claim" in report["limit"]


def test_a_live_synthesis_separates_every_wrong_action_or_says_it_cannot() -> None:
    live = synth.synthesize()
    assert live["mutants"] > 0
    for task in live["per_task"]:
        assert task["minimal_cover"] is not None
        assert "mtime" not in (task["minimal_cover"] or [])
        assert "content" in (task["minimal_cover"] or [])
