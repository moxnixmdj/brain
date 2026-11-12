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

Added 2026-11-12 (positive control): everything above asks the gate to REJECT, and a gate that
rejects *everything* passes all of it. The production-checker test feeds a hand-written
`{"pass": True}` dict, which shows the evaluator works on a payload nobody produced. The tests below
close that gap by executing real adapters on a defect whose repair is inside the mutation grammar
and requiring the live predicate to accept the verified result: 5/5 solvers, 0 real repairs
rejected. They also pin the two acceptance controllers, which correctly fail closed on that fixture
and which the legacy transport predicate accepted — a positively measured false-accept, not just an
argument. Without this direction, "we narrowed the gate" and "we disabled repair" are
indistinguishable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate_accepts_a_failed_repair_probe_20261112 import (  # noqa: E402
    ACCEPTANCE_CONTROLLERS,
    CASES,
    FIXTURE,
    REGISTRY,
    REPAIR_SOLVERS,
    REPAIRABLE_FIXTURE,
    apply_predicate,
    run,
    run_positive_control,
)

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def _positive() -> dict:
    if "p" not in _CACHE:
        _CACHE["p"] = run_positive_control()
    return _CACHE["p"]


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


# ------------------------------------------------------------------ positive control (other direction)

def test_the_repairable_fixture_really_is_repairable_and_really_is_broken():
    """If `x + x` -> `x * x` were unreachable, the positive control would prove nothing.

    Checked by executing the repaired and the unrepaired source directly, with no adapter and no
    predicate involved, so this cannot be satisfied by a bug in either.
    """
    import subprocess
    import tempfile

    repaired = REPAIRABLE_FIXTURE["calc.py"].replace("x + x", "x * x")
    assert repaired != REPAIRABLE_FIXTURE["calc.py"]
    probe = "import test_calc; test_calc.test_square()"
    with tempfile.TemporaryDirectory(prefix="repairable_") as tmp:
        (Path(tmp) / "test_calc.py").write_text(REPAIRABLE_FIXTURE["test_calc.py"], encoding="utf-8")
        (Path(tmp) / "calc.py").write_text(repaired, encoding="utf-8")
        good = subprocess.run([sys.executable, "-c", probe], cwd=tmp,
                              capture_output=True, text=True, timeout=120)
        (Path(tmp) / "calc.py").write_text(REPAIRABLE_FIXTURE["calc.py"], encoding="utf-8")
        bad = subprocess.run([sys.executable, "-c", probe], cwd=tmp,
                             capture_output=True, text=True, timeout=120)
    assert good.returncode == 0, good.stderr[-400:]
    assert bad.returncode != 0, "the starting fixture already passes: there is nothing to repair"


def test_every_repair_solver_finds_and_verifies_the_reachable_repair():
    records = _positive()["records"]
    assert len(records) == len(REPAIR_SOLVERS)
    not_run = [r["capability_id"] for r in records if not r["ran"]]
    assert not not_run, not_run
    missed = [(r["capability_id"], r.get("status")) for r in records if r["passed"] is not True]
    assert not missed, missed


def test_the_live_gate_accepts_every_real_repair_and_rejects_none():
    """The direction that separates a corrected gate from a disabled one."""
    summary = _positive()["summary"]
    assert summary["ran"] == len(REPAIR_SOLVERS)
    assert summary["found_and_verified_repair"] == summary["ran"]
    assert summary["registry_accepts_the_repair"] == summary["ran"]
    assert summary["registry_rejects_a_real_repair"] == 0


def test_the_production_checker_accepts_the_real_adapter_result_not_just_a_hand_written_dict():
    """Same claim through the code the runtime calls, on payloads adapters actually produced."""
    from canonical.runtime.grounded_action_v1 import _check_expect

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    import tempfile

    from gate_accepts_a_failed_repair_probe_20261112 import _load, _materialise

    for record in _positive()["records"]:
        cid = record["capability_id"]
        module_name, args = CASES[cid]
        root = _materialise(REPAIRABLE_FIXTURE)
        try:
            result = _load(module_name).run(dict(args), str(root))
        finally:
            import shutil

            shutil.rmtree(root, ignore_errors=True)
        assert result.get("pass") is True, cid
        ok, _ = _check_expect(registry[cid]["action_template"]["expect"], result)
        assert ok, cid


def test_the_acceptance_controllers_fail_closed_and_the_legacy_gate_would_have_accepted_them():
    """A patch exists, but no measurement receipt / request contract was supplied.

    Refusing is correct. The legacy transport predicate accepted both, so this is a measured
    false-accept that the repoint removed, on the success-side fixture rather than by argument.
    """
    report = _positive()
    records = report["controller_records"]
    assert len(records) == len(ACCEPTANCE_CONTROLLERS)
    assert all(r["ran"] for r in records), [r["capability_id"] for r in records if not r["ran"]]
    for record in records:
        assert record["passed"] is False, record["capability_id"]
        assert record["output_verified"] is True, record["capability_id"]
        assert record["registry_accepts"] is False, record["capability_id"]
        assert record["legacy_accepts"] is True, record["capability_id"]
    summary = report["summary"]
    assert summary["controllers_fail_closed"] == len(ACCEPTANCE_CONTROLLERS)
    assert summary["controllers_the_live_gate_rejects"] == len(ACCEPTANCE_CONTROLLERS)
    assert summary["controllers_the_legacy_gate_accepted"] == len(ACCEPTANCE_CONTROLLERS)


def test_both_directions_hold_in_one_report():
    """The conjunction is the claim: false on failure AND true on a verified repair."""
    report = _report()
    assert report["summary"]["registry_rejects_the_failure"] == report["summary"]["ran"]
    positive = report["positive_control"]
    assert positive["registry_accepts_the_repair"] == positive["ran"]
    assert positive["registry_rejects_a_real_repair"] == 0
