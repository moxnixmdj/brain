"""A pre-merge test gate must not turn unexecuted/failing tests green.

These run real git and pytest on disposable projects. The XML is evidence of
pytest's report, not a security boundary against hostile tests or plugins.
"""
import json
import os
import subprocess
import sys

import pytest

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as gate

DIFF = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def compute():
-    return 1
+    return 2
"""


def _project(tmp_path, test_source, extra_files=None):
    anchor = tmp_path / "anchor"
    (anchor / "tests").mkdir(parents=True)
    (anchor / "app.py").write_text("def compute():\n    return 1\n")
    (anchor / "tests/test_app.py").write_text(test_source)
    for name, contents in (extra_files or {}).items():
        (anchor / name).write_text(contents)
    (tmp_path / "change.diff").write_text(DIFF)
    return anchor


def _run(tmp_path):
    return gate.run({"anchor_path": "anchor", "diff_path": "change.diff",
                     "output_path": "out/result.json", "python_executable": sys.executable,
                     "timeout_s": 30}, tmp_path)


@pytest.mark.parametrize("test_source", [
    "import pytest\n@pytest.mark.skip(reason='not available')\ndef test_case():\n    assert False\n",
    "import pytest\n@pytest.mark.xfail(reason='known')\ndef test_case():\n    assert False\n",
    "import pytest\npytest.skip('module unavailable', allow_module_level=True)\n",
    "import pytest\npytest.importorskip('brain_missing_optional_package_for_gate_test')\n",
], ids=["skipped-test", "expected-failure", "module-skip", "missing-optional-module"])
def test_all_skipped_or_xfailed_is_not_a_verified_patch(tmp_path, monkeypatch, test_source):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, test_source)
    result = _run(tmp_path)
    assert result["gate"] != "PASS", result
    assert result["verified"] is False
    assert result["complete"] is False
    artifact = json.loads((tmp_path / "out/result.json").read_text())
    assert artifact["tests_passed"] == 0


def test_pytest_exit_override_without_failure_summary_is_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, "from app import compute\n\n"
                              "def test_good():\n    assert compute() in (1, 2)\n\n"
                              "def test_bad():\n    assert compute() > 100\n", {
        "force_exit_plugin.py": "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n",
        "pytest.ini": "[pytest]\naddopts = -p force_exit_plugin --no-summary\n",
    })
    # The actual plugin makes pytest return zero and suppresses FAILED lines.
    check = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=anchor,
                           env=dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"),
                           capture_output=True, text=True, timeout=30)
    assert check.returncode == 0
    assert "FAILED " not in check.stdout
    result = _run(tmp_path)
    assert result["gate"] != "PASS", result
    assert result["verified"] is False
    assert result["tests_failed"] >= 1


def test_a_passing_test_and_a_skipped_test_are_not_mistaken_for_all_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "import pytest\nfrom app import compute\n"
             "def test_good():\n    assert compute() == 2\n\n"
             "@pytest.mark.skip(reason='unavailable')\ndef test_skipped():\n    assert compute() == 2\n")
    result = _run(tmp_path)
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE", result
    assert result["local_gate"] == "PASS"
    assert result["verified"] is False
    artifact = json.loads((tmp_path / "out/result.json").read_text())
    assert artifact["tests_passed"] == 1
    assert artifact["tests_skipped"] == 1


@pytest.mark.parametrize("action", [
    "path.unlink(missing_ok=True)",
    "path.write_text('<not-xml')",
    "path.write_text('<unrelated><testcase name=\"fabricated\"/></unrelated>')",
    "path.write_text('<testsuites><testsuite/></testsuites>')",
], ids=["missing", "malformed", "wrong-root", "no-cases"])
def test_missing_or_unusable_junit_report_cannot_verify(tmp_path, monkeypatch, action):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "from app import compute\ndef test_good():\n    assert compute() == 2\n", {
        "report_plugin.py": ("from pathlib import Path\n"
                             "def pytest_unconfigure(config):\n"
                             "    path = Path(config.option.xmlpath)\n"
                             f"    {action}\n"),
        "pytest.ini": "[pytest]\naddopts = -p report_plugin\n",
    })
    result = _run(tmp_path)
    assert result["gate"] == "FAIL"
    assert result["verified"] is False
    assert result["complete"] is False
    assert result["tests_passed"] == 0


def test_reused_junit_parser_preserves_duplicate_case_failures(tmp_path):
    from canonical.runtime.bound_capabilities.quality_flake_detect_v1 import _junit_cases, _junit_outcomes
    report = tmp_path / "duplicates.xml"
    report.write_text('<testsuite><testcase classname="x" name="test_a"><failure/></testcase>'
                      '<testcase classname="x" name="test_a"/></testsuite>')
    assert _junit_cases(report) == [("x::test_a", "failed"), ("x::test_a", "passed")]
    assert _junit_outcomes(report) == {"x::test_a": "failed"}


def test_duplicate_case_failure_is_not_overwritten_by_later_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "from pathlib import Path\n"
             "def test_changing():\n"
             "    marker = Path('first-run.marker')\n"
             "    if not marker.exists():\n"
             "        marker.write_text('seen')\n"
             "        assert False, 'first collection fails'\n"
             "    assert marker.read_text() == 'seen'\n", {
        "force_exit_plugin.py": "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n",
        "pytest.ini": ("[pytest]\naddopts = -p force_exit_plugin --no-summary --keep-duplicates "
                       "tests/test_app.py tests/test_app.py\n"),
    })
    result = _run(tmp_path)
    assert result["pytest_returncode"] == 0
    assert result["tests_passed"] == 1
    assert result["tests_failed"] == 1
    assert result["gate"] == "FAIL"
    assert result["verified"] is False
