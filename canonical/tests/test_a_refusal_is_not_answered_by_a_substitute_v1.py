# PROJECT_BRAIN
"""A refusal is not answered by a substitute; an edit promise is not discharged by reading.

Two laws, both already stated somewhere in this repository, wired where they were
missing.  Measured on 32a73a0 (main), which is the commit these pins are written
against.

LAW 1 -- composition asks the sentence first.
    The door refuses a sentence for two reasons: no single capability matches
    (`GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH`) or the matched capability
    could not be admitted.  Three sites then asked the composer, and only one of
    them required anything of the sentence.  So a refusal was answered by a
    chain the request never asked for, and the verdict named a failure of the
    SUBSTITUTE's promise instead of the refusal that had really happened.

    Over the 28-row surface census: 19 sentences reached the composer, 18 had
    been refused a moment earlier, and none of the 18 was a pass.  The condition
    is not new; it is the one the route-admission site already applied --
    the sentence must state a command line, or a payload together with where it
    goes.  "Check the file X" states neither and keeps failing closed (#6119).

LAW 2 -- an edit promise is a promise, whatever verb carries it.
    `promised_source_change_errors` already refused to call a run a pass when a
    source file the sentence asked to have changed was byte-identical
    afterwards, but it only recognised repair|fix|patch|correct as asking.
    "Add a parameter qty ... and update every caller" asks in the same sense,
    and was answered by a symbol INDEXER: the door reported PASS with the
    fixture's one-argument `line_total` untouched, so the call the sentence
    described raised TypeError.  Measured: `add_parameter`, a false pass.

    Destructive verbs are deliberately NOT in the widened set: "delete X.py"
    promises X is gone, and "still readable and different" is the wrong test for
    it -- covered instead by the promised-artifact law and NAMED_INPUT_REMOVED.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402


class TestTheSentenceDecidesWhetherAChainMayAnswerIt(unittest.TestCase):
    def test_a_stated_command_line_is_grounded(self):
        goal = 'Run the shell command "printf hello"'
        self.assertTrue(door._states_an_executable_form(goal))
        self.assertIsNotNone(door.composer_route.extract_argv(goal))

    def test_a_payload_with_its_destination_is_grounded(self):
        goal = "Write the text 'PROJECT BRAIN' to the file notes/out.txt"
        self.assertTrue(door._states_an_executable_form(goal))

    def test_a_payload_without_a_destination_is_not_grounded(self):
        # The #6119 shape: the only path in the sentence would become the
        # destination by default and a file would be overwritten by a report
        # about it.
        self.assertFalse(door._states_an_executable_form("Check the file canonical/AGENTS.md"))

    def test_a_question_is_not_an_executable_form(self):
        # A sentence that says where its answer goes states a payload and a
        # destination, and IS grounded -- it is a write.  What must not be
        # grounded is a question that states neither.
        for goal in ("Which function in canonical/runtime is never executed by the tests in canonical/tests?",
                     "Would the tests in canonical/tests pass if the deprecated inspect API were replaced?"):
            self.assertFalse(door._states_an_executable_form(goal), goal)

    def test_every_composition_site_asks_the_same_question(self):
        """One condition, three sites.  A site that composes unguarded is the bug."""
        source = (ROOT / "canonical/runtime/live_brain_route_admission_v1.py").read_text(encoding="utf-8")
        for call in ('composed = (_try_composed(task_id, goal, started)\n'
                     '                    if _states_an_executable_form(',
                     'if _states_an_executable_form(normalized, admission):'):
            self.assertIn(call, source)
        # The unguarded shape that answered compiler refusals must be gone.
        self.assertNotIn("gap_future_artifacts = _future_artifacts(gap_normalized)\n"
                         "        composed = _try_composed(task_id, goal, started)",
                         source)


class TestAnEditPromiseIsServedByAChange(unittest.TestCase):
    PY = "canonical/astra_runtime/tmp/pin_edit_promise/app/models.py"

    @classmethod
    def setUpClass(cls):
        cls.base = ROOT / "canonical/astra_runtime/tmp/pin_edit_promise"
        (cls.base / "app").mkdir(parents=True, exist_ok=True)
        (cls.base / "app/__init__.py").write_text("", encoding="utf-8")
        (cls.base / "app/models.py").write_text(
            '"""Models."""\n\n\ndef line_total(item):\n    return item.price_cents * item.qty\n',
            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.base, ignore_errors=True)

    def test_the_promise_is_read_from_the_verb_and_the_named_file(self):
        goal = ("Add a parameter qty with a default value to the function line_total in %s "
                "and update every caller so behaviour is unchanged." % self.PY)
        self.assertEqual(door._promised_source_files(goal), [self.PY])

    def test_the_old_verbs_still_promise(self):
        goal = "Repair the python source file %s so the unit tests pass." % self.PY
        self.assertEqual(door._promised_source_files(goal), [self.PY])

    def test_a_destructive_verb_does_not_promise_a_different_file(self):
        goal = "Delete %s and then report what you removed." % self.PY
        self.assertEqual(door._promised_source_files(goal), [])

    def test_an_unchanged_source_fails_the_promise_and_a_changed_one_does_not(self):
        goal = ("Add a parameter qty with a default value to the function line_total in %s "
                "and update every caller so behaviour is unchanged." % self.PY)
        digest = door._source_digest(self.PY)
        self.assertTrue(digest)
        unchanged = door.promised_source_change_errors(goal, {self.PY: digest}, [])
        self.assertEqual(len(unchanged), 1)
        self.assertTrue(unchanged[0].startswith("PROMISED_SOURCE_UNCHANGED"), unchanged[0])
        # A run that really changed the file discharges the same promise.
        path = ROOT / self.PY
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original + "\n\ndef other():\n    return 1\n", encoding="utf-8")
            self.assertEqual(door.promised_source_change_errors(goal, {self.PY: digest}, []), [])
        finally:
            path.write_text(original, encoding="utf-8")

    def test_a_read_only_request_promises_nothing_about_source(self):
        goal = "Count the function and class definitions in %s and write the number to %s/answer.json" % (
            "canonical/astra_runtime/tmp/pin_edit_promise/app", "canonical/astra_runtime/tmp/pin_edit_promise")
        self.assertEqual(door._promised_source_files(goal), [])


if __name__ == "__main__":
    unittest.main()
