from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import r2_finance_explicit_definition_unless_direct_adequacy_v1 as d
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256


def _context_bool(value: bool):
    ctx = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"breach": {"type": "BOOL", "value": value}},
    }
    return ctx, typed_context_sha256(ctx)


def _context_decimal(value: str):
    ctx = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exposure": {"type": "DECIMAL_STRING", "value": value}},
    }
    return ctx, typed_context_sha256(ctx)


def _case_bool(value: bool = True):
    ctx, digest = _context_bool(value)
    return {
        "schema": "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_CASE_V1",
        "source_id": "finance-defined-case",
        "source_text": (
            "Exception B means breach is true. "
            "Apply Rule A unless Exception B."
        ),
        "typed_context": ctx,
        "typed_context_sha256": digest,
    }


def _case_decimal(value: str = "150"):
    ctx, digest = _context_decimal(value)
    return {
        "schema": "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_CASE_V1",
        "source_id": "finance-defined-decimal",
        "source_text": (
            "Threshold Breach means exposure is at least 100. "
            "Apply escalation unless Threshold Breach."
        ),
        "typed_context": ctx,
        "typed_context_sha256": digest,
    }


def _goal(
    inp="canonical/tmp/finance_defined_case.json",
    out="canonical/tmp/finance_defined_result.json",
):
    return (
        "Using the explicit-definition typed finance UNLESS case at "
        f"{inp}, select and independently verify the applicable branch and save it "
        f"to {out}."
    )


def _write(root: Path, case):
    p = root / "canonical/tmp/finance_defined_case.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(case), encoding="utf-8")
    return p


def test_bool_true_resolves_definition_and_selects_exception(tmp_path: Path):
    _write(tmp_path, _case_bool(True))
    out = d.run({"task_id": "finance-def-1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "EXCEPTION_BRANCH"
    assert out["definition_term"] == "Exception B"
    assert out["condition_holds"] is True
    assert out["acceptance_receipt"]["producer_independent"] is True
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_defined_result.json").read_text()
    )
    assert result["selected_text"] == "Exception B"


def test_bool_false_resolves_definition_and_selects_ordinary(tmp_path: Path):
    _write(tmp_path, _case_bool(False))
    out = d.run({"task_id": "finance-def-2", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "ORDINARY_BRANCH"
    result = json.loads(
        (tmp_path / "canonical/tmp/finance_defined_result.json").read_text()
    )
    assert result["selected_text"] == "Apply Rule A"


def test_decimal_definition_is_evaluated_against_typed_context(tmp_path: Path):
    _write(tmp_path, _case_decimal("150"))
    out = d.run({"task_id": "finance-def-3", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["field_name"] == "exposure"
    assert out["operator"] == "DECIMAL_GE"
    assert out["literal"] == "100"
    assert out["condition_holds"] is True
    assert out["selected_branch"] == "EXCEPTION_BRANCH"


def test_reference_term_mismatch_fails_closed(tmp_path: Path):
    case = _case_bool(True)
    case["source_text"] = (
        "Exception B means breach is true. "
        "Apply Rule A unless Exception C."
    )
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-def-4", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_free_text_definition_outside_typed_grammar_fails_closed(tmp_path: Path):
    case = _case_bool(True)
    case["source_text"] = (
        "Exception B means material supervisory concern exists. "
        "Apply Rule A unless Exception B."
    )
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-def-5", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_more_than_two_sentences_fails_closed(tmp_path: Path):
    case = _case_bool(True)
    case["source_text"] = (
        "Exception B means breach is true. "
        "Background sentence. "
        "Apply Rule A unless Exception B."
    )
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-def-6", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_typed_context_digest_mismatch_fails_closed(tmp_path: Path):
    case = _case_bool(True)
    case["typed_context_sha256"] = "0" * 64
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-def-7", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_preflight_is_side_effect_free(tmp_path: Path):
    _write(tmp_path, _case_bool(True))
    out = d.preflight({"task_id": "finance-def-8", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert out["preflight_execution_authority"] is False
    assert not (tmp_path / "canonical/tmp/finance_defined_result.json").exists()


def test_verifier_failure_rolls_back_existing_output(monkeypatch, tmp_path: Path):
    _write(tmp_path, _case_bool(True))
    outp = tmp_path / "canonical/tmp/finance_defined_result.json"
    outp.write_text('{"old":true}\n', encoding="utf-8")
    original = outp.read_bytes()

    original_verify = d.verifier.verify
    calls = {"n": 0}

    def fail_after_preflight(case, result):
        calls["n"] += 1
        if calls["n"] == 1:
            return original_verify(case, result)
        return {
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["forced"],
        }

    monkeypatch.setattr(d.verifier, "verify", fail_after_preflight)
    out = d.run({"task_id": "finance-def-9", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["rollback_complete"] is True
    assert outp.read_bytes() == original


def test_conflicting_definition_fails_closed(tmp_path: Path):
    case = _case_bool(True)
    case["source_text"] = (
        "Exception B means breach is true. "
        "Exception B means breach is false. "
        "Apply Rule A unless Exception B."
    )
    _write(tmp_path, case)
    out = d.preflight({"task_id": "finance-def-10", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_nonmatching_goal_claims_no_scope(tmp_path: Path):
    out = d.preflight(
        {"task_id": "finance-def-11", "goal": "Analyze this finance definition."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False
