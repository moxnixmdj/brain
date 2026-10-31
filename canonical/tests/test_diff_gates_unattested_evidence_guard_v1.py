"""Local reports cannot authorize diff-gate PASS without authenticated evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full
from canonical.runtime.bound_capabilities import python_review_diff_coverage_gate as coverage
from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as mutation


@pytest.mark.parametrize("module", [full, coverage, mutation], ids=["full", "coverage", "mutation"])
@pytest.mark.parametrize("variant", [0, 1, 2, 3])
def test_forged_reports_are_only_unattested_local_observations(tmp_path, monkeypatch, module, variant):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    if module is coverage:
        pytest.importorskip("coverage")
    anchor = tmp_path / "anchor"
    (anchor / "tests").mkdir(parents=True)
    (anchor / "subject.py").write_text("VALUE = 1\n")
    (anchor / "tests/test_subject.py").write_text(
        "from subject import VALUE\ndef test_actual():\n    assert VALUE == 999\n")
    # The plugin fabricates a passing base report and a failure for the numeric
    # mutant, even though the real test fails in both worlds.
    (anchor / "conftest.py").write_text(
        "from pathlib import Path\n"
        "def is_mutant():\n    return 'VALUE = 3' in Path('subject.py').read_text()\n"
        "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 1 if is_mutant() else 0\n"
        "def pytest_unconfigure(config):\n"
        f"    name = 'fabricated_{variant}'\n"
        "    failure = '<failure>invented</failure>' if is_mutant() else ''\n"
        "    Path(config.option.xmlpath).write_text("
        "'<testsuite><testcase name=\"' + name + '\">' + failure + '</testcase></testsuite>')\n")
    (tmp_path / "change.diff").write_text("--- a/subject.py\n+++ b/subject.py\n"
                                          "@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n")
    result = module.run({"anchor_path": "anchor", "diff_path": "change.diff",
                         "output_path": "out/result.json", "python_executable": sys.executable,
                         "timeout_s": 30, "max_mutants": 1}, tmp_path)
    artifact = json.loads((tmp_path / "out/result.json").read_text())
    assert result["local_gate"] == "PASS"  # the forgery reached the old green decision
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["verified"] is False
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"
    assert artifact["gate"] == result["gate"]
    assert artifact["local_gate"] == "PASS"


@pytest.mark.parametrize("module", [full, coverage, mutation], ids=["full", "coverage", "mutation"])
def test_genuine_green_remains_a_local_diagnostic_not_verified(tmp_path, monkeypatch, module):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    if module is coverage:
        pytest.importorskip("coverage")
    anchor = tmp_path / "anchor"
    (anchor / "tests").mkdir(parents=True)
    (anchor / "subject.py").write_text("VALUE = 1\n")
    (anchor / "tests/test_subject.py").write_text(
        "from subject import VALUE\ndef test_actual():\n    assert VALUE == 2\n")
    (tmp_path / "change.diff").write_text("--- a/subject.py\n+++ b/subject.py\n"
                                          "@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n")
    result = module.run({"anchor_path": "anchor", "diff_path": "change.diff",
                         "output_path": "out/result.json", "python_executable": sys.executable,
                         "timeout_s": 30, "max_mutants": 1}, tmp_path)
    assert result["local_gate"] == "PASS"
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["verified"] is False
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"
    assert result["output_verified"] is True
    registry = json.loads((Path(__file__).resolve().parents[2] /
                           "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    capability = {full: "python.repo.diff_apply_full_testgate.v1",
                  coverage: "python.review.diff_coverage_gate.v1",
                  mutation: "python.review.diff_mutation_gate.v1"}[module]
    assert set(result) == set(registry["capabilities"][capability]["result_fields"])
