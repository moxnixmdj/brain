import hashlib
import json
from pathlib import Path

from canonical.runtime.agency_finite_acceptance_closure_v1 import (
    CASE_SPECS,
    REQUIRED_DIMENSIONS,
    REQUIRED_METRICS,
    run_portfolio,
)

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "canonical/governance/AGENCY_FINITE_PORTFOLIO_FREEZE_20261007_V1.json"


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def test_agency_freeze_is_content_addressed_and_preexposure():
    doc = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert doc["status"].startswith("FROZEN_BEFORE_FIRST_QUALIFICATION_EXECUTION")
    assert doc["fixed_case_count"] == 2
    assert doc["frozen_cases"] == CASE_SPECS
    assert set(doc["required_dimensions"]) == REQUIRED_DIMENSIONS
    assert set(doc["required_metrics"]) == REQUIRED_METRICS
    assert all(doc["freeze_guards"].values())

    for binding in doc["source_bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file(), binding
        assert _git_blob(path) == binding["git_blob_sha"], binding


def test_two_case_agency_portfolio_is_complete_and_at_ceiling():
    out = run_portfolio()
    assert out["pass"] is True, out
    assert out["status"] == "PASS__FINITE_DECLARED_AGENCY_PORTFOLIO_AT_OBJECTIVE_CEILING"
    assert out["case_count"] == 2
    assert out["dimension_coverage_complete"] is True
    assert set(out["dimension_coverage"]) == REQUIRED_DIMENSIONS
    assert out["brain_success_fraction"] == 1.0
    assert out["metrics_at_objective_ceiling"] is True
    assert out["opus_case_execution_required"] is False
    assert all(row["success"] and row["verified"] for row in out["cases"])
    for row in out["cases"]:
        assert row["metrics"]["terminal_task_success"] == 1
        assert row["metrics"]["invalid_action_rate"] == 0
        assert row["metrics"]["unrecovered_failure_rate"] == 0
        assert row["metrics"]["duplicate_or_conflicting_work_rate"] == 0


def test_failure_case_is_load_bearing_replanning_not_a_benign_receipt():
    out = run_portfolio()
    row = next(x for x in out["cases"] if x["kind"] == "DELEGATION_STEP_UNAVAILABLE_WITNESS")
    assert row["evidence"]["case_class"] == "STEP_UNAVAILABLE"
    assert row["evidence"]["receipt_kind"] == "STEP_UNAVAILABLE"
    assert row["evidence"]["plan_changed_after_receipt"] is True
    assert row["evidence"]["completed_work_replayed"] is False
    assert row["evidence"]["verdict"]["pass"] is True
