from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import r2_finance_normalized_if_direct_adequacy_v1 as d


def _case(value: bool = True, *, text: str = "If Condition A holds, Apply Rule B."):
    return {
        "schema": "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_CASE_V1",
        "source_id": "normalized-finance-if-case",
        "source_text": text,
        "antecedent_holds": value,
    }


def _goal(inp="canonical/tmp/finance_if_case.json", out="canonical/tmp/finance_if_result.json"):
    return (
        "Using the normalized finance supervisory IF case at "
        f"{inp}, select and independently verify the applicable branch and save it "
        f"to {out}."
    )


def _write(root: Path, case):
    p = root / "canonical/tmp/finance_if_case.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(case), encoding="utf-8")
    return p


def test_prefix_if_true_selects_consequent_and_independently_verifies(tmp_path: Path):
    _write(tmp_path, _case(True))
    out = d.run({"task_id": "finance-if-1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "CONSEQUENT_BRANCH"
    assert out["acceptance_receipt"]["producer_independent"] is True
    assert out["direct_adequacy_authority"] is True
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_if_result.json").read_text(encoding="utf-8")
    )
    assert result["selected_text"] == "Apply Rule B"
    assert result["antecedent_holds"] is True


def test_prefix_if_false_selects_condition_not_met(tmp_path: Path):
    _write(tmp_path, _case(False))
    out = d.run({"task_id": "finance-if-2", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "CONDITION_NOT_MET"
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_if_result.json").read_text(encoding="utf-8")
    )
    assert result["selected_text"] == ""
    assert result["selected_span"] is None


def test_suffix_if_shape_is_admitted(tmp_path: Path):
    _write(tmp_path, _case(True, text="Apply Rule B if Condition A holds."))
    out = d.run({"task_id": "finance-if-3", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_if_result.json").read_text(encoding="utf-8")
    )
    assert result["selected_text"] == "Apply Rule B"


def test_preflight_is_side_effect_free(tmp_path: Path):
    _write(tmp_path, _case(True))
    out = d.preflight({"task_id": "finance-if-4", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert out["preflight_execution_authority"] is False
    assert "EXPLICIT_TYPED_ANTECEDENT_TRUTH" in out["semantic_scope"]
    assert not (tmp_path / "canonical/tmp/finance_if_result.json").exists()


def test_non_boolean_antecedent_fails_closed(tmp_path: Path):
    case = _case(True)
    case["antecedent_holds"] = "unknown"
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-if-5", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_multiple_if_operators_are_rejected(tmp_path: Path):
    _write(tmp_path, _case(True, text="If A, apply B if C."))
    out = d.preflight({"task_id": "finance-if-6", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_unless_is_not_misclassified_as_if(tmp_path: Path):
    _write(tmp_path, _case(True, text="Apply Rule B unless Exception C."))
    out = d.preflight({"task_id": "finance-if-7", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_verifier_tamper_rolls_back(monkeypatch, tmp_path: Path):
    _write(tmp_path, _case(True))
    outp = tmp_path / "canonical/tmp/finance_if_result.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text('{"old":true}\n', encoding="utf-8")
    original = outp.read_bytes()

    original_verify = d.verifier.verify
    calls = {"count": 0}

    def fail_after_preflight(case, result):
        calls["count"] += 1
        if calls["count"] == 1:
            return original_verify(case, result)
        return {
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["forced"],
        }

    monkeypatch.setattr(d.verifier, "verify", fail_after_preflight)
    out = d.run({"task_id": "finance-if-8", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["rollback_complete"] is True
    assert outp.read_bytes() == original


def test_nonmatching_goal_does_not_claim_scope(tmp_path: Path):
    out = d.preflight(
        {"task_id": "finance-if-9", "goal": "Analyze this finance case."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False
