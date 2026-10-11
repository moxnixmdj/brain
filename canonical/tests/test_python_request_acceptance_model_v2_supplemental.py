from __future__ import annotations

from pathlib import Path

from canonical.runtime.bound_capabilities.python_request_acceptance_model_v2 import (
    compile_plan,
    evaluate_plan,
)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "qa").mkdir()
    return tmp_path


def test_fresh_supplemental_freeform_semantics_stays_explicitly_unbound(tmp_path):
    root = _repo(tmp_path)
    plan = compile_plan("Make nested malformed records recover while preserving valid siblings.")
    assert plan["pass"] is True
    assert plan["unbound_predicate_count"] >= 1
    out = evaluate_plan(
        plan,
        repo_root=root,
        existing_test_evidence={"status": "PASS", "tests_passed": 10000},
    )
    assert out["pass"] is False
    assert out["repair_stop_authorized_by_this_capability"] is False
    assert out["existing_test_evidence_is_request_semantics_authority"] is False


def test_fresh_supplemental_scope_and_content_must_both_clear(tmp_path):
    root = _repo(tmp_path)
    (root / "src/core.py").write_text("READY=True\n", encoding="utf-8")
    plan = compile_plan(
        'Only modify "src/core.py". File "src/core.py" must contain "READY".'
    )
    assert plan["unbound_predicate_count"] == 0
    good = evaluate_plan(plan, repo_root=root, changed_paths=["src/core.py"])
    assert good["pass"] is True
    bad = evaluate_plan(plan, repo_root=root, changed_paths=["src/core.py", "src/extra.py"])
    assert bad["pass"] is False
    assert bad["repair_stop_authorized_by_this_capability"] is False


def test_fresh_supplemental_quote_aware_filename_maps_multiple_raw_obligations(tmp_path):
    root = _repo(tmp_path)
    (root / "src/widget.py").write_text("VALUE=7\n", encoding="utf-8")
    plan = compile_plan('File "src/widget.py" must exist.')
    assert plan["predicate_count"] == 1
    assert plan["raw_obligation_count"] >= 2
    assert plan["bound_raw_obligation_count"] == plan["raw_obligation_count"]
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert out["repair_stop_authorized_by_this_capability"] is True
