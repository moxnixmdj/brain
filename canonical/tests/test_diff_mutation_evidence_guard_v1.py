# PROJECT_BRAIN
"""Mutation kills require test-failure evidence, not arbitrary process failure."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as gate


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, test: str, conftest: str = "") -> None:
    anchor = root / "anchor"
    _write(anchor, "subject.py", "VALUE = 1\n\ndef preserved():\n    return 'intact'\n")
    _write(anchor, "tests/test_subject.py", test)
    if conftest:
        _write(anchor, "tests/conftest.py", conftest)
    _write(root, "change.diff", "--- a/subject.py\n+++ b/subject.py\n"
           "@@ -1,2 +1,2 @@\n-VALUE = 1\n+VALUE = 2\n \n")


def _run(root: Path, timeout: int = 30):
    return gate.run({"anchor_path": "anchor", "diff_path": "change.diff",
                     "output_path": "out/mutation.json", "python_executable": sys.executable,
                     "max_mutants": 1, "timeout_s": timeout}, root)


_BLIND_TEST = "from subject import preserved\ndef test_preserved():\n    assert preserved() == 'intact'\n"
_CHECK = "'VALUE = 3' in Path('subject.py').read_text()"


@pytest.mark.parametrize("test,conftest", [
    (_BLIND_TEST, "from pathlib import Path\nimport pytest\n"
     "def pytest_sessionstart(session):\n"
     f"    if {_CHECK}:\n        pytest.exit('session aborted', returncode=3)\n"),
    (_BLIND_TEST, "from pathlib import Path\nimport pytest\n"
     "def pytest_collection_modifyitems(items):\n"
     f"    if {_CHECK}:\n        pytest.exit('collection aborted', returncode=4)\n"),
    ("import subject\nif subject.VALUE == 3:\n    raise ImportError('collection error')\n" + _BLIND_TEST, ""),
    ("import subject, pytest\nif subject.VALUE == 3:\n    pytest.skip('nothing collected', allow_module_level=True)\n"
     + _BLIND_TEST, ""),
], ids=["session-abort", "collection-abort", "import-error", "nothing-collected"])
def test_an_aborted_mutant_run_is_inconclusive_not_killed(tmp_path, monkeypatch, test, conftest):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, test, conftest)
    result = _run(tmp_path)
    assert result["gate"] == "FAIL"
    assert result["verified"] is False
    assert result["mutants_killed"] == 0
    assert result["mutants_inconclusive"] == 1
    assert result["inconclusive"][0]["reason"] == "NO_RELIABLE_TEST_VERDICT"


def test_mutant_timeout_is_inconclusive_not_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, _BLIND_TEST,
             "from pathlib import Path\nimport time\n"
             "def pytest_sessionstart(session):\n"
             f"    if {_CHECK}:\n        time.sleep(5)\n")
    result = _run(tmp_path, timeout=3)
    assert result["gate"] == "FAIL"
    assert result["verified"] is False
    assert result["mutants_killed"] == 0
    assert result["mutants_inconclusive"] == 1
    assert result["inconclusive"][0]["reason"] == "TIMEOUT"


def test_all_skipped_base_suite_cannot_establish_a_mutation_baseline(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "import pytest\n@pytest.mark.skip(reason='unavailable')\n"
             "def test_case():\n    assert False\n")
    with pytest.raises(SystemExit, match="BASE_WORLD_RED"):
        _run(tmp_path)


def test_an_observed_test_failure_can_kill_the_mutant(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "from subject import VALUE\ndef test_value():\n    assert VALUE == 2\n")
    result = _run(tmp_path)
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["local_gate"] == "PASS"
    assert result["verified"] is False
    assert result["mutant_limit_reached"] is True
    assert result["mutants_killed"] == 1
    assert result["mutants_inconclusive"] == 0


@pytest.mark.parametrize("action", ["report.unlink()", "report.write_text('<bad')"], ids=["missing", "malformed"])
def test_missing_or_malformed_mutant_report_is_inconclusive(tmp_path, monkeypatch, action):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    conftest = ("from pathlib import Path\n"
                "def pytest_unconfigure(config):\n"
                f"    if {_CHECK}:\n"
                "        report = Path(config.option.xmlpath)\n"
                f"        {action}\n")
    _project(tmp_path, _BLIND_TEST, conftest)
    result = _run(tmp_path)
    assert result["gate"] == "FAIL"
    assert result["mutants_killed"] == 0
    assert result["mutants_inconclusive"] == 1


def test_mutant_failure_with_forced_zero_exit_is_inconclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _project(tmp_path, "from subject import VALUE\ndef test_value():\n    assert VALUE == 2\n",
             "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n")
    result = _run(tmp_path)
    assert result["gate"] == "FAIL"
    assert result["mutants_killed"] == 0
    assert result["mutants_inconclusive"] == 1
