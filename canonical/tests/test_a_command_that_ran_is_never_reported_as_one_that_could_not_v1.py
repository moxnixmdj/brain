"""A command that ran must never be reported as one that could not.

`execute_chain` dispatches a command and only then lets the adapter check its own
expectations, so the adapter can raise AFTER the work has landed.  For `rm A` the
file is deleted and only then does the output check fail -- and the step that
raised was never appended, so the only record that a command had been dispatched
was destroyed at the moment it was created.

Measured on b364795:

    "Run the shell command rm A"
        -> A deleted
        -> execute_chain: status FAIL__COMPOSER_STEP_RAISED, steps []
        -> solve(): FAIL__RAW_GOAL_COMPILATION_GAP, composer_route null

The system deleted a file and then reported that it could not turn the sentence
into an executable contract.  A false report in that direction is the one kind
that must never happen: it tells the operator nothing changed when something did.
"""

import shutil
import unittest

from canonical.runtime import live_brain_route_admission_v1 as ra

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/ran1"


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    (d / "a1.txt").write_text("body\n", encoding="utf-8")
    return "%s/%s" % (SCRATCH, name)


def _solve(goal):
    from time import perf_counter_ns
    return ra.solve({"task_id": "RAN%d" % perf_counter_ns(), "goal": goal})


class TestACommandThatRanIsReportedAsOneThatRan(unittest.TestCase):

    def test_a_deletion_that_landed_is_not_reported_as_a_compilation_gap(self):
        """The report must not deny a side effect that already happened."""
        base = _fresh("rmcase")
        target = "%s/a1.txt" % base
        result = _solve("Run the shell command rm %s" % target)

        self.assertFalse((ROOT / target).exists(), "fixture did not delete")
        self.assertNotEqual(
            result.get("failure_class"),
            "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
            "reported 'could not make this executable' about a command that ran",
        )
        self.assertEqual(result.get("failure_class"), "STEP_RAISED_OUTCOME_UNKNOWN")

    def test_the_record_names_the_command_that_was_dispatched(self):
        """The argv must survive, or nothing downstream can ever know."""
        base = _fresh("rmcase2")
        target = "%s/a1.txt" % base
        result = _solve("Run the shell command rm %s" % target)
        steps = (result.get("composer_execution") or {}).get("steps") or []
        self.assertTrue(steps, "no step record survived the adapter raising")
        argv = (steps[0].get("args") or {}).get("argv") or []
        self.assertIn("rm", argv)
        self.assertIn(target, argv)
        self.assertTrue(
            steps[0].get("adapter_raised"),
            "the reason the adapter raised was discarded",
        )

    def test_it_is_still_refused(self):
        """This is a truthful report, not acceptance.  Fail closed stays closed."""
        base = _fresh("rmcase3")
        result = _solve("Run the shell command rm %s/a1.txt" % base)
        self.assertIs(result.get("pass"), False)
        self.assertNotIn("PASS", str(result.get("status")))


class TestACommandThatNeverRanIsStillReportedAsOneThatNeverRan(unittest.TestCase):

    def test_a_chain_that_dispatched_nothing_still_reports_the_honest_gap(self):
        """The scoping: no step dispatched means no claim that work happened."""
        base = _fresh("mkcase")
        result = _solve("Run the shell command mkdir %s/sub" % base)
        self.assertIs(result.get("pass"), False)
        steps = (result.get("composer_execution") or {}).get("steps") or []
        dispatched = [s for s in steps
                      if s.get("adapter_raised") is not None
                      or s.get("result") is not None]
        if not dispatched:
            self.assertNotEqual(
                result.get("failure_class"), "STEP_RAISED_OUTCOME_UNKNOWN",
                "claimed a command ran when none was dispatched",
            )


if __name__ == "__main__":
    unittest.main()
