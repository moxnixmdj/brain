"""The issue-to-PR verdict must not mistake a heuristic test slice for a suite."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator


def _repo(tmp_path: Path, *, tests: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    source = root / "src"
    (source / "pkg").mkdir(parents=True)
    (source / "pkg" / "__init__.py").write_text("")
    (source / "pkg" / "core.py").write_text("def helper(x):\n    return x + 1\n")
    for name, content in tests.items():
        path = source / "tests" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (root / "task.json").write_text(json.dumps({
        "issue_id": "guard", "title": "rename helper",
        "edits": [{"op": "rename_symbol", "module": "pkg/core.py",
                   "name": "helper", "new_name": "compute"}],
    }))
    return root


def _run(root: Path, python_executable: str = sys.executable) -> dict:
    return orchestrator.run({
        "task_path": "task.json", "source_root": "src", "worktree_path": "work",
        "output_path": "out/summary.json", "diff_path": "out/change.diff",
        "pr_intent_path": "out/pr.json", "python_executable": python_executable,
    }, root)


def _pytest(cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=30, check=False,
    )


SMOKE = "from pkg.core import helper\n\ndef test_smoke():\n    assert helper(2) == 3\n"
DYNAMIC = (
    "import importlib\n\ndef test_dynamic():\n"
    "    mod = importlib.import_module('pkg.core')\n"
    "    assert getattr(mod, 'helper')(2) == 3\n"
)


def test_an_omitted_dynamic_regression_cannot_produce_a_verified_pr(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={"test_smoke.py": SMOKE, "test_dynamic.py": DYNAMIC})
    assert _pytest(root / "src").returncode == 0  # the unmodified suite is actually green
    result = _run(root)
    selection = json.loads((root / "work/.orchestrate_testselect.json").read_text())
    assert "tests/test_smoke.py" in selection["selected_tests"]
    assert "tests/test_dynamic.py" not in selection["selected_tests"]  # real blind spot
    assert _pytest(root / "work").returncode == 1
    assert result["test_failed_count"] >= 1
    assert result["edits_verified"] is True
    assert result["verified"] is False
    assert "def helper" in (root / "src/pkg/core.py").read_text()  # source untouched


def test_the_full_green_suite_runs_even_when_some_tests_are_not_selected(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={
        "test_smoke.py": SMOKE,
        "test_unrelated.py": "def test_unrelated():\n    assert 2 + 2 == 4\n",
    })
    result = _run(root)
    assert result["test_selected_count"] == 1
    assert result["test_passed_count"] == 2  # the unselected test really ran
    assert result["local_test_report_passed"] is True
    assert result["verified"] is False
    assert result["verification_status"] == "UNRESOLVED__TEST_EVIDENCE_UNAUTHENTICATED"
    intent = json.loads((root / "out/pr.json").read_text())
    assert intent["body"]["tests"]["scope"] == "PYTEST_DEFAULT_DISCOVERY"
    assert intent["body"]["tests"]["selection_is_acceptance_authority"] is False


def test_no_tests_cannot_verify_a_pr(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={})
    result = _run(root)
    assert result["test_selected_count"] == 0
    assert result["test_passed_count"] == 0
    assert result["edits_verified"] is True
    assert result["verified"] is False
    intent = json.loads((root / "out/pr.json").read_text())
    assert intent["body"]["tests"]["pytest_rc"] == 5


def test_an_all_skipped_suite_cannot_verify_a_pr(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={"test_skipped.py": (
        "import pytest\nfrom pkg.core import helper\n\n"
        "@pytest.mark.skip(reason='not available')\n"
        "def test_skipped():\n    assert helper(2) == 3\n"
    )})
    result = _run(root)
    assert result["test_passed_count"] == 0
    assert result["verified"] is False


@pytest.mark.parametrize("printed", [
    "print('1 passed')",
    "print('999 passed')",
    "import sys; print('1 passed', file=sys.stderr)",
    "print('=== 1 passed in 0.01s ===')",
])
def test_an_all_skipped_suite_cannot_spoof_a_pass_count(tmp_path, monkeypatch, printed):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={"test_skipped.py": (
        "import pytest\nfrom pkg.core import helper\n" + printed + "\n\n"
        "@pytest.mark.skip(reason='not available')\n"
        "def test_skipped():\n    assert helper(2) == 3\n"
    )})
    (root / "src/pytest.ini").write_text("[pytest]\naddopts = -s\n")
    direct = _pytest(root / "src")
    assert direct.returncode == 0 and "passed" in direct.stdout + direct.stderr
    result = _run(root)
    assert result["test_passed_count"] == 0
    assert result["verified"] is False


def test_missing_pytest_cannot_verify_even_with_no_selected_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={})
    env = tmp_path / "isolated-python"
    venv.EnvBuilder(with_pip=False).create(env)
    isolated_python = str(env / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    result = _run(root, isolated_python)
    assert result["test_pytest"] == "UNAVAILABLE"
    assert result["test_selected_count"] == 0
    assert result["verified"] is False


def test_junit_failure_is_not_verified_when_pytest_exit_is_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    root = _repo(tmp_path, tests={
        "test_smoke.py": SMOKE,
        "test_bad.py": "def test_bad():\n    assert 1 == 2\n",
    })
    # A real project plugin can override the process status. JUnit still reports
    # the failed test; this is not a sandbox against a plugin that forges XML.
    (root / "src/force_exit_plugin.py").write_text(
        "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n"
    )
    (root / "src/pytest.ini").write_text("[pytest]\naddopts = -p force_exit_plugin\n")
    direct = _pytest(root / "src")
    assert direct.returncode == 0 and "1 failed" in direct.stdout
    result = _run(root)
    assert result["test_passed_count"] >= 1
    assert result["test_failed_count"] >= 1
    assert result["verified"] is False
