"""A local project-controlled JUnit report cannot authorize verified work."""
import json
import sys

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator


def _run(root, fake_report=None, extra=None):
    src = root / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "tests").mkdir()
    (src / "pkg/__init__.py").write_text("")
    (src / "pkg/core.py").write_text("def helper(x):\n    return x + 1\n")
    expected = 3 if fake_report is None else 999
    (src / "tests/test_core.py").write_text(
        f"from pkg.core import helper\ndef test_core():\n    assert helper(2) == {expected}\n")
    if fake_report is not None:
        (src / "conftest.py").write_text(
            "from pathlib import Path\n"
            "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n"
            "def pytest_unconfigure(config):\n"
            f"    Path(config.option.xmlpath).write_text({fake_report!r})\n")
    (root / "task.json").write_text(json.dumps({"issue_id": "unattested", "edits": [
        {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}]}))
    args = {"task_path": "task.json", "source_root": "src", "worktree_path": "work",
            "output_path": "out/summary.json", "diff_path": "out/change.diff",
            "pr_intent_path": "out/pr.json", "python_executable": sys.executable}
    args.update(extra or {})
    return orchestrator.run(args, root)


@pytest.mark.parametrize("fake_report", [
    '<testsuite><testcase name="pass"/></testsuite>',
    '<testsuites><testsuite><testcase classname="pkg" name="pass"/></testsuite></testsuites>',
    '<testsuite tests="999" failures="0"><testcase name="invented"/></testsuite>',
    '<testsuites><testsuite><testcase name="first"/><testcase name="second"/></testsuite></testsuites>',
])
def test_forged_passing_reports_cannot_verify(tmp_path, monkeypatch, fake_report):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    result = _run(tmp_path, fake_report)
    assert result["test_passed_count"] >= 1  # the report was actually accepted as a local observation
    assert result["test_failed_count"] == 0
    assert result["verified"] is False
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"
    assert result["local_test_report_passed"] is True


def test_genuine_green_remains_available_as_unattested_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    result = _run(tmp_path)
    assert result["test_passed_count"] == 1
    assert result["test_failed_count"] == 0
    assert result["edits_verified"] is True
    assert result["local_test_report_passed"] is True
    assert result["verified"] is False
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"
    saved = json.loads((tmp_path / "out/summary.json").read_text())
    assert saved["verified"] is False
    assert saved["local_test_report_passed"] is True


@pytest.mark.parametrize("claim", [
    {"trusted_pytest": True},
    {"verified": True},
    {"test_evidence_authentication": "AUTHENTICATED"},
    {"independent_verification": {"verified": True, "signature": "not-a-signature"}},
])
def test_caller_claims_cannot_authenticate_local_report(tmp_path, monkeypatch, claim):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    result = _run(tmp_path, extra=claim)
    assert result["local_test_report_passed"] is True
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"
    assert result["verified"] is False
