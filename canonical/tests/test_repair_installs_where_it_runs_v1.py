"""The repair loop must fix the environment the program runs in, or say it could not.

§A83 found 61 of 154 "verified" capabilities could not run. `repair_v1` imported fine and diagnosed
correctly, and its repair loop still could not repair anything -- the same shape of defect one layer down.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

from canonical.runtime import repair_v1 as R


def test_the_install_targets_the_interpreter_that_will_run_the_program() -> None:
    """THE DEFECT: `python3 -m pip install fasteners` against a command run by `/tmp/venv/bin/python`.

    A module installed into an interpreter the program never uses cannot fix that program's import. The
    repair must address the environment that actually failed, which is the interpreter named in the
    command itself.
    """
    assert R._interpreter_of("/tmp/venv/bin/python app.py") == "/tmp/venv/bin/python"
    assert R._interpreter_of("python3 script.py") == "python3"
    assert R._interpreter_of("python3.11 -m pytest") == "python3.11"
    # not a python command: there is no interpreter to retarget, so the caller falls back
    assert R._interpreter_of("npm test") == ""
    assert R._interpreter_of("") == ""


def test_a_missing_module_is_actually_installed_into_the_running_interpreter() -> None:
    """THE LOOP, END TO END, IN THE DIRECTION THAT MUST SUCCEED.

    The program imports a package that is absent. `attempt` must diagnose it, install it into the very
    interpreter that will run the program, re-run, and report success only because the re-run exited zero.
    """
    name = "six"                                     # small, pure-python, and certainly absent here
    if __import__("importlib").util.find_spec(name) is not None:
        pytest.skip("the probe module is already present, so the failure cannot be produced")

    root = pathlib.Path(tempfile.mkdtemp(prefix="repair_ok_"))
    (root / "app.py").write_text("import %s\nprint('started', %s.__name__)\n" % (name, name))

    out = R.attempt("%s app.py" % sys.executable, str(root), timeout=180, max_attempts=2)

    assert out["ok"] is True, out
    assert out["exit_code"] == 0
    assert "started" in out["output"]


def test_a_repair_that_cannot_be_applied_is_reported_not_retried_into_silence() -> None:
    """THE DEFECT IN THE OTHER DIRECTION, which is the one that produces false reports.

    A package that exists on no index cannot be installed by anyone. The old loop swallowed the failure and
    retried `max_attempts` times, so the trace showed a `setup` on every attempt -- reading as "we tried
    three repairs" when the truth was "we tried none". The loop must stop, and must name the obstruction.
    """
    root = pathlib.Path(tempfile.mkdtemp(prefix="repair_fail_"))
    (root / "app.py").write_text("import this_module_cannot_possibly_exist_zzq\nprint(1)\n")

    out = R.attempt("%s app.py" % sys.executable, str(root), timeout=120, max_attempts=3)

    assert out["ok"] is False
    # it stopped rather than retrying an environment that had not changed
    assert len(out["attempts"]) == 1, out["attempts"]
    assert out["repairs_that_could_not_be_applied"], out
    assert "could not be applied" in out["reason"], out["reason"]
    # and the obstruction is named, not summarised away
    assert "No matching distribution" in out["reason"] or "Could not find a version" in out["reason"]
