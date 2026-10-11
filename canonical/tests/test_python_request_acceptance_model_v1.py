from __future__ import annotations

from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities.python_request_acceptance_model_v1 import (
    RequestAcceptanceError,
    compile_plan,
    evaluate_plan,
)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


def test_heldout_complete_bound_request_can_authorize_stop(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/out.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    request = (
        'File "pkg/out.py" must exist. '
        'Python file "pkg/out.py" must parse. '
        'File "pkg/out.py" must contain "def add". '
        'File "pkg/out.py" must not contain "eval(".'
    )
    plan = compile_plan(request)
    assert plan["unbound_predicate_count"] == 0
    out = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/out.py"])
    assert out["pass"] is True
    assert out["repair_stop_authorized_by_this_capability"] is True
    assert out["bound_verified_pass_count"] == 4


def test_heldout_existing_tests_cannot_erase_unbound_request_semantics(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/parser.py").write_text("def parse(x):\n    return x\n", encoding="utf-8")
    request = (
        'Python file "pkg/parser.py" must parse. '
        'Make the parser robust to malformed nested inputs.'
    )
    plan = compile_plan(request)
    assert plan["bound_predicate_count"] == 1
    assert plan["unbound_predicate_count"] == 1
    out = evaluate_plan(
        plan,
        repo_root=root,
        changed_paths=["pkg/parser.py"],
        existing_test_evidence={"status": "PASS", "tests_passed": 999},
    )
    assert out["pass"] is False
    assert out["existing_test_evidence_is_request_semantics_authority"] is False
    assert out["repair_stop_authorized_by_this_capability"] is False
    assert out["unbound_predicate_count"] == 1


def test_heldout_negative_requirement_fails_when_forbidden_literal_survives(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/safe.py").write_text("def f(x):\n    return eval(x)\n", encoding="utf-8")
    plan = compile_plan('File "pkg/safe.py" must not contain "eval(".')
    out = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/safe.py"])
    assert out["pass"] is False
    assert out["bound_verified_fail_count"] == 1
    assert out["repair_stop_authorized_by_this_capability"] is False


def test_heldout_scope_predicate_is_executable(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/a.py").write_text("x=1\n", encoding="utf-8")
    (root / "pkg/b.py").write_text("x=2\n", encoding="utf-8")
    plan = compile_plan('Only modify "pkg/a.py".')
    good = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/a.py"])
    bad = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/a.py", "pkg/b.py"])
    assert good["pass"] is True
    assert bad["pass"] is False
    assert bad["predicate_results"][0]["reason"] == "CHANGED_PATH_OUTSIDE_SCOPE"


def test_heldout_do_not_modify_is_negative_scope_requirement(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/locked.py").write_text("LOCKED=True\n", encoding="utf-8")
    plan = compile_plan('Do not modify "pkg/locked.py".')
    assert plan["acceptance_predicates"][0]["predicate_class"] == "NEGATIVE_REQUIREMENT"
    good = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/other.py"])
    bad = evaluate_plan(plan, repo_root=root, changed_paths=["pkg/locked.py"])
    assert good["pass"] is True
    assert bad["pass"] is False


def test_heldout_explicit_test_predicate_is_independent_and_not_global_semantics(tmp_path):
    root = _repo(tmp_path)
    test = root / "tests/test_smoke.py"
    test.write_text("assert 2 + 2 == 4\n", encoding="utf-8")
    plan = compile_plan('Test file "tests/test_smoke.py" must pass.')
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert out["predicate_results"][0]["reason"] == "TEST_PASS"
    assert out["existing_test_evidence_is_request_semantics_authority"] is False


def test_heldout_unsupported_paraphrase_remains_unbound_instead_of_guessing(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/x.py").write_text("x=1\n", encoding="utf-8")
    plan = compile_plan('Please ensure pkg/x.py is present and valid Python.')
    assert plan["unbound_predicate_count"] == 1
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is False
    assert out["predicate_results"][0]["status"] == "UNBOUND"


def test_heldout_path_traversal_fails_closed():
    with pytest.raises(RequestAcceptanceError):
        compile_plan('File "../outside.py" must exist.')


def test_heldout_file_absence_and_parse_are_distinct_predicates(tmp_path):
    root = _repo(tmp_path)
    (root / "pkg/live.py").write_text("x = (1 + 2)\n", encoding="utf-8")
    request = 'File "pkg/dead.py" must not exist. Python file "pkg/live.py" must parse.'
    plan = compile_plan(request)
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert len(out["predicate_results"]) == 2
    assert {x["reason"] for x in out["predicate_results"]} == {"FILE_ABSENT", "PYTHON_PARSE_PASS"}
