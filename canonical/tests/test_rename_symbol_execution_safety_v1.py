"""A test-process failure must not leave a rename or forge verification."""
import json
import subprocess
import sys

import pytest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


def _fixture(tmp_path, test_source="def test_ok():\n    assert True\n"):
    src = tmp_path / "src"
    src.mkdir()
    (src / "core.py").write_text("def old_name():\n    return 1\n")
    tests = src / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text(test_source)
    return src


def _args(executable=sys.executable):
    return {"source_root": "src", "module": "core.py", "qualname": "old_name",
            "new_symbol": "new_name", "output_path": "out/report.json",
            "run_tests": ["tests/test_example.py"], "python_executable": str(executable),
            "timeout_s": 1}


@pytest.mark.parametrize("mode", ["missing", "directory", "not_executable", "timeout"])
def test_test_process_failure_restores_the_original_file(tmp_path, mode):
    src = _fixture(tmp_path, "import time\ndef test_wait():\n    time.sleep(3)\n")
    original = (src / "core.py").read_bytes()
    if mode == "missing":
        executable = tmp_path / "missing-python"
    elif mode == "directory":
        executable = tmp_path
    elif mode == "not_executable":
        executable = tmp_path / "not-executable"
        executable.write_text("not executable")
        executable.chmod(0o644)
    else:
        executable = sys.executable
    with pytest.raises((OSError, subprocess.TimeoutExpired)):
        rename.run(_args(executable), tmp_path)
    assert (src / "core.py").read_bytes() == original
    assert not (tmp_path / "out/report.json").exists()


@pytest.mark.parametrize("case", range(4))
def test_pytest_plugin_cannot_forge_verified_rename(tmp_path, case):
    src = _fixture(tmp_path, f"def test_fails_{case}():\n    assert False\n")
    (src / "conftest.py").write_text(
        "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n")
    args = _args()
    args["timeout_s"] = 30
    result = rename.run(args, tmp_path)
    artifact = json.loads((tmp_path / "out/report.json").read_text())
    assert result["verified"] is False
    assert artifact["verified"] is False
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["local_gate"] == "PASS"
    assert result["test_evidence_authentication"] == "UNAUTHENTICATED"


def test_genuinely_passing_tests_are_also_provisional(tmp_path):
    _fixture(tmp_path)
    args = _args()
    args["timeout_s"] = 30
    result = rename.run(args, tmp_path)
    assert result["local_gate"] == "PASS"
    assert result["gate"] == "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    assert result["verified"] is False
