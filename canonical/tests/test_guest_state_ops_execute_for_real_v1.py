"""Run the guest state-operation programs for real, verbatim, with no rewriting at all.

`OSWorldHostGuestOps.run` compiles a payload into a Python program with `compile_state_ops` and
sends it to `controller.execute_python_command`. Its existing test supplies a controller that
records the program and returns a canned receipt, so the program was never executed.

State ops are plain filesystem work -- mkdir, write, copy, move, delete, list, replace, json set,
sha256, asserts -- and `_path` only rejects traversal and a handful of protected prefixes. So
these can run **exactly as generated**, against a real directory, with no substitution of any
kind. That is the most faithful execution available anywhere in this repo.

What execution found that the canned controller could not
---------------------------------------------------------
`JSON_SET` reads the file before writing it, so it **cannot create a missing file**. A payload
that means "record this key" fails on a fresh path with `FileNotFoundError`. That is a real
constraint on how the operation may be sequenced, and it was invisible to every existing test.
It is pinned below as a documented limitation rather than papered over.

Also checked by execution and found **correct**: `JSON_SET` appends a real newline. The module
sources `\\\\n` inside an f-string, which reads like it might emit a literal backslash-n; it does
not. The suspicion was tested and dropped.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.osworld_v21_host_guest_ops_v1 import (  # noqa: E402
    GuestOpsError,
    OSWorldHostGuestOps,
)
from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError  # noqa: E402


class RealController:
    """Executes the compiled program. No canned receipts."""

    def __init__(self) -> None:
        self.programs: list[str] = []

    def execute_python_command(self, program: str) -> dict:
        self.programs.append(program)
        result = subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True, timeout=120
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
def work():
    return pathlib.Path(tempfile.mkdtemp(prefix="brain-stateops-"))


@pytest.fixture()
def guest():
    controller = RealController()
    operations = OSWorldHostGuestOps()
    operations.bind_environment(_Env(controller))
    operations._controller_for_tests = controller
    return operations


def _run(guest, ops):
    return guest.run({"ops": ops})


# --------------------------------------------------------------------------- the chain
def test_mkdir_actually_creates_the_directory(guest, work):
    _run(guest, [{"type": "MKDIR", "path": str(work / "a" / "b")}])
    assert (work / "a" / "b").is_dir()


def test_write_text_puts_exactly_that_text_on_disk(guest, work):
    target = work / "notes.txt"
    _run(guest, [{"type": "WRITE_TEXT", "path": str(target), "text": "alpha=1\nbeta=2\n"}])
    assert target.read_text() == "alpha=1\nbeta=2\n"


def test_copy_duplicates_the_bytes(guest, work):
    src = work / "src.txt"
    src.write_text("payload\n")
    dst = work / "deep" / "dst.txt"

    _run(guest, [{"type": "COPY", "src": str(src), "dst": str(dst)}])

    assert dst.exists()
    assert dst.read_bytes() == src.read_bytes()


def test_move_removes_the_source(guest, work):
    src = work / "moving.txt"
    src.write_text("x\n")
    dst = work / "moved.txt"

    _run(guest, [{"type": "MOVE", "src": str(src), "dst": str(dst)}])

    assert dst.exists() and not src.exists()


def test_text_replace_changes_the_disk(guest, work):
    target = work / "notes.txt"
    target.write_text("alpha\nbeta\ngamma\n")

    _run(guest, [
        {"type": "WRITE_TEXT", "path": str(target), "text": "alpha\nbeta\ngamma\n"},
        {"type": "TEXT_REPLACE", "path": str(target), "old": "beta", "new": "BETA"},
    ])

    assert target.read_text() == "alpha\nBETA\ngamma\n"


def test_read_text_returns_what_is_really_there(guest, work):
    target = work / "read.txt"
    target.write_text("on disk\n")

    out = _run(guest, [{"type": "READ_TEXT", "path": str(target), "max_chars": 100}])

    assert "on disk" in out["output"]


def test_list_dir_enumerates_the_real_directory(guest, work):
    (work / "one.txt").write_text("1")
    (work / "two.txt").write_text("2")

    out = _run(guest, [{"type": "LIST_DIR", "path": str(work)}])

    assert "one.txt" in out["output"] and "two.txt" in out["output"]


def test_sha256_file_matches_hashlib(guest, work):
    import hashlib

    target = work / "hash.txt"
    target.write_text("hash me\n")

    out = _run(guest, [{"type": "SHA256_FILE", "path": str(target)}])

    assert hashlib.sha256(target.read_bytes()).hexdigest() in out["output"]


def test_delete_removes_the_file(guest, work):
    target = work / "doomed.txt"
    target.write_text("bye\n")

    _run(guest, [{"type": "DELETE", "path": str(target)}])

    assert not target.exists()


def test_json_set_writes_a_real_newline_at_end_of_file(guest, work):
    """Tested because the module's f-string escaping looks like it might emit a literal \\n."""
    import json

    target = work / "state.json"
    target.write_text("{}\n")

    _run(guest, [{"type": "JSON_SET", "path": str(target), "key": "status", "value": "done"}])

    raw = target.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\\n" not in raw
    assert json.loads(raw.decode()) == {"status": "done"}


# --------------------------------------------------------------------------- what execution found
def test_json_set_cannot_create_a_missing_file(guest, work):
    """A documented limitation, discovered by running it: JSON_SET reads before writing."""
    target = work / "absent.json"
    assert not target.exists()

    with pytest.raises(GuestOpsError):
        _run(guest, [{"type": "JSON_SET", "path": str(target), "key": "k", "value": 1}])


def test_a_failing_assert_stops_the_chain(guest, work):
    """Asserts are compiled into the program; if they did not run, ok=True would be a lie."""
    target = work / "asserted.txt"
    target.write_text("actual\n")

    with pytest.raises(GuestOpsError):
        _run(guest, [
            {"type": "ASSERT_TEXT_EQUALS", "path": str(target), "text": "expected\n"},
        ])


def test_a_passing_assert_completes(guest, work):
    target = work / "asserted.txt"
    target.write_text("expected\n")

    out = _run(guest, [
        {"type": "ASSERT_TEXT_EQUALS", "path": str(target), "text": "expected\n"},
    ])

    assert out["ok"] is True


# --------------------------------------------------------------------------- refusals
def test_traversal_is_refused_before_anything_runs(guest):
    with pytest.raises(StateOpsError):
        _run(guest, [{"type": "READ_TEXT", "path": "/tmp/../etc/passwd"}])


@pytest.mark.parametrize("path", ["/root/.bashrc", "/proc/self/environ", "/evaluation_examples/x"])
def test_protected_paths_are_refused(guest, path):
    with pytest.raises(StateOpsError):
        _run(guest, [{"type": "READ_TEXT", "path": path}])


def test_an_unknown_operation_is_refused(guest):
    with pytest.raises(StateOpsError):
        _run(guest, [{"type": "FORMAT_THE_DISK", "path": "/tmp/x"}])


def test_a_relative_path_is_refused(guest):
    with pytest.raises(StateOpsError):
        _run(guest, [{"type": "READ_TEXT", "path": "relative/x"}])


# --------------------------------------------------------------------------- proof of execution
def test_the_controller_really_ran_a_program(guest):
    _run(guest, [{"type": "MKDIR", "path": str(pathlib.Path(tempfile.mkdtemp()) / "made")}])
    controller = guest._controller_for_tests
    assert controller.programs
    assert "pathlib.Path(" in controller.programs[-1]
