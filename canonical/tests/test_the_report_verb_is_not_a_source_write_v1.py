"""What a sentence promises is decided by the OBJECT of its verb, not the verb.

Measured on 7913c4d, seed 11 and 424242 of the end-to-end suite: two sentences that
asked for exactly the same work

  "Repair ... with the test guided repair loop ... save the repair report to R."
  "With the test guided repair loop, repair ... and write the repair report to R."

compiled to different capabilities, because ``write`` is a token in the *provides*
of ``python.software.repair.apply.verified.v1`` and a token in the goal.  The second
sentence therefore reached the tool that OVERWRITES the source -- and the family's
oracle forbids that, so the run was refused for doing what it was told.  ``save``
is not in that capability's provides, which is the whole of the difference.

The fix is lexical and closed on purpose: a verb whose object is an evidence noun
(report, receipt, patch, log, ...) says where evidence goes, it does not ask for the
source bytes to change.  ``apply`` is deliberately not in the neutralized list --
"apply the patch to X" is a real request to write X.

The same confusion existed one layer down, in the front door's own reading of a
repair sentence: "with the coupled multi-edit repair LOOP" made the loop's name a
repair verb, so the witness tests that follow it became repair targets that no
repair could ever change.  Gate and bench then disagreed about the same sentence.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_report_verb"
FIXTURE = WORK / "repairfix"
BASE = "canonical/astra_runtime/tmp/test_report_verb/repairfix"

LOOP = "python.software.repair.loop.test_guided.ast.v1"
WRITER = "python.software.repair.apply.verified.v1"


def _fixture() -> None:
    shutil.rmtree(WORK, ignore_errors=True)
    FIXTURE.mkdir(parents=True)
    (FIXTURE / "calc.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8")
    (FIXTURE / "test_calc.py").write_text(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        "import calc\n"
        "assert calc.add(2, 3) == 5\n", encoding="utf-8")


def _selected(goal: str) -> str:
    _, _, compiled = live.compile_against_live_registry(goal, ROOT)
    return str(compiled.get("selected_capability") or "")


def test_a_report_is_not_a_source_change() -> None:
    # "write the repair report to R" says where evidence goes ...
    assert goal_compiler._artifact_write_tokens(
        "repair X and write the repair report to R") == {"write"}
    # ... while "apply the patch to X" asks for X itself to change, so the verb
    # that names that capability's own action must survive.
    assert goal_compiler._artifact_write_tokens("apply the patch to X") == set()
    assert goal_compiler._artifact_write_tokens("save the report to R") == {"save"}


def test_only_the_object_decides_which_repair_capability_the_sentence_reaches() -> None:
    """The two sentences differ in one verb and must reach the same capability."""
    _fixture()
    try:
        saved = _selected(
            "Repair the python source %s/calc.py with the test guided repair loop so that "
            "the unit tests in %s/test_calc.py pass; save the repair report to %s/r1.json."
            % (BASE, BASE, BASE))
        written = _selected(
            "With the test guided repair loop, repair the python source %s/calc.py so that "
            "the unit tests in %s/test_calc.py pass, and write the repair report to %s/r2.json."
            % (BASE, BASE, BASE))
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
    assert saved == LOOP, saved
    assert written == LOOP, written
    # a sentence that really does ask for the source to change in place still
    # reaches the capability that is allowed to write it
    _fixture()
    try:
        inplace = _selected(
            "Apply the verified repair to the python source %s/calc.py so that the test "
            "%s/test_calc.py passes, and write the report to %s/r3.json."
            % (BASE, BASE, BASE))
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
    assert inplace == WRITER, inplace


def test_a_repair_verb_that_names_a_tool_governs_nothing() -> None:
    """"repair loop" is a tool name; it must not make the witness tests targets."""
    _fixture()
    try:
        root_goal = (
            "Repair the python source root %s with the coupled multi-edit repair loop with "
            "test command \"python -B %s/test_calc.py\" so that the unit tests in "
            "%s/test_calc.py pass, and save the repair report to %s/r.json."
            % (BASE, BASE, BASE, BASE))
        roots = adm._promised_source_roots(root_goal)
        files = adm._promised_source_files(root_goal)
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
    assert roots == [BASE], roots
    # the root governs everything inside it; nothing in there is demanded twice
    assert files == [], files
