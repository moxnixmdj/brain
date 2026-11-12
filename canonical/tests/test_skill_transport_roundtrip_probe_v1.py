#!/usr/bin/env python3
"""A lesson learned once is permanent only in the sense that another machine still holds it.

These tests pin the transport round trip: teach on A, ship, land on B, and re-check on B. They
also pin the two ways the probe could lie -- by reporting a verdict with no numbers behind it,
and by writing into the live memory it is supposed to be measuring.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import skill_transport_roundtrip_probe_20261112 as P  # noqa: E402
from canonical.swe_kernel import skill_recheck_v1 as R  # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    _default_db_path,
    _seed_bundle_path,
)


def test_the_round_trip_survives_on_this_tree(tmp_path):
    """The claim under test: one lesson, taught once, re-checkable on a machine that never saw it."""
    assert P.main(["--keep", str(tmp_path / "work")]) == 0


def test_the_probe_reports_numbers_not_adjectives(tmp_path):
    result = P.measure(tmp_path / "work")
    assert result["schema"] == P.SCHEMA
    assert result["authority"] == "NONE"
    assert result["model_dependency_count"] == 0
    assert result["incremental_spend_usd"] == 0
    assert result["taught_on_a"] is True
    assert result["recheck_on_a"][R.PASS] == 1
    assert result["bundle_carries_the_demonstration"] is True
    assert result["imported_on_b"]["accepted"] == 1
    assert result["recheck_on_b"][R.PASS] == 1, "B holds the rule but lost the demonstration"
    assert result["recheckable_on_b_by_either"] == 1
    # and the CLI form of the same measurement is green
    assert P.main(["--json", "--keep", str(tmp_path / "cli")]) == 0


def test_the_shipped_memory_is_measured_from_the_file_a_new_machine_receives():
    """Not from this sandbox's store: from the bundle in version control."""
    bundle = _seed_bundle_path()
    assert bundle.is_file(), bundle
    report = R.recheck_bundle(bundle)
    assert report.get("error") is None, report
    assert report["total"] >= 1
    assert report["recheckable"] == report["total"], report["counts"]


def test_the_probe_does_not_write_into_the_memory_it_measures(tmp_path):
    """A probe that teaches the live store while measuring it is measuring itself."""
    live = pathlib.Path(_default_db_path())
    before_live = live.read_bytes() if live.is_file() else None
    bundle = pathlib.Path(_seed_bundle_path())
    before_bundle = bundle.read_bytes()

    assert P.main(["--keep", str(tmp_path / "work")]) == 0

    assert bundle.read_bytes() == before_bundle, "the probe edited the shipped bundle"
    after_live = live.read_bytes() if live.is_file() else None
    assert after_live == before_live, "the probe wrote into the live skill store"


@pytest.mark.parametrize("break_it,expected", [
    (lambda m: m.update(bundle_carries_the_demonstration=False), "not the text it was taught on"),
    (lambda m: m.update(recheck_on_b={R.PASS: 0, R.FAIL: 0, R.ABSENT: 1}),
     "did not survive the transport"),
    (lambda m: m.update(recheckable_on_b_by_either=0), "no way to contradict"),
    (lambda m: m.update(imported_on_b={"accepted": 0, "merged": 0, "refused": 1}),
     "B refused the lesson"),
    (lambda m: m.update(taught_on_a=False, teach_refusal="NON_GENERALIZABLE_SNIPPET"),
     "never learned on A"),
    (lambda m: m.update(shipped_bundle_recheckable=0, shipped_bundle_total=5),
     "cannot be shown wrong on a new machine"),
])
def test_every_way_this_could_be_false_is_named(break_it, expected, tmp_path):
    """The verdict must be reachable as BROKEN, or SURVIVED is decoration."""
    result = P.measure(tmp_path / "work")
    ok, failures = P.verdict(result)
    assert ok and not failures, failures

    break_it(result)
    ok, failures = P.verdict(result)
    assert ok is False
    assert any(expected in line for line in failures), failures


def test_an_unmeasurable_run_is_reported_as_unmeasurable_not_as_a_pass(monkeypatch):
    def boom(workdir):
        raise RuntimeError("store unreadable")

    monkeypatch.setattr(P, "measure", boom)
    assert P.main([]) == 2
