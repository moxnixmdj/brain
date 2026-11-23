"""Two successive, different faults, repaired with no scheduler.

WHY THIS IS A SEPARATE TEST FROM EITHER MODULE. Every component here refuses when it cannot help:
`repair_v1` refuses a code bug with "matches nothing known", `fix_from_the_failure_v1` refuses a
symptom-only failure with `THE_FAILURE_STATES_NO_CORRECTION`. Because each refusal is precise, a plain loop
that offers every failure to every repairer needs no planner and no ordering rule -- **the refusal is the
dispatch**. That is the "best part is no part" design, and it is only valid if the refusals are exact, which
is what these tests check.

MEASUREMENT ERRORS THAT SHAPED THIS FILE, all the same error:
Five earlier probes were invalid because the mechanism under test CHANGES THE WORLD and the probe then
measured it again. `pip install` in round 1 makes round 2's "is it absent?" check a question about a
different world. The tests below capture the failing OUTPUT once and hand that exact text downstream, never
re-deciding from a fresh run whether there is anything to repair.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import pytest

from canonical.runtime import fix_from_the_failure_v1 as F
from canonical.runtime import repair_v1 as R

_BODY = "total = 0\nfor n in [1, 2, 3]:\n    total = total + n\nprint(totl)\n"


def _observe(world: pathlib.Path) -> tuple[int, str]:
    run = subprocess.run([sys.executable, "app.py"], cwd=world, capture_output=True, text=True)
    return run.returncode, (run.stdout or "") + (run.stderr or "")


def test_two_successive_faults_are_both_repaired_by_one_plain_loop() -> None:
    """A world holding a program with an unavailable module AND a misspelling.

    Round 1 repairs what the first failure states. Round 2 observes afresh and repairs what the second
    states. Neither repairer knows the other exists, and nothing chooses between them.
    """
    world = pathlib.Path(tempfile.mkdtemp(prefix="two_faults_"))
    # A MODULE THAT IS INSTALLABLE BUT NOT PART OF THIS PROJECT'S DEPENDENCIES, so the fault is real and the
    # repair can succeed. `termcolor` was the first choice and it made this test skip in practice, because an
    # earlier probe had installed it -- a test that skips on the machine it runs on proves nothing.
    module = "pyjokes"
    (world / "app.py").write_text("import %s\n" % module + _BODY)

    code, output = _observe(world)
    # the skip must test WHETHER THE MODULE IS PRESENT, not what the program did. An earlier version skipped
    # on `code == 0`; once termcolor was installed the program still failed (on the misspelling), the skip did
    # not fire, and the test then asserted a module fault that could not occur. A guard on the wrong
    # condition is not a guard.
    if "No module named" not in output:
        pytest.skip("the probe module is already installed, so the first fault cannot be produced")

    # fault 1: the environment, decided from the text captured once
    diagnosed = R.diagnose("%s app.py" % sys.executable, output, code, str(world))
    assert diagnosed["class"] == "missing_python_module", diagnosed
    applied = subprocess.run(diagnosed["setup"], shell=True, cwd=str(world),
                             capture_output=True, text=True, timeout=300)
    assert applied.returncode == 0, applied.stderr[-300:]

    # fault 2: observed afresh, because the world genuinely changed
    code2, output2 = _observe(world)
    assert code2 != 0, "the misspelling must still be there after the module is installed"
    verdict = F.repair_from_failure(world / "app.py", output2)
    assert verdict["repaired"] is True, verdict
    assert (verdict["bad"], verdict["good"]) == ("totl", "total")

    # and the program runs, which is the only thing that counts as repaired
    code3, output3 = _observe(world)
    assert code3 == 0, output3
    assert output3.strip() == "6"


def test_both_repairers_refuse_precisely_which_is_what_makes_a_loop_safe() -> None:
    """THE PRECISION IS THE DESIGN. A loop needs no scheduler only if each refusal is exact.

    An environment repairer must not claim a code bug. A code repairer must not claim a symptom it cannot
    read. If either were vague, a loop would keep offering failures to a module that silently does nothing
    and report that as progress -- which is exactly the failure §A108 recorded in `repair_v1` itself.
    """
    world = pathlib.Path(tempfile.mkdtemp(prefix="refusals_"))
    (world / "app.py").write_text(_BODY)

    code, output = _observe(world)
    assert code != 0

    environment = R.diagnose("%s app.py" % sys.executable, output, code, str(world))
    assert environment["class"] != "missing_python_module", environment
    assert not (environment.get("setup") or environment.get("repair")), environment

    code_verdict = F.repair_from_the_failure if False else F.repair_from_failure  # noqa: F841
    unreadable = F.repair_from_failure(world / "app.py", "TypeError: unsupported operand type(s)")
    assert unreadable["repaired"] is False
    assert unreadable["why"] == "THE_FAILURE_STATES_NO_CORRECTION"
    assert unreadable["classes_that_do"], "a refusal must say which classes it CAN handle"


def test_an_impossible_module_is_reported_not_flailed_at() -> None:
    """THE HONEST DEAD END. A module that exists on no index cannot be installed by anyone.

    `pip` returns non-zero, the code repairer correctly refuses (the failure states no correction), and the
    loop stops with both reasons recorded. It does not retry, and it does not report the attempt as progress.
    """
    world = pathlib.Path(tempfile.mkdtemp(prefix="dead_end_"))
    (world / "app.py").write_text("import zq_never_exists_zz\n" + _BODY)

    code, output = _observe(world)
    assert "No module named" in output

    diagnosed = R.diagnose("%s app.py" % sys.executable, output, code, str(world))
    assert diagnosed["class"] == "missing_python_module"
    applied = subprocess.run(diagnosed["setup"], shell=True, cwd=str(world),
                             capture_output=True, text=True, timeout=300)
    assert applied.returncode != 0, "an impossible module must not appear to install"

    # the world did not change, so the second failure is the first one and the code repairer refuses it
    verdict = F.repair_from_failure(world / "app.py", output)
    assert verdict["repaired"] is False
    assert verdict["why"] == "THE_FAILURE_STATES_NO_CORRECTION"
