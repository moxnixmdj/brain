#!/usr/bin/env python3
"""A check that ran nothing is not a pass.

The defect this closes
----------------------
`generalization_rung_gradient_v1.Check._runs` stood a project's check up with
``python -m unittest <module>`` and took ``returncode == 0`` as "the check passes". For a
module whose tests are plain ``def test_*()`` functions -- pytest style, with no
``unittest.TestCase`` -- `unittest` collects **nothing**, prints ``Ran 0 tests ... OK`` and
exits **0**. The check was then recorded ``available=True`` and accepted *every* candidate,
including a deliberately broken one.

Measured on this repository at base `b8c42ebce3`: of 2,592 ``test_*.py`` files under
``canonical/``, **943 (36.4%)** declare module-level test functions and no ``TestCase``.
Two were run both ways:

    canonical/runtime/test_requirement_graph_kernel.py
        unittest: Ran 0 tests ... OK   (exit 0)      pytest: 10 passed
    canonical/runtime/test_prequalification_stage_a_reducer.py
        unittest: Ran 0 tests ... OK   (exit 0)      pytest:  4 passed

Why this outranks every learning idea
-------------------------------------
A missing check is honest: it says "unknown" and the caller refuses. A *vacuous* check is
worse than no check, because it says "verified" about an edit nobody tested. Every route that
learns from a verification bit inherits the lie:

* ASCENT (arXiv:2610.05303) skips the weight update when verification fails. A verifier that
  cannot fail trains on every trajectory, including the wrong ones, permanently.
* Experience Distillation (arXiv:2607.21051) distils from verified trajectories; its corpus
  is only as good as its acceptance bit.
* Token-space reuse is the same: this repo's own `a_failure_is_a_context_not_a_ban` probe
  shows a boundary needs a *real* contrasting failure. A vacuous pass supplies none, so the
  lesson generalises past the situation that made it true.

So this is not a test-hygiene fix. It is the admission gate on the learning signal itself,
and it is a prerequisite for token-space and weight-space learning alike.

What it does
------------
`run_check` executes the check and returns how many tests it **actually ran**. Zero is never
a pass. When `unittest` collects nothing the pytest collector is tried, so the 943 files
become real checks instead of false ones. When neither collector can run, the reason is
reported and the caller refuses -- it does not fall back to "OK".

Authority NONE. This module registers no capability and claims no benchmark movement.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CHECK_COLLECTION_ADMISSION_V1"
AUTHORITY = "NONE"

#: Reasons are distinct because the repair for each is different work.
RAN_NO_TESTS = "CHECK_RAN_NO_TESTS"
COLLECTOR_UNAVAILABLE = "CHECK_COLLECTOR_UNAVAILABLE"
DEPENDENCY_MISSING = "CHECK_DEPENDENCY_MISSING"
TIMED_OUT = "CHECK_TIMED_OUT"
COULD_NOT_START = "CHECK_COULD_NOT_START"

_UNITTEST_RAN = re.compile(r"^Ran (\d+) tests?\b", re.MULTILINE)
_PYTEST_COUNT = re.compile(r"(\d+) (passed|failed|error|errors|xfailed|xpassed)\b")
_DEFAULT_TIMEOUT_S = 180


def _module_to_path(module: str) -> str:
    return module.replace(".", "/") + ".py"


def parse_unittest(stdout: str, stderr: str) -> int:
    """Tests actually executed, per unittest's own summary. Absent summary means zero.

    A module that fails to IMPORT is reported by unittest as a synthetic `_FailedTest`:
    ``Ran 1 test ... FAILED (errors=1)``. That 1 is the loader's placeholder, not a test of
    the code under test, so it is not counted -- otherwise a missing dependency reads as
    "the candidate failed the tests" and blames the edit for the machine.
    """
    text = stdout + "\n" + stderr
    if import_failed(text):
        return 0
    match = _UNITTEST_RAN.search(stderr) or _UNITTEST_RAN.search(stdout)
    return int(match.group(1)) if match else 0


def import_failed(text: str) -> bool:
    """Whether a runner could not import the module at all."""
    return ("ModuleNotFoundError" in text or "ImportError" in text
            or "_FailedTest" in text)


def parse_pytest(stdout: str, stderr: str) -> int:
    """Tests that reached a verdict on the code under test.

    Skipped and deselected prove nothing. Neither does an ERROR: a module that errored during
    collection never ran, and counting it would turn "the dependency is missing" into "the
    candidate failed the tests" -- blaming the edit for the machine. Errors are classified
    separately by `collection_errored`.
    """
    text = stdout + "\n" + stderr
    total = 0
    for count, kind in _PYTEST_COUNT.findall(text):
        if kind in ("passed", "failed", "xfailed", "xpassed"):
            total += int(count)
    return total


def collection_errored(stdout: str, stderr: str) -> bool:
    text = stdout + "\n" + stderr
    return ("error during collection" in text or "errors during collection" in text
            or "Interrupted:" in text and "error" in text)


def _spawn(argv: list[str], cwd: pathlib.Path, env: Mapping[str, str],
           timeout_s: int) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(argv, cwd=str(cwd), capture_output=True,
                              timeout=timeout_s, env=dict(env))
    except (subprocess.TimeoutExpired, OSError):
        return None


def run_check(test_module: str, *, cwd: pathlib.Path | str,
              env: Mapping[str, str] | None = None,
              timeout_s: int = _DEFAULT_TIMEOUT_S,
              python: str | None = None) -> dict[str, Any]:
    """Run a project's check and prove it executed at least one test.

    Returns ``{"ran": bool, "passed": bool|None, "collected": int, "runner": str,
    "reason": str}``. ``passed`` is ``None`` whenever nothing ran: there is no verdict to
    have. A caller must treat ``ran=False`` as *unknown*, never as success.
    """
    import sys

    directory = pathlib.Path(cwd)
    interpreter = python or sys.executable
    environment = dict(env) if env is not None else dict(os.environ)
    out: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "test_module": test_module,
        "ran": False, "passed": None, "collected": 0, "runner": "none", "reason": RAN_NO_TESTS,
        "attempts": [],
    }
    if not test_module:
        out["reason"] = RAN_NO_TESTS
        return out

    # --- unittest collector -------------------------------------------------
    done = _spawn([interpreter, "-m", "unittest", test_module], directory, environment, timeout_s)
    if done is None:
        out["reason"] = TIMED_OUT
        out["attempts"].append({"runner": "unittest", "started": False})
        return out
    stdout = done.stdout.decode("utf-8", errors="replace")
    stderr = done.stderr.decode("utf-8", errors="replace")
    collected = parse_unittest(stdout, stderr)
    out["attempts"].append({"runner": "unittest", "collected": collected,
                            "returncode": done.returncode})
    if collected > 0:
        out.update(ran=True, passed=done.returncode == 0, collected=collected,
                   runner="unittest", reason="")
        return out
    if import_failed(stdout + "\n" + stderr):
        # Import failure is a missing dependency under either collector; say so now.
        out["reason"] = DEPENDENCY_MISSING
        return out

    # --- pytest collector (the 943 files unittest cannot see) ---------------
    done = _spawn([interpreter, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                   _module_to_path(test_module)], directory, environment, timeout_s)
    if done is None:
        out["reason"] = TIMED_OUT
        out["attempts"].append({"runner": "pytest", "started": False})
        return out
    stdout = done.stdout.decode("utf-8", errors="replace")
    stderr = done.stderr.decode("utf-8", errors="replace")
    if "No module named pytest" in stderr or "No module named pytest" in stdout:
        out["reason"] = COLLECTOR_UNAVAILABLE
        out["attempts"].append({"runner": "pytest", "available": False})
        return out
    collected = parse_pytest(stdout, stderr)
    out["attempts"].append({"runner": "pytest", "collected": collected,
                            "returncode": done.returncode})
    if collection_errored(stdout, stderr):
        # The module never ran. A missing import is a dependency; anything else is a
        # collector that could not start. Neither is a verdict on the candidate.
        out["reason"] = (DEPENDENCY_MISSING
                         if "ModuleNotFoundError" in stdout or "ImportError" in stdout
                         else COULD_NOT_START)
        return out
    if collected > 0:
        # pytest exit 0 = all passed; 1 = tests failed. 5 = nothing collected.
        out.update(ran=True, passed=done.returncode == 0, collected=collected,
                   runner="pytest", reason="")
        return out
    if "ModuleNotFoundError" in stdout or "ImportError" in stdout:
        out["reason"] = DEPENDENCY_MISSING
        return out
    out["reason"] = RAN_NO_TESTS
    return out


def accepts(candidate_is_ok: dict[str, Any], *, expect: str = "PASS") -> bool:
    """Whether a check verdict licenses an edit. Unknown is never assent.

    ``expect`` is what the check must say about the file *as it is*: PASS for a migration
    (the edit must keep it working), FAIL for a repair (the edit must fix it).
    """
    if not candidate_is_ok.get("ran") or candidate_is_ok.get("passed") is None:
        return False
    return bool(candidate_is_ok["passed"]) == (expect == "PASS")
