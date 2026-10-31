# PROJECT_BRAIN
"""Real coverage/pytest regressions for changed-file and test evidence."""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("coverage", reason="these regressions exercise real coverage.py")

from canonical.runtime.bound_capabilities import python_review_diff_coverage_gate as gate


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, subject: str = "subject.py", test_source: str | None = None):
    anchor = root / "anchor"
    _write(anchor, subject, "def compute():\n    return 1\n")
    _write(anchor, "tests/test_other.py", test_source or "def test_sanity():\n    assert len('other') == 5\n")
    diff = (f"--- a/{subject}\n+++ b/{subject}\n@@ -1,2 +1,2 @@\n"
            " def compute():\n-    return 1\n+    return 2\n")
    _write(root, "change.diff", diff)
    return anchor


def _run(root: Path):
    return gate.run({"anchor_path": "anchor", "diff_path": "change.diff",
                     "output_path": "out/coverage.json", "python_executable": sys.executable,
                     "timeout_s": 30}, root)


@pytest.mark.parametrize("subject", [
    "subject.py", "pkg/subject.py", "src/feature/subject.py", "tools/subject.py",
])
def test_unimported_changed_file_is_not_reported_as_full_coverage(tmp_path, monkeypatch, subject):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, subject)
    result = _run(tmp_path)
    artifact = json.loads((tmp_path / "out/coverage.json").read_text())
    assert result["verified"] is False
    assert result["gate"] != "PASS"
    assert artifact["diff_covered_ratio"] is None
    assert artifact["unmeasured_files"] == [subject]


def test_configured_coverage_omit_is_not_treated_as_full_coverage(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 2\n")
    _write(anchor, ".coveragerc", "[run]\nomit = subject.py\n")
    result = _run(tmp_path)
    artifact = json.loads((tmp_path / "out/coverage.json").read_text())
    assert result["verified"] is False
    assert artifact["diff_covered_ratio"] is None
    assert artifact["unmeasured_files"] == ["subject.py"]


def test_non_python_diff_does_not_claim_full_python_coverage(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path)
    _write(anchor, "settings.ini", "setting=old\n")
    _write(tmp_path, "change.diff", "--- a/settings.ini\n+++ b/settings.ini\n"
           "@@ -1 +1 @@\n-setting=old\n+setting=new\n")
    result = _run(tmp_path)
    artifact = json.loads((tmp_path / "out/coverage.json").read_text())
    assert result["verified"] is False
    assert result["gate"] != "PASS"
    assert artifact["diff_covered_ratio"] is None


@pytest.mark.parametrize("test_source", [
    "import pytest\n@pytest.mark.skip(reason='unavailable')\ndef test_case():\n    assert False\n",
    "import pytest\n@pytest.mark.xfail(reason='known')\ndef test_case():\n    assert False\n",
], ids=["all-skipped", "all-xfailed"])
def test_coverage_does_not_accept_a_suite_without_a_passing_case(tmp_path, monkeypatch, test_source):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, test_source=test_source)
    with pytest.raises(SystemExit, match="SUITE_RED"):
        _run(tmp_path)


def test_coverage_rejects_reported_failure_even_when_plugin_forces_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source=(
        "def test_sanity():\n    assert len('other') == 5\n"
        "def test_failure():\n    assert len('other') == 0\n"))
    _write(anchor, "force_exit_plugin.py", "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n")
    _write(anchor, "pytest.ini", "[pytest]\naddopts = -p force_exit_plugin --no-summary\n")
    with pytest.raises(SystemExit, match="SUITE_RED"):
        _run(tmp_path)


def test_a_measured_file_does_not_hide_a_second_unmeasured_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 2\n")
    _write(anchor, "unimported.py", "def forgotten():\n    return 1\n")
    with (tmp_path / "change.diff").open("a", encoding="utf-8") as diff:
        diff.write("--- a/unimported.py\n+++ b/unimported.py\n@@ -1,2 +1,2 @@\n"
                   " def forgotten():\n-    return 1\n+    return 2\n")
    result = _run(tmp_path)
    assert result["verified"] is False
    assert result["coverage_scope"] == "UNMEASURED_CHANGED_FILES"
    assert result["unmeasured_files"] == ["unimported.py"]
    assert result["diff_executable_lines"] > 0
    assert result["diff_covered_ratio"] is None


def test_comment_only_hunk_with_no_executable_lines_is_not_100_percent(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 1\n")
    _write(anchor, "subject.py", "# a\n# b\n# c\n# old\n# e\n# f\n# g\n\ndef compute():\n    return 1\n")
    _write(tmp_path, "change.diff", "--- a/subject.py\n+++ b/subject.py\n"
           "@@ -1,7 +1,7 @@\n # a\n # b\n # c\n-# old\n+# new\n # e\n # f\n # g\n")
    result = _run(tmp_path)
    assert result["verified"] is False
    assert result["coverage_scope"] == "NO_EXECUTABLE_LINES_IN_DIFF_HUNKS"
    assert result["unmeasured_files"] == []
    assert result["diff_executable_lines"] == 0
    assert result["diff_covered_ratio"] is None


@pytest.mark.parametrize("added,config", [
    ("\ndef untested():\n    return 2  # pragma: no cover\n", ""),
    ("\ndef untested():  # pragma: no cover\n    return 2\n", ""),
    ("\ndef untested(flag):\n    if flag:  # pragma: no cover\n        return 2\n    return 3\n", ""),
    ("\ndef untested():\n    raise NotImplementedError('untested')\n",
     "[report]\nexclude_lines =\n    pragma: no cover\n    raise NotImplementedError\n"),
], ids=["body-pragma", "function-pragma", "branch-pragma", "configured-exclusion"])
def test_excluded_changed_lines_are_not_counted_as_covered(tmp_path, monkeypatch, added, config):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 1\n")
    original = (anchor / "subject.py").read_text()
    diff = "".join(difflib.unified_diff(original.splitlines(keepends=True),
                                        (original + added).splitlines(keepends=True),
                                        fromfile="a/subject.py", tofile="b/subject.py"))
    _write(tmp_path, "change.diff", diff)
    if config:
        _write(anchor, ".coveragerc", config)
    result = _run(tmp_path)
    assert result["verified"] is False
    assert result["coverage_scope"] == "EXCLUDED_DIFF_LINES"
    assert result["unmeasured_lines"]
    assert result["diff_covered_ratio"] is None


def test_coverage_does_not_modify_an_inherited_coverage_data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    previous_data = tmp_path / "unrelated-coverage-data"
    previous_data.write_bytes(b"previous coverage data must not be touched")
    monkeypatch.setenv("COVERAGE_FILE", str(previous_data))
    _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 2\n")
    result = _run(tmp_path)
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["local_gate"] == "PASS"
    assert result["verified"] is False
    assert previous_data.read_bytes() == b"previous coverage data must not be touched"


def test_coverage_rejects_a_missing_junit_report(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = _project(tmp_path, test_source="from subject import compute\ndef test_compute():\n    assert compute() == 2\n")
    _write(anchor, "report_plugin.py", "from pathlib import Path\ndef pytest_unconfigure(config):\n"
           "    Path(config.option.xmlpath).unlink(missing_ok=True)\n")
    _write(anchor, "pytest.ini", "[pytest]\naddopts = -p report_plugin\n")
    with pytest.raises(SystemExit, match="SUITE_RED"):
        _run(tmp_path)
