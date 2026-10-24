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
    """A dispatched command is recorded, whatever happened next.

    Originally written against `rm A`, which deleted A and was then reported as a
    compilation gap.  A single removal is now certified outright (see
    test_a_removal_is_certified_only_when_the_removal_is_proven_v1), so the
    invariant is asserted on a dispatch that still ends in a raise: a removal
    whose target was never there.  The command was still dispatched, and the
    record still has to say so.
    """

    def test_a_dispatch_that_raised_is_not_reported_as_a_compilation_gap(self):
        base = _fresh("rmcase")
        result = _solve("Run the shell command rm %s/never_existed.txt" % base)
        self.assertNotEqual(
            result.get("failure_class"),
            "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
            "reported 'could not make this executable' about a command that was dispatched",
        )

    def test_the_record_names_the_command_that_was_dispatched(self):
        base = _fresh("rmcase2")
        target = "%s/never_existed.txt" % base
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

    def test_a_removal_that_could_not_happen_is_still_refused(self):
        """Certifying a real removal must not certify one that never happened."""
        base = _fresh("rmcase3")
        result = _solve("Run the shell command rm %s/never_existed.txt" % base)
        self.assertIs(result.get("pass"), False)
        self.assertNotIn("PASS", str(result.get("status")))


class TestACommandThatNeverRanIsStillReportedAsOneThatNeverRan(unittest.TestCase):
    """The other half, tested against the guarantee rather than against one command.

    This was originally written against `mkdir`, which at the time refused before
    dispatching anything.  `mkdir` now runs, so naming a command here would pin a
    limitation instead of the invariant.  The invariant is: when no step was
    dispatched, _try_composed returns None and the caller keeps reporting the
    honest compilation gap -- it must never claim work that did not start.
    """

    def test_a_chain_with_no_dispatched_step_returns_none(self):
        from canonical.runtime import composer_route_v1 as croute

        original = croute.execute_chain
        try:
            croute.execute_chain = lambda chain, goal, *a, **k: {
                "pass": False, "status": "OPEN__COMPOSER_SLOT_UNBOUND",
                "steps": [], "failed_step": {"missing_slots": ["output_path"]},
            }
            self.assertIsNone(
                ra._try_composed("NODISPATCH", "Run the shell command xyz q1", 0),
                "claimed a command ran when the chain dispatched nothing",
            )
        finally:
            croute.execute_chain = original

    def test_a_step_that_only_recorded_a_type_error_is_not_a_dispatched_command(self):
        """A step rejected before the adapter was entered ran nothing."""
        from canonical.runtime import composer_route_v1 as croute

        original = croute.execute_chain
        try:
            croute.execute_chain = lambda chain, goal, *a, **k: {
                "pass": False, "status": "FAIL__COMPOSER_STEP_REJECTED",
                "steps": [{"index": 0, "capability_id": "shell.command.run",
                           "args": {"argv": ["xyz"]},
                           "type_errors": ["MISSING_SLOT:output_path:PATH_OUTPUT"],
                           "result": None}],
            }
            self.assertIsNone(
                ra._try_composed("NORUN", "Run the shell command xyz q1", 0),
                "treated a type-level rejection as a command that ran",
            )
        finally:
            croute.execute_chain = original


class TestADirectoryIsARealArtifact(unittest.TestCase):
    """A path is not required to have an extension, and a directory never does.

    Two extractors in one brain disagreed about what a path is.
    goal_compiler._repo_paths found `canonical/.../sub`; the composer's own
    extract_paths required an extension and found nothing, so PATH_OUTPUT could
    not be filled and the chain refused with OPEN__COMPOSER_SLOT_UNBOUND before
    dispatching.  The narrower extractor was the one that decided whether a
    command could run.
    """

    def test_a_path_with_no_extension_is_still_a_path(self):
        from canonical.runtime import composer_route_v1 as croute
        found = croute.extract_paths(
            "Run the shell command mkdir canonical/astra_runtime/tmp/x/sub")
        self.assertIn("canonical/astra_runtime/tmp/x/sub", found)

    def test_the_parent_of_a_file_already_found_is_not_a_second_path(self):
        """Otherwise paths[-1] moves off the file and onto the folder holding it."""
        from canonical.runtime import composer_route_v1 as croute
        found = croute.extract_paths(
            "Run the shell command cp canonical/astra_runtime/tmp/x/a1.txt "
            "canonical/astra_runtime/tmp/x/b2.txt")
        self.assertEqual(found[-1], "canonical/astra_runtime/tmp/x/b2.txt")
        self.assertNotIn("canonical/astra_runtime/tmp/x", found)

    def test_a_sentence_that_already_found_its_paths_is_unchanged(self):
        from canonical.runtime import composer_route_v1 as croute
        self.assertEqual(
            croute.extract_paths("compress notes.txt into notes.txt.gz"),
            ["notes.txt", "notes.txt.gz"],
        )


class TestADirectoryTheCommandCreatedIsNotReportedMissing(unittest.TestCase):

    def test_mkdir_produces_the_directory_and_is_not_refused(self):
        base = _fresh("mkdir2")
        target = "%s/sub" % base
        result = _solve("Run the shell command mkdir %s" % target)
        self.assertTrue(
            (ROOT / target).is_dir(),
            "the directory was never created: %s" % (result.get("status"),),
        )
        self.assertIs(
            result.get("pass"), True,
            "refused a directory the command demonstrably created: %s / %s"
            % (result.get("status"), result.get("failure_class")),
        )


if __name__ == "__main__":
    unittest.main()
