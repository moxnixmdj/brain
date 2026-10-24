"""A command is verified by running it again, not by believing the report.

``shell.command.run`` became reachable in PR #6120, and that PR named the gap it
left open: the capability had no independent inspector, so its runs reported
"executed" and never "verified". Measured here, that gap was the single largest
blocker on ordinary requests -- 6 of 15 everyday requests were stopped by
``NO_INDEPENDENT_REINSPECTION_FOR:shell.command.run`` and nothing else. With an
inspector, the everyday denominator moves **2 of 15 -> 9 of 15**.

The obvious check is worthless and this file exists to make sure it was not the
one taken. A command's result already carries ``returncode`` and ``stdout``;
comparing them to themselves proves nothing, which is precisely the failure PR
#6118 documented for a written file. What is available instead is the world: the
command can be run again. So this inspector re-runs the argv and requires
returncode, stdout and stderr to come back identical.

Re-running is only safe for a command that cannot change anything, so the set is
closed and everything outside it is **refused with a named reason rather than
passed**. ``cp``, ``mv``, ``rm``, ``mkdir``, ``touch``, ``tee`` and ``dd`` are
absent on purpose -- re-running one of those is a second side effect, not a
check. ``sort -o FILE`` is refused too, because a reader with an output flag is a
writer. That costs coverage and the cost is stated rather than hidden: those
commands still execute and still report pass, they are simply not certified.

Also pinned here is the defect found while measuring this one. PR #6120's argv
grounding check was written unscoped, and it fired on every capability that
declares its own argv in its ``action_template`` -- the 295 receipt-backed rows
all run ``["python3", "canonical/runtime/<name>.py"]``, and "python3" is not in
"Run the <capability>." Measured, that refused **174 of the 223 passing goals**
with ``STEP_COMMAND_NOT_IN_THE_REQUEST``. A capability's declared argv is part of
a definition verified at acquisition, not something a binder took out of a
sentence, so the check now applies only when the sentence itself states a
command. That is the second test class below, and it fails on 9d0c74b.
"""

from __future__ import annotations

import shutil
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import canonical.runtime.raw_goal_trace_acceptance_v1 as _acceptance  # noqa: E402

INSPECTORS = _acceptance.INSPECTORS

# Looked up rather than imported, so a tree without it yields failing assertions
# with a reason instead of a module-level ImportError that hides every check in
# this file.
_STATES_A_COMMAND_IMPL = getattr(_acceptance, "_STATES_A_COMMAND", None)


def _STATES_A_COMMAND(goal) -> bool:
    if _STATES_A_COMMAND_IMPL is None:
        raise AssertionError(
            "raw_goal_trace_acceptance_v1 applies its argv grounding check to every "
            "argv it sees, including the argv a capability declares in its own "
            "action_template. Measured on 9d0c74b that refused 174 of the 223 passing "
            "goals with STEP_COMMAND_NOT_IN_THE_REQUEST, because the token 'python3' "
            "is not in 'Run the <capability>.'"
        )
    return bool(_STATES_A_COMMAND_IMPL(goal))

# No English words: path components become goal tokens, so a directory named for
# the behaviour under test can change which capability is selected.
SCRATCH = "canonical/astra_runtime/tmp/w8r2t"
BODY = "banana\napple\ncherry\n"


def _fresh() -> str:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    (ROOT / f).write_text(BODY, encoding="utf-8")
    return f


def _inspect(argv, stdout, returncode=0, stderr=""):
    fn = INSPECTORS.get("shell.command.run")
    if fn is None:
        raise AssertionError(
            "shell.command.run has no independent inspector, so every command that "
            "runs is refused with NO_INDEPENDENT_REINSPECTION_FOR and no command can "
            "ever be accepted -- measured, that blocked 6 of 15 ordinary requests."
        )
    return fn({"argv": argv}, {"stdout": stdout, "stderr": stderr,
                               "returncode": returncode}, ROOT)


class TestTheInspectorIsRegistered(unittest.TestCase):
    def test_shell_command_run_has_an_inspector(self):
        self.assertIn("shell.command.run", INSPECTORS)


class TestTheReportIsHeldAgainstTheWorld(unittest.TestCase):
    """The check must be able to fail, or it is a rubber stamp."""

    def setUp(self):
        self.f = _fresh()

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_an_honest_read_is_accepted(self):
        ok, reason, ledger = _inspect(["cat", self.f], BODY)
        self.assertTrue(ok, "refused an honest read: %s" % reason)
        self.assertTrue(ledger.get("command_re_run"), "did not actually re-run: %r" % ledger)

    def test_a_forged_stdout_is_refused(self):
        ok, reason, _ = _inspect(["cat", self.f], "INVENTED CONTENT\n")
        self.assertFalse(ok, "certified a report that does not match the world")
        self.assertEqual(reason, "COMMAND_OUTPUT_NOT_REPRODUCED")

    def test_a_forged_return_code_is_refused(self):
        ok, reason, _ = _inspect(["cat", self.f], BODY, returncode=1)
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_RETURN_CODE_NOT_REPRODUCED")

    def test_a_forged_stderr_is_refused(self):
        ok, reason, _ = _inspect(["cat", self.f], BODY, stderr="a lie\n")
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_STDERR_NOT_REPRODUCED")

    def test_a_forged_line_count_is_refused(self):
        ok, reason, _ = _inspect(["wc", "-l", self.f], "99 %s\n" % self.f)
        self.assertFalse(ok, "certified a line count the file does not have")
        self.assertEqual(reason, "COMMAND_OUTPUT_NOT_REPRODUCED")

    def test_a_true_line_count_is_accepted(self):
        ok, reason, _ = _inspect(["wc", "-l", self.f], "3 %s\n" % self.f)
        self.assertTrue(ok, "refused the real line count: %s" % reason)


class TestNothingIsReRunThatCouldChangeSomething(unittest.TestCase):
    """Fail closed: coverage is refused, never guessed at."""

    def setUp(self):
        self.f = _fresh()

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    # A command that changes something cannot be re-run, so it is held to the
    # promise it made about the world instead -- but only when that promise can
    # be stated precisely enough to be checked.  These cannot, so they are
    # refused rather than passed.
    # `rm` and `tee` are not here any more, and that is the point of both.
    # A single removal has a precise promise -- the path is gone -- and a single
    # tee has one too -- its operand exists when it returns, because tee opens it
    # O_CREAT|O_TRUNC whatever is on stdin.  Each is certified, and every shape of
    # it that cannot be stated is refused, by
    # test_a_removal_is_certified_only_when_the_removal_is_proven_v1 and
    # test_a_command_that_cannot_be_re_run_is_checked_by_what_it_left_v1.
    # What is left is the set for which no promise can be stated at all.
    NO_STATEABLE_PROMISE = ("dd", "chmod", "ln", "sed", "truncate")

    def test_a_mutating_command_with_no_stateable_promise_is_refused(self):
        for program in self.NO_STATEABLE_PROMISE:
            ok, reason, _ = _inspect([program, self.f], "")
            self.assertFalse(ok, "re-ran or certified a mutating command: %s" % program)
            self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")

    def test_a_mutating_command_is_checked_against_the_world_not_re_run(self):
        """cp/mv/mkdir/touch are verified by their effect, and can still fail."""
        dest = "%s/b2.txt" % SCRATCH
        ok, reason, _ = _inspect(["cp", self.f, dest], "")
        self.assertFalse(ok, "certified a copy that was never made")
        self.assertEqual(reason, "COMMAND_CP_DESTINATION_ABSENT_FROM_DISK")
        (ROOT / dest).write_text("NOT THE SOURCE\n", encoding="utf-8")
        ok, reason, _ = _inspect(["cp", self.f, dest], "")
        self.assertFalse(ok, "certified a copy whose bytes differ from the source")
        self.assertEqual(reason, "COMMAND_CP_DESTINATION_DIFFERS_FROM_SOURCE")
        (ROOT / dest).write_text(BODY, encoding="utf-8")
        ok, reason, _ = _inspect(["cp", self.f, dest], "")
        self.assertTrue(ok, "refused a copy that is really there and really equal: %s" % reason)

    def test_a_reader_with_an_output_flag_is_refused(self):
        ok, reason, _ = _inspect(["sort", "-o", "%s/b2.txt" % SCRATCH, self.f], "")
        self.assertFalse(ok, "sort -o writes a file; re-running it is a side effect")
        self.assertEqual(reason, "COMMAND_TAKES_AN_OUTPUT_FLAG")

    def test_an_absent_or_empty_argv_is_refused(self):
        ok, reason, _ = _inspect([], "")
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_ARGV_ABSENT")


class TestEndToEndAnOrdinaryReadIsCertified(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _solve(self, goal):
        from canonical.runtime.live_brain_route_admission_v1 import solve

        return solve({"task_id": "INSP_%x" % time.perf_counter_ns(), "goal": goal})

    def _certified(self, goal):
        return str(self._solve(goal).get("status")).endswith(
            "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED")

    def test_an_ordinary_read_command_reaches_exact_acceptance(self):
        f = _fresh()
        self.assertTrue(
            self._certified("Run the shell command cat %s" % f),
            "an ordinary read command was not certified",
        )

    def test_a_mutating_command_is_certified_from_its_effect_on_the_world(self):
        f = _fresh()
        dest = "%s/b2.txt" % SCRATCH
        result = self._solve("Run the shell command cp %s %s" % (f, dest))
        self.assertIs(result.get("pass"), True, "a stated command stopped running")
        self.assertTrue((ROOT / dest).is_file(), "cp did not produce the copy")
        self.assertEqual((ROOT / dest).read_text(encoding="utf-8"), BODY)
        self.assertTrue(
            str(result.get("status")).endswith("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "a copy that really exists and really matches was not certified: %s"
            % (result.get("raw_goal_acceptance") or {}).get("reason"),
        )

    def test_a_command_that_writes_nothing_still_has_to_produce_the_file(self):
        """`tee` with no stdin makes an empty file. Existence is the whole claim.

        The sentence promised a file, not content, so an empty file is not
        evidence of failure -- but the file must still exist, and that is what
        is asserted, so this pass cannot be a silent no-op.
        """
        _fresh()
        dest = "%s/b2.txt" % SCRATCH
        result = self._solve("Run the shell command tee %s" % dest)
        self.assertTrue(
            (ROOT / dest).is_file(),
            "reported anything at all for a file that was never produced: %s"
            % (result.get("status"),),
        )
        # `tee` writes its file and then cannot be re-run to check it, because
        # re-running is a second write. The honest answer is "I did this and
        # could not verify it", never "done". This asserted failure_class None
        # while solve() said pass=True over a verifier that said pass=False --
        # it pinned the false pass, so it is rewritten to pin the refusal.
        if result.get("pass") is True:
            acc = result.get("raw_goal_acceptance") or {}
            self.assertIsNot(
                acc.get("pass"), False,
                "claimed success over its own verifier's refusal: %s"
                % (acc.get("reason"),),
            )
        else:
            self.assertEqual(result.get("failure_class"), "COMPOSED_CHAIN_NOT_VERIFIED")


class TestEveryPostconditionCanBeFalsified(unittest.TestCase):
    """The full matrix. Each row builds its own world, then asks.

    A postcondition that only ever passes is not a check, so every accepting row
    here is paired with the nearest world in which it must fail: the copy that
    was never made, the copy whose bytes differ, the move that left the source
    behind, the directory that does not exist.
    """

    A = "%s/a1.txt" % SCRATCH
    B = "%s/b2.txt" % SCRATCH
    D = "%s/sub" % SCRATCH

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _world(self):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        (ROOT / self.A).write_text(BODY, encoding="utf-8")

    def _ask(self, argv, expect_ok, expect_reason=""):
        ok, reason, _ = _inspect(argv, "")
        self.assertEqual(
            ok, expect_ok,
            "argv=%r expected ok=%s reason=%s, got ok=%s reason=%s"
            % (argv, expect_ok, expect_reason, ok, reason))
        if expect_reason:
            self.assertEqual(reason, expect_reason)

    def test_cp(self):
        self._world()
        self._ask(["cp", self.A, self.B], False, "COMMAND_CP_DESTINATION_ABSENT_FROM_DISK")
        self._world(); shutil.copy(ROOT / self.A, ROOT / self.B)
        self._ask(["cp", self.A, self.B], True)
        self._world(); (ROOT / self.B).write_text("DIFFERENT\n", encoding="utf-8")
        self._ask(["cp", self.A, self.B], False, "COMMAND_CP_DESTINATION_DIFFERS_FROM_SOURCE")
        self._world(); (ROOT / self.B).write_text("x\n", encoding="utf-8")
        self._ask(["cp", "%s/missing.txt" % SCRATCH, self.B], False,
                  "COMMAND_CP_SOURCE_ABSENT_FROM_DISK")
        self._world(); shutil.copy(ROOT / self.A, ROOT / self.B)
        self._ask(["cp", self.A, self.B, "extra"], False,
                  "COMMAND_CP_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE")
        self._world(); shutil.copy(ROOT / self.A, ROOT / self.B)
        self._ask(["cp", "/etc/passwd", self.B], False, "COMMAND_CP_PATH_OUTSIDE_REPOSITORY")

    def test_mv(self):
        self._world(); (ROOT / self.B).write_text(BODY, encoding="utf-8")
        (ROOT / self.A).unlink()
        self._ask(["mv", self.A, self.B], True)
        self._world(); (ROOT / self.B).write_text("x\n", encoding="utf-8")
        self._ask(["mv", self.A, self.B], False, "COMMAND_MV_SOURCE_STILL_PRESENT")
        self._world()
        self._ask(["mv", self.A, self.B], False, "COMMAND_MV_DESTINATION_ABSENT_FROM_DISK")

    def test_mkdir(self):
        self._world()
        self._ask(["mkdir", self.D], False, "COMMAND_MKDIR_DIRECTORY_ABSENT_FROM_DISK")
        self._world(); (ROOT / self.D).mkdir()
        self._ask(["mkdir", self.D], True)

    def test_touch(self):
        self._world()
        self._ask(["touch", self.B], False, "COMMAND_TOUCH_TARGET_ABSENT_FROM_DISK")
        self._world(); (ROOT / self.B).write_text("", encoding="utf-8")
        self._ask(["touch", self.B], True)

    def test_commands_with_no_stateable_promise_stay_refused(self):
        """`rm` is not in this list any more, and that is the point.

        It used to be, because nothing could be said about a removal.  A single
        removal now has a precise promise -- the path is gone -- and is certified
        by test_a_removal_is_certified_only_when_the_removal_is_proven_v1, which
        also pins every shape that still cannot be stated.  What remains here is
        the set for which no promise can be stated at all.
        """
        self._world()
        for program in ("dd", "chmod", "ln", "sed", "truncate"):
            self._ask([program, self.A], False,
                      "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")


class TestTheArgvCheckOnlyAppliesToAStatedCommand(unittest.TestCase):
    """Regression pin for the defect measuring this file turned up."""

    # Every one of the 295 receipt-backed capabilities declares its own argv in
    # its action_template, and none of those sentences states a command.
    NO_COMMAND = (
        "Run the archive manifest listing.",
        "Run the aa briefcase component summary noninversion v1.",
        "Run the python source audit ast.",
        "Read the file %s/a1.txt" % SCRATCH,
        "Write the text hello world to the file %s/b2.txt" % SCRATCH,
    )
    STATES_A_COMMAND = (
        "Run the shell command cat %s/a1.txt" % SCRATCH,
        "Use the command line wc -l %s/a1.txt" % SCRATCH,
        "Pass the argv cat %s/a1.txt" % SCRATCH,
    )

    def test_a_sentence_that_states_no_command_is_not_asked_about_one(self):
        wrong = [g for g in self.NO_COMMAND if _STATES_A_COMMAND(g)]
        self.assertEqual(
            wrong, [],
            "treated a capability's own declared argv as a claim the sentence made: %r" % wrong,
        )

    def test_a_sentence_that_states_a_command_is_held_to_it(self):
        missing = [g for g in self.STATES_A_COMMAND if not _STATES_A_COMMAND(g)]
        self.assertEqual(missing, [], "a stated command was not recognised: %r" % missing)


if __name__ == "__main__":
    unittest.main()
