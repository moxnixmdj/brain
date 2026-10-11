from __future__ import annotations

from pathlib import Path

from canonical.runtime.bound_capabilities.python_request_acceptance_model_v2 import (
    compile_plan,
    evaluate_plan,
)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "checks").mkdir()
    return tmp_path


def test_heldout_v2_complete_bound_request_authorizes_stop(tmp_path):
    root = _repo(tmp_path)
    (root / "app/service.py").write_text("def handle(x):\n    return x + 1\n", encoding="utf-8")
    request = (
        'File "app/service.py" must exist. '
        'Python file "app/service.py" must compile. '
        'File "app/service.py" must contain "def handle". '
        'File "app/service.py" must not contain "exec(".'
    )
    plan = compile_plan(request)
    assert plan["pass"] is True
    assert plan["predicate_count"] == 4
    assert plan["unbound_predicate_count"] == 0
    assert plan["bound_raw_obligation_count"] == plan["raw_obligation_count"]
    out = evaluate_plan(plan, repo_root=root, changed_paths=["app/service.py"])
    assert out["pass"] is True
    assert out["repair_stop_authorized_by_this_capability"] is True
    assert out["verified_pass_raw_obligation_count"] == out["raw_obligation_count"]


def test_heldout_v2_passing_tests_cannot_bind_freeform_semantics(tmp_path):
    root = _repo(tmp_path)
    (root / "app/parser.py").write_text("def parse(x):\n    return x\n", encoding="utf-8")
    request = (
        'Python file "app/parser.py" must parse. '
        'Make nested malformed records recover without losing valid siblings.'
    )
    plan = compile_plan(request)
    assert plan["bound_predicate_count"] == 1
    assert plan["unbound_predicate_count"] == 1
    out = evaluate_plan(
        plan,
        repo_root=root,
        existing_test_evidence={"status": "PASS", "tests_passed": 5000},
    )
    assert out["pass"] is False
    assert out["existing_test_evidence_is_request_semantics_authority"] is False
    assert out["repair_stop_authorized_by_this_capability"] is False


def test_heldout_v2_negative_literal_requirement_fails_closed(tmp_path):
    root = _repo(tmp_path)
    (root / "app/runner.py").write_text("def run(code):\n    return exec(code)\n", encoding="utf-8")
    plan = compile_plan('File "app/runner.py" must not contain "exec(".')
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is False
    assert out["bound_verified_fail_count"] == 1
    assert out["predicate_results"][0]["reason"] == "LITERAL_PRESENT"


def test_heldout_v2_exact_scope_is_enforced(tmp_path):
    root = _repo(tmp_path)
    (root / "app/core.py").write_text("VALUE=1\n", encoding="utf-8")
    (root / "app/config.py").write_text("VALUE=2\n", encoding="utf-8")
    plan = compile_plan('Only modify "app/core.py".')
    assert evaluate_plan(plan, repo_root=root, changed_paths=["app/core.py"])["pass"] is True
    bad = evaluate_plan(plan, repo_root=root, changed_paths=["app/core.py", "app/config.py"])
    assert bad["pass"] is False
    assert bad["predicate_results"][0]["reason"] == "CHANGED_PATH_OUTSIDE_SCOPE"


def test_heldout_v2_negative_scope_is_enforced(tmp_path):
    root = _repo(tmp_path)
    (root / "app/schema.py").write_text("VERSION=1\n", encoding="utf-8")
    plan = compile_plan('Must not modify "app/schema.py".')
    assert evaluate_plan(plan, repo_root=root, changed_paths=["app/other.py"])["pass"] is True
    assert evaluate_plan(plan, repo_root=root, changed_paths=["app/schema.py"])["pass"] is False


def test_heldout_v2_explicit_test_predicate_executes_only_its_own_obligation(tmp_path):
    root = _repo(tmp_path)
    (root / "checks/test_contract.py").write_text("assert sorted([3,1,2]) == [1,2,3]\n", encoding="utf-8")
    plan = compile_plan('Test file "checks/test_contract.py" must pass.')
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert out["predicate_results"][0]["reason"] == "TEST_PASS"
    assert out["existing_test_evidence_is_request_semantics_authority"] is False


def test_heldout_v2_unsupported_paraphrase_stays_unbound(tmp_path):
    root = _repo(tmp_path)
    (root / "app/cache.py").write_text("CACHE={}\n", encoding="utf-8")
    plan = compile_plan("Ensure app/cache.py remains syntactically valid and backward compatible.")
    assert plan["pass"] is True
    assert plan["unbound_predicate_count"] == 1
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is False
    assert out["predicate_results"][0]["status"] == "UNBOUND"


def test_heldout_v2_path_escape_is_fail_closed():
    plan = compile_plan('File "../escape.py" must exist.')
    assert plan["pass"] is False
    assert plan["status"] == "FAIL_CLOSED"
    assert any("PATH_INVALID" in x for x in plan["errors"])


def test_heldout_v2_quote_aware_mapping_preserves_all_raw_obligations(tmp_path):
    root = _repo(tmp_path)
    (root / "app/live.py").write_text("x=(2+3)\n", encoding="utf-8")
    request = 'File "app/gone.py" must not exist. Python file "app/live.py" must parse.'
    plan = compile_plan(request)
    assert plan["predicate_count"] == 2
    assert plan["raw_obligation_count"] > plan["predicate_count"]
    assert plan["bound_raw_obligation_count"] == plan["raw_obligation_count"]
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert {x["reason"] for x in out["predicate_results"]} == {"FILE_ABSENT", "PYTHON_PARSE_PASS"}


def test_heldout_v2_unbalanced_quote_fails_closed():
    plan = compile_plan('File "app/broken.py must exist.')
    assert plan["pass"] is False
    assert plan["status"] == "FAIL_CLOSED"
    assert any("UNBALANCED_QUOTED_SOURCE" in x for x in plan["errors"])
