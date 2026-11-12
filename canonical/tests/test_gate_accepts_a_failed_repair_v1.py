"""Executed proof, in both directions, that the repair gate now reads the outcome.

The claim is narrow and must stay narrow: on a workspace whose only test no bounded mutation can
satisfy, every repair adapter answers `pass == False` and still returns `output_verified == True`.

Three things are pinned here, and each fails loudly if it stops being true:

  * the fixture is genuinely unsatisfiable, so this cannot quietly become a measurement of nothing;
  * the predicate these capabilities carried until 2026-11-12 would have accepted the failure —
    kept as `LEGACY_EXPECT` in the probe, never read back into the registry, because the reason for
    the repoint has to survive the repoint;
  * the live registry, and the **production** checker `grounded_action_v1._check_expect` that the
    runtime actually calls, reject the failure.

That last one matters: re-implementing `field_equals` inside a probe proves the probe's opinion, not
the system's behaviour. `test_the_production_expect_checker_rejects_failure_and_accepts_success`
exists so the claim is about the code that runs.
"""
from __future__ import annotations

import json
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
    """The registry must ask the question the adapter already answered."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    for capability_id in CASES:
        assert capability_id in registry, capability_id
        entry = registry[capability_id]
        expect = entry["action_template"]["expect"]
        assert expect == {"field": "pass", "type": "field_equals", "value": True}, capability_id
        assert "pass" in entry["result_fields"], capability_id


def test_every_adapter_ran():
    skipped = [r for r in _report()["records"] if not r["ran"]]
    assert not skipped, skipped


def test_the_honest_answer_is_no_repair_everywhere():
    """The adapters are not broken. They report failure correctly."""
    records = _report()["records"]
    assert records
    wrong = [r["capability_id"] for r in records if r["passed"] is not False]
    assert not wrong, wrong
    assert all(r["status"].startswith("OPEN__") for r in records)


def test_the_legacy_predicate_still_would_have_accepted_every_one_of_them():
    """This is the defect as it stood. It is kept as the reason for the repoint, not as policy."""
    rejected = [r["capability_id"] for r in _report()["records"] if not r["legacy_accepts"]]
    assert not rejected, rejected


def test_the_registry_predicate_rejects_every_executed_failed_repair():
    """This is the fix. If it ever stops being true the gate has regressed to reading transport."""
    accepted = [r["capability_id"] for r in _report()["records"] if r["registry_accepts"]]
    assert not accepted, accepted


def test_the_registered_predicate_matches_the_corrected_predicate():
    disagreements = [
        r["capability_id"] for r in _report()["records"]
        if r["registry_accepts"] != r["corrected_accepts"]
    ]
    assert not disagreements, disagreements


def test_the_production_expect_checker_rejects_failure_and_accepts_success():
    """The runtime calls `_check_expect`. This is the code that actually decides, not a restatement."""
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
    assert summary["legacy_accepts_the_failure"] == summary["ran"]
    assert summary["registry_rejects_the_failure"] == summary["ran"]
    assert summary["registry_reads_the_outcome"] == summary["ran"]
    assert summary["pass_declared_in_result_fields"] == summary["ran"]
