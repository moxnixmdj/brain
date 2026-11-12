"""Executed proof that the registered repairs gate accepts a repair that failed.

The claim is narrow and must stay narrow: on a workspace whose only test no bounded mutation can
satisfy, every repair adapter answers `pass == False` and still returns `output_verified == True`,
so the registry's `field_equals output_verified == true` accepts it.

These tests would fail if either half of that stopped being true — which is the point. They also
pin the fixture as genuinely unsatisfiable, so a future edit cannot quietly make the test passable
and turn this into a measurement of nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate_accepts_a_failed_repair_probe_20261112 import (  # noqa: E402
    CASES,
    FIXTURE,
    REGISTRY,
    apply_predicate,
    run,
)

import json  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_the_fixture_is_genuinely_unsatisfiable():
    """If this ever passes, the probe is measuring a repair and not a failure.

    Runs the fixture as a real test in its own process, with no module stand-ins: the guard is
    right that replacing `calc` in `sys.modules` would hide whatever the adapter actually sees.
    """
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="unsatisfiable_") as tmp:
        for name, body in FIXTURE.items():
            (Path(tmp) / name).write_text(body, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-c", "import test_calc; test_calc.test_square()"],
            cwd=tmp, capture_output=True, text=True, timeout=120,
        )
    assert completed.returncode != 0, "fixture test passed: the probe no longer tests failure"
    assert "AssertionError" in completed.stderr, completed.stderr[-400:]


def test_the_predicate_implementation_is_the_registrys_own_semantics():
    assert apply_predicate({"type": "field_equals", "field": "x", "value": True}, {"x": True})
    assert not apply_predicate({"type": "field_equals", "field": "x", "value": True}, {"x": False})
    assert not apply_predicate({"type": "field_equals", "field": "x", "value": True}, {})


def test_an_unsupported_expect_type_is_refused_rather_than_guessed():
    try:
        apply_predicate({"type": "field_starts_with", "field": "x", "value": "P"}, {"x": "P"})
    except ValueError:
        return
    raise AssertionError("an unknown predicate type was silently accepted")


def test_every_case_is_a_real_bound_capability_with_outcome_acceptance():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    for capability_id in CASES:
        assert capability_id in registry, capability_id
        entry = registry[capability_id]
        expect = entry["action_template"]["expect"]
        assert expect == {"field": "pass", "type": "field_equals", "value": True}
        assert "pass" in entry["result_fields"]


def test_every_adapter_ran():
    report = _report()
    skipped = [r for r in report["records"] if not r["ran"]]
    assert not skipped, skipped


def test_the_honest_answer_is_no_repair_everywhere():
    """The adapters are not broken. They report failure correctly."""
    records = _report()["records"]
    assert records
    wrong = [r["capability_id"] for r in records if r["passed"] is not False]
    assert not wrong, wrong
    assert all(r["status"].startswith("OPEN__") for r in records)


def test_the_registry_predicate_rejects_every_executed_failed_repair():
    records = _report()["records"]
    accepted = [r["capability_id"] for r in records if r["registry_accepts"]]
    assert not accepted, accepted


def test_the_registered_predicate_matches_the_corrected_predicate():
    records = _report()["records"]
    disagreements = [
        r["capability_id"] for r in records
        if r["registry_accepts"] != r["corrected_accepts"]
    ]
    assert not disagreements, disagreements


def test_the_production_expect_checker_rejects_failure_and_accepts_success():
    from canonical.runtime.grounded_action_v1 import _check_expect

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    for capability_id in CASES:
        expect = registry[capability_id]["action_template"]["expect"]
        ok, _ = _check_expect(expect, {
            "pass": False,
            "output_verified": True,
            "status": "OPEN__NO_VERIFIED_REPAIR",
        })
        assert not ok, capability_id
        ok, _ = _check_expect(expect, {"pass": True, "status": "PASS"})
        assert ok, capability_id


def test_the_registered_gate_rejects_all_eight_known_failure_paths():
    summary = _report()["summary"]
    assert summary["ran"] == 8
    assert summary["honest_answer_no_repair"] == summary["ran"]
    assert summary["registry_accepts_the_failure"] == 0
    assert summary["corrected_rejects_the_failure"] == summary["ran"]
    assert summary["pass_declared_in_result_fields"] == summary["ran"]
