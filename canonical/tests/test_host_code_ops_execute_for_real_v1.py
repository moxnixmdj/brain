"""Run the host code-operation programs for real, instead of pattern-matching them.

THE GAP THIS CLOSES
-------------------
`OSWorldHostCodeOps` never sends a shell to the policy. It builds a **fixed Python program per
operation** (`_program_header()` plus a body), hands that program text to
`environment.controller.execute_python_command`, and parses a JSON receipt out of the output.

Five test files in this repo supply an `execute_python_command`, and every one of them looks
like this:

    def execute_python_command(self, program):
        self.programs.append(program)
        return {"status": "success", "output": json.dumps(self.output)}

That records the program text and returns a **canned** receipt. The program is never run. So
those tests verify routing -- right operation, right arguments, right receipt parsing -- and
they cannot tell a working program from one that raises `NameError` on its first line.

This was demonstrated, not assumed. Monkeypatching `_program_header` so every generated program
dies immediately:

    with the repo's double   -> ok=True    (broken program passes)
    with real execution      -> CodeOpsError: CODE_OP_CONTROLLER_FAILURE

WHAT IS EXERCISED HERE
----------------------
`OSWorldHostCodeOps` end to end: its path safety, its generated programs, and **the effects it
claims on a real filesystem**. Every assertion about a change is checked against the disk, not
against the receipt -- a receipt is the thing that was wrong before.

ROOT MAPPING
------------
`SAFE_ROOTS` is `("/home/oai",)`, the OSWorld deployment root. `_safe_path` is exercised against
that real root. Where the root is not writable, the controller maps the literal root prefix to a
writable temporary directory and records that it did so; the program's logic, imports, asserts
and JSON contract are untouched. Where the root *is* writable it is used directly, unchanged.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.osworld_v21_host_code_ops_v1 import (  # noqa: E402
    CodeOpsError,
    OSWorldHostCodeOps,
)

DEPLOYMENT_ROOT = "/home/oai"
PROJECT = DEPLOYMENT_ROOT + "/share/project"


# --------------------------------------------------------------------------- real execution
class RootedPythonController:
    """Runs the generated program in a real subprocess. No canned receipts."""

    def __init__(self, local_root: pathlib.Path, *, rewrite: bool) -> None:
        self.local_root = str(local_root)
        self.rewrite = rewrite
        self.programs: list[str] = []
        self.rewritten = 0

    def execute_python_command(self, program: str) -> dict:
        self.programs.append(program)
        executed = program
        if self.rewrite:
            if DEPLOYMENT_ROOT in executed:
                self.rewritten += 1
                executed = executed.replace(DEPLOYMENT_ROOT, self.local_root)
        result = subprocess.run(
            [sys.executable, "-c", executed],
            capture_output=True,
            text=True,
            timeout=180,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": (result.stderr or None) if result.returncode else None,
        }


class _Env:
    vm_screen_size = (1920, 1080)

    def __init__(self, controller) -> None:
        self.controller = controller


@pytest.fixture()
def local_root():
    root = pathlib.Path(DEPLOYMENT_ROOT)
    if root.is_dir() and os.access(root, os.W_OK):
        project = root / "share" / "project"
        project.mkdir(parents=True, exist_ok=True)
        for stale in project.iterdir():
            if stale.is_dir():
                import shutil

                shutil.rmtree(stale, ignore_errors=True)
            else:
                stale.unlink(missing_ok=True)
        yield root, False
        return
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain-safe-root-"))
    (tmp / "share" / "project").mkdir(parents=True, exist_ok=True)
    yield tmp, True


@pytest.fixture()
def ops(local_root):
    root, rewrite = local_root
    controller = RootedPythonController(root, rewrite=rewrite)
    operations = OSWorldHostCodeOps()
    operations.bind_environment(_Env(controller))
    operations._controller_for_tests = controller  # for assertions only
    return operations


def _local(root: pathlib.Path, deployment_path: str, rewrite: bool) -> pathlib.Path:
    if not rewrite:
        return pathlib.Path(deployment_path)
    return pathlib.Path(deployment_path.replace(DEPLOYMENT_ROOT, str(root)))


# --------------------------------------------------------------------------- the operations
def test_write_text_verified_puts_exactly_that_text_on_disk(ops, local_root):
    root, rewrite = local_root
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/app.py", "text": "alpha = 1\nbeta = 2\n"}})

    on_disk = _local(root, PROJECT + "/app.py", rewrite).read_text()
    assert on_disk == "alpha = 1\nbeta = 2\n"


def test_read_text_returns_what_is_actually_on_disk(ops, local_root):
    root, rewrite = local_root
    target = _local(root, PROJECT + "/note.txt", rewrite)
    target.write_text("written by the test, not by the operation\n")

    out = ops.run({"operation": "READ_TEXT", "args": {"path": PROJECT + "/note.txt"}})

    assert out["ok"] is True
    assert out["result"]["text"] == "written by the test, not by the operation\n"
    assert out["result"]["chars"] == len("written by the test, not by the operation\n")


def test_replace_text_verified_changes_the_disk(ops, local_root):
    root, rewrite = local_root
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/app.py", "text": "alpha = 1\nbeta = 2\n"}})

    ops.run({"operation": "REPLACE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/app.py", "old": "alpha", "new": "gamma"}})

    assert _local(root, PROJECT + "/app.py", rewrite).read_text() == "gamma = 1\nbeta = 2\n"


def test_python_compile_accepts_a_real_module(ops):
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/ok.py", "text": "def f():\n    return 1\n"}})
    out = ops.run({"operation": "PYTHON_COMPILE", "args": {"path": PROJECT + "/ok.py"}})
    assert out["ok"] is True


def test_python_compile_rejects_a_real_syntax_error(ops):
    """Proves `compile()` actually runs: the fake double cannot fail this way."""
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/bad.py", "text": "def f(:\n    return 1\n"}})
    with pytest.raises(CodeOpsError):
        ops.run({"operation": "PYTHON_COMPILE", "args": {"path": PROJECT + "/bad.py"}})


def test_pytest_reports_a_real_pass(ops):
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/test_ok.py",
                      "text": "def test_truth():\n    assert 1 + 1 == 2\n"}})
    out = ops.run({"operation": "PYTEST",
                   "args": {"cwd": PROJECT, "target": "test_ok.py", "timeout_s": 120}})
    assert out["ok"] is True
    assert out["result"]["returncode"] == 0


def test_pytest_reports_a_real_failure_as_not_ok(ops):
    """A suite that fails must come back ok=False, not as a successful receipt."""
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/test_bad.py",
                      "text": "def test_false():\n    assert 1 + 1 == 3\n"}})
    out = ops.run({"operation": "PYTEST",
                   "args": {"cwd": PROJECT, "target": "test_bad.py", "timeout_s": 120}})
    assert out["ok"] is False
    assert out["result"]["returncode"] != 0


def test_git_status_reads_a_real_repository(ops, local_root):
    root, rewrite = local_root
    project = _local(root, PROJECT, rewrite)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    (project / "tracked.py").write_text("x = 1\n")

    out = ops.run({"operation": "GIT_STATUS", "args": {"cwd": PROJECT}})

    assert out["ok"] is True
    assert "tracked.py" in out["result"]["stdout"]


# --------------------------------------------------------------------------- refusals
def test_unknown_operation_is_refused(ops):
    with pytest.raises(CodeOpsError):
        ops.run({"operation": "DELETE_EVERYTHING", "args": {}})


def test_path_traversal_is_refused(ops):
    with pytest.raises(CodeOpsError):
        ops.run({"operation": "READ_TEXT", "args": {"path": "/home/oai/../etc/passwd"}})


def test_a_path_outside_the_safe_root_is_refused(ops):
    for path in ("/etc/passwd", "/home/oai2/x.py", "/home/user/brain/x.py"):
        with pytest.raises(CodeOpsError):
            ops.run({"operation": "READ_TEXT", "args": {"path": path}})


def test_a_protected_benchmark_path_is_refused(ops):
    with pytest.raises(CodeOpsError):
        ops.run({"operation": "READ_TEXT",
                 "args": {"path": "/home/oai/share/evaluation_examples/x.py"}})


def test_a_relative_path_is_refused(ops):
    with pytest.raises(CodeOpsError):
        ops.run({"operation": "READ_TEXT", "args": {"path": "share/project/app.py"}})


def test_the_controller_really_ran_a_program(ops):
    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/app.py", "text": "alpha = 1\n"}})
    ops.run({"operation": "READ_TEXT", "args": {"path": PROJECT + "/app.py"}})
    controller = ops._controller_for_tests
    assert controller.programs, "no program was executed"
    assert "pathlib.Path(" in controller.programs[-1]


# --------------------------------------------------------------------------- the falsification
def test_a_program_that_cannot_run_is_never_reported_as_ok(ops, monkeypatch):
    """The claim under test: those receipts mean the operation worked.

    With the repo's double they do not -- a program that dies on line 1 still returns ok=True.
    With real execution it cannot.
    """
    import canonical.runtime.osworld_v21_host_code_ops_v1 as module

    ops.run({"operation": "WRITE_TEXT_VERIFIED",
             "args": {"path": PROJECT + "/app.py", "text": "alpha = 1\n"}})

    class CannedController:
        def execute_python_command(self, program):
            return {"status": "success",
                    "output": json.dumps({"ok": True, "operation": "PYTHON_COMPILE",
                                          "path": PROJECT + "/app.py"})}

    with monkeypatch.context() as patch:
        patch.setattr(module, "_program_header",
                      lambda: "UNDEFINED_NAME_FROM_A_TYPO\n")
        canned = OSWorldHostCodeOps()
        canned.bind_environment(_Env(CannedController()))
        pretend = canned.run({"operation": "PYTHON_COMPILE",
                              "args": {"path": PROJECT + "/app.py"}})
    assert pretend["ok"] is True, "the double is expected to accept a broken program"

    with monkeypatch.context() as patch:
        patch.setattr(module, "_program_header",
                      lambda: "UNDEFINED_NAME_FROM_A_TYPO\n")
        with pytest.raises(CodeOpsError):
            ops.run({"operation": "PYTHON_COMPILE",
                     "args": {"path": PROJECT + "/app.py"}})
