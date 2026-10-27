"""A path the sentence reserved for the report is not an operand of a command.

Measured on 53150bd: the sentence

    "Rename the parameter old_price to price in the python module X
     and save the report to R."

bound ``mv X R``.  ``_RESULT_DESTINATION`` saw "to R" and read R as the
destination of the command -- true of "copy the file A to the file B" and false
here, because what goes to R is the REPORT.  The command removed X, the front
door refused the run with ``FAIL_CLOSED__NAMED_INPUT_REMOVED``, and the source
was gone: the refusal was honest and the loss was permanent.

The invariant is role exclusivity, and it is one line: a path the sentence
introduces as where its evidence goes belongs to the report and to nothing else,
so a command that changes the filesystem may not take it as an operand.  A
read-only program is untouched by this -- its stdout is what lands in that path,
which is the mechanism that already existed.

These tests are written in pairs: every refusal is paired with the sentence in
which the same rule must NOT fire.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_report_path_role"
BASE = "canonical/astra_runtime/tmp/test_report_path_role"


def test_a_report_path_is_never_an_operand_of_a_mutating_command() -> None:
    # the sentence that deleted its own source
    assert composer._prose_argv(
        "Rename the parameter old_price to price in the python module "
        f"{BASE}/pkg/util.py and save the report to {BASE}/r7.json.") is None
    # the same sentence with the deletion verb and the report path swapped in
    assert composer._prose_argv(
        f"Move the python module {BASE}/pkg/util.py and save the report to "
        f"{BASE}/r7.json.") is None


def test_a_real_destination_still_binds_exactly_as_before() -> None:
    """The rule must not touch a sentence whose destination is the command's."""
    copy = composer._prose_argv(
        f"Copy the file {BASE}/pkg/util.py to the file {BASE}/pkg/bak.py.")
    assert copy is not None and copy[0] == "cp", copy
    assert copy[-2:] == [f"{BASE}/pkg/util.py", f"{BASE}/pkg/bak.py"], copy
    move = composer._prose_argv(
        f"Move the file {BASE}/pkg/util.py to the file {BASE}/pkg/bak.py.")
    assert move is not None and move[0] == "mv", move
    assert move[-2:] == [f"{BASE}/pkg/util.py", f"{BASE}/pkg/bak.py"], move


def test_a_read_only_command_may_still_write_its_result_to_the_report_path() -> None:
    """Excluding the path from OPERANDS is not excluding it as a destination."""
    argv = composer._prose_argv(
        f"Write the unique lines of {BASE}/a.txt to the file {BASE}/b.txt.")
    if argv is not None:  # the read-only route may or may not claim this shape
        assert BASE + "/b.txt" not in argv[:-1], argv


def test_the_refused_rename_leaves_the_source_file_where_it_was() -> None:
    shutil.rmtree(WORK, ignore_errors=True)
    (WORK / "pkg").mkdir(parents=True)
    source = WORK / "pkg/util.py"
    original = "def add(a, b):\n    return a + b\n"
    source.write_text(original, encoding="utf-8")
    goal = (f"Rename the parameter old_price to price in the python module "
            f"{BASE}/pkg/util.py and save the report to {BASE}/r7.json.")
    try:
        result = adm.solve({"task_id": "TEST_REPORT_PATH_ROLE", "goal": goal})
    finally:
        survived = source.is_file()
        content = source.read_text(encoding="utf-8") if survived else None
        shutil.rmtree(WORK, ignore_errors=True)
    assert survived, "the run removed the source file it was asked to edit"
    assert content == original, content
    # the run is still refused -- the request names a refactor the machine
    # cannot bind, and a refusal is the honest answer
    assert result.get("pass") is False, result.get("status")
