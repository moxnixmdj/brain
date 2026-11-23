"""A repair derived from the failure, with no fixed reference and no model.

The bottleneck: `repair_v1` repairs the environment and refused six ordinary program bugs as "matches
nothing known" -- correctly, because their repair is an EDIT. `fix_shape_v1` needs both the buggy and the
fixed program, which a real task never gives.

The criterion this module tests is narrow and stated: **the failure must state the correction, and the world
must confirm it.** One of four ordinary bugs meets it. That ratio is the honest content here.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

from canonical.runtime import fix_from_the_failure_v1 as F


def _run(source: str) -> tuple[pathlib.Path, str]:
    directory = pathlib.Path(tempfile.mkdtemp(prefix="fix_"))
    program = directory / "m.py"
    program.write_text(source)
    result = subprocess.run([sys.executable, str(program)], capture_output=True, text=True)
    return program, (result.stdout or "") + (result.stderr or "")


def test_a_misspelling_the_interpreter_names_is_repaired_and_judged_by_re_running() -> None:
    """THE ONE REPAIRABLE CLASS, end to end.

    CPython prints both the bad name and the correction. The correction is then checked against the file --
    it must be a name the program actually uses -- and the edit is confirmed by EXIT 0 on a re-run, never by
    the suggestion being plausible.
    """
    program, output = _run("total = 0\nfor n in [1, 2, 3]:\n    total = total + n\nprint(totl)\n")
    assert "NameError" in output and "Did you mean" in output

    verdict = F.repair_from_failure(program, output)

    assert verdict["repaired"] is True, verdict
    assert (verdict["bad"], verdict["good"]) == ("totl", "total")
    assert verdict["judged_by"].startswith("RE_RUNNING")
    # the program really runs now, and says what it should
    again = subprocess.run([sys.executable, str(program)], capture_output=True, text=True)
    assert again.returncode == 0 and again.stdout.strip() == "6"


def test_a_failure_that_states_no_correction_is_refused_and_the_classes_are_named() -> None:
    """THREE OF FOUR ORDINARY BUGS ARE NOT REPAIRABLE THIS WAY, and the refusal says which classes are.

    `KeyError`, `TypeError` and `IndexError` state a problem and no correction. A caller deciding whether to
    keep trying needs to know that, not that the system "failed".
    """
    for source in ("cfg = {'a': 1}\nprint(cfg['b'])\n",           # KeyError
                   "n = '3'\nprint(n + 1)\n",                     # TypeError
                   "xs = [1, 2]\nprint(xs[5])\n"):                # IndexError
        program, output = _run(source)
        verdict = F.repair_from_failure(program, output)
        assert verdict["repaired"] is False, verdict
        assert verdict["why"] == "THE_FAILURE_STATES_NO_CORRECTION", verdict
        assert verdict["classes_that_do"], "a refusal must say which classes it can handle"
        # and the file was not touched
        assert program.read_text() == source


def test_a_suggested_name_that_is_not_in_the_program_is_refused() -> None:
    """The interpreter can suggest a builtin or a name from another module.

    Replacing with a name this file never uses trades one NameError for another, so the suggestion is checked
    BEFORE the edit rather than discovered by the re-run.
    """
    program, output = _run("print(totl)\n")
    verdict = F.repair_from_failure(
        program, "NameError: name 'totl' is not defined. Did you mean: 'total'?")

    assert verdict["repaired"] is False, verdict
    assert verdict["why"] == "THE_SUGGESTED_NAME_IS_NOT_IN_THE_PROGRAM"
    assert program.read_text() == "print(totl)\n"


def test_an_edit_that_does_not_make_the_program_run_is_reverted() -> None:
    """THE SAFETY PROPERTY, and the reason a plausible edit is not enough.

    A replacement can satisfy every static check and still not run -- the re-run is the judge, and a failed
    edit is undone. Leaving a wrong edit in place because it was plausible is worse than leaving the original
    bug: the original at least fails the same way twice.
    """
    # `len` exists as a name here, so the static check passes, but replacing `cont` with it cannot run:
    # `len` takes an argument and is then concatenated to a string.
    source = "cont = 'a'\nprint(cont + 'b')\ntotal = cont\n"
    program, _ = _run(source)
    output = "NameError: name 'cont' is not defined. Did you mean: 'len'?"

    verdict = F.repair_from_failure(program, output)

    # either it refused before editing, or it edited, failed, and reverted -- both leave the file intact
    assert program.read_text() == source, (verdict, program.read_text())
    if verdict.get("reverted"):
        assert verdict["why"] == "THE_EDIT_DID_NOT_MAKE_THE_PROGRAM_RUN"
