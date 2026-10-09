from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import r2_finance_normalized_unless_direct_adequacy_v1 as d


def _case(value: bool = False):
    return {
        "schema": "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_CASE_V1",
        "source_id": "normalized-finance-case",
        "source_text": "Apply Rule A unless Exception B applies.",
        "exception_applies": value,
    }


def _goal(
    inp="canonical/tmp/finance_case.json",
    out="canonical/tmp/finance_result.json",
):
    return (
        "Using the normalized finance supervisory UNLESS case at "
        f"{inp}, select and independently verify the applicable branch and save it "
        f"to {out}."
    )


def _write_case(root: Path, value: bool = False):
    p = root / "canonical/tmp/finance_case.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_case(value)), encoding="utf-8")
    return p


def test_preflight_exact_side_effect_free_and_scope_bound(tmp_path: Path):
    _write_case(tmp_path, False)
    out = d.preflight({"task_id": "finance-1", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True, out
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert out["preflight_execution_authority"] is False
    assert "EXPLICIT_TYPED_EXCEPTION_TRUTH" in out["semantic_scope"]
    assert not (tmp_path / "canonical/tmp/finance_result.json").exists()


def test_false_exception_selects_ordinary_branch_and_independently_verifies(tmp_path: Path):
    _write_case(tmp_path, False)
    out = d.run({"task_id": "finance-1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "ORDINARY_BRANCH"
    assert out["semantic_acceptance_complete"] is True
    assert out["actual_goal_satisfaction_verified"] is True
    assert out["direct_adequacy_authority"] is True
    assert out["acceptance_receipt"]["producer_independent"] is True
    assert out["source_immutability_verified"] is True


def test_true_exception_selects_exception_branch(tmp_path: Path):
    _write_case(tmp_path, True)
    out = d.run({"task_id": "finance-2", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "EXCEPTION_BRANCH"
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_result.json").read_text(encoding="utf-8")
    )
    assert result["exception_applies"] is True
    assert result["selected_branch"] == "EXCEPTION_BRANCH"


def test_verifier_tamper_rolls_back(monkeypatch, tmp_path: Path):
    _write_case(tmp_path, False)
    outp = tmp_path / "canonical/tmp/finance_result.json"
    outp.write_text('{"old":true}\n', encoding="utf-8")
    original = outp.read_bytes()

    monkeypatch.setattr(
        d.verifier,
        "verify",
        lambda case, result: {
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["forced"],
        },
    )
    out = d.run({"task_id": "finance-3", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["rollback_complete"] is True
    assert outp.read_bytes() == original


def test_non_boolean_exception_fact_fails_closed(tmp_path: Path):
    p = _write_case(tmp_path, False)
    case = _case(False)
    case["exception_applies"] = "unknown"
    p.write_text(json.dumps(case), encoding="utf-8")
    out = d.preflight({"task_id": "finance-4", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_multiple_unless_operators_not_admitted(tmp_path: Path):
    p = _write_case(tmp_path, False)
    case = _case(False)
    case["source_text"] = "Apply A unless B unless C."
    p.write_text(json.dumps(case), encoding="utf-8")
    out = d.preflight({"task_id": "finance-5", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_nonmatching_goal_does_not_claim_scope(tmp_path: Path):
    out = d.preflight(
        {"task_id": "finance-6", "goal": "Analyze this finance case."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False
