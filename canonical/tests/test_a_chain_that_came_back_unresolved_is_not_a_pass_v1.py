"""A step that ran is not a step that answered.

Measured 2026-10-30 on a fresh tree, over the front door::

    goal    "Find the root cause of the failure in <pkg>/test_calc.py."
    route   terminal.tournament.failure.witness -> terminal.kstar.root.assess.stdlib
    step    {"status": "UNRESOLVED", "outcome": "UNRESOLVED",
             "missing_premises": [3 named premises], "abc_closed": false}
    answer  pass=True, PASS__COMPOSED_CAPABILITY_CHAIN, semantic_acceptance_complete=False

No diagnosis of the failing test existed anywhere in the answer.  The step is a theorem
assessment from the decision family and it came back UNRESOLVED -- but every step returned a dict,
so ``execute_chain`` wrote ``PASS__COMPOSER_CHAIN_EXECUTED``, and the door lifted that to
``PASS__COMPOSED_CAPABILITY_CHAIN``.  The one thing the record proved was that the step did *not*
resolve, and that is exactly what the report left out.

Two rules are pinned here, because either one alone is not enough:

  * the composer's verdict is the last step's verdict -- a negative outcome, named missing
    premises, or an explicitly unverified output is a refusal, not a pass;
  * a refusal keeps the composer's own name for what happened.  Every non-passing chain used to
    be relabelled ``STEP_RAISED_OUTCOME_UNKNOWN`` ("a step raised, nobody knows what the world
    looks like"), which was false here: nothing raised, and the world was known to be *unsolved*.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = "canonical/astra_runtime/tmp/test_chain_unresolved"

SOURCE = ("def add(a, b):\n    return a - b\n")
TEST = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n")


def _fresh() -> str:
    base = pathlib.Path(WORK)
    shutil.rmtree(ROOT / base, ignore_errors=True)
    (ROOT / base / "pkg").mkdir(parents=True)
    (ROOT / base / "pkg" / "calc.py").write_text(SOURCE, encoding="utf-8")
    (ROOT / base / "pkg" / "test_calc.py").write_text(TEST, encoding="utf-8")
    return WORK


class AStepThatCouldNotAnswerIsNotAPass(unittest.TestCase):

    def test_an_unresolved_outcome_is_read_as_no_answer(self):
        self.assertEqual(composer._step_says_no_answer({"outcome": "UNRESOLVED"}),
                         "outcome=UNRESOLVED")

    def test_named_missing_premises_are_read_as_no_answer(self):
        self.assertEqual(composer._step_says_no_answer({"missing_premises": ["p1", "p2"]}),
                         "missing_premises=2")

    def test_an_explicitly_unverified_output_is_read_as_no_answer(self):
        self.assertEqual(composer._step_says_no_answer({"output_verified": False}),
                         "output_verified=false")

    def test_a_declared_absence_is_an_answer_not_an_unverified_output(self):
        """`rm` reports output_verified=false because the output is GONE. That is the promise."""
        self.assertIsNone(composer._step_says_no_answer(
            {"output_verified": False, "output_absent_after_run": True,
             "returncode": 0, "argv": ["rm", "x"]}))

    def test_a_step_that_answered_is_not_touched(self):
        for observed in ({"status": "OK", "output_verified": True},
                         {"missing_premises": []},
                         {"output_path": "x.json", "output_sha256": "ab"},
                         None, "raw stdout"):
            self.assertIsNone(composer._step_says_no_answer(observed), observed)

    def test_a_chain_whose_last_step_says_unresolved_does_not_pass(self):
        base = _fresh()
        executed = composer.execute_chain(
            ["terminal.kstar.root.assess.stdlib"],
            "Find the root cause of the failure in %s/pkg/test_calc.py." % base)
        self.assertIs(executed.get("pass"), False)
        self.assertEqual(executed.get("status"), "FAIL_CLOSED__COMPOSED_STEP_UNRESOLVED")
        self.assertEqual(executed.get("failure_class"), "COMPOSED_STEP_UNRESOLVED")
        self.assertIn("UNRESOLVED", str((executed.get("failed_step") or {}).get("reason")))
        # The evidence stays in the record: a refusal must still say what the step produced.
        self.assertTrue((executed.get("steps") or [{}])[0].get("result"))

    def test_the_door_keeps_the_composers_name_for_the_failure(self):
        base = _fresh()
        result = door.solve({"task_id": "chain_unresolved",
                             "goal": "Find the root cause of the failure in %s/pkg/test_calc.py."
                                     % base})
        self.assertIsNot(result.get("pass"), True)
        status = str(result.get("status") or "")
        self.assertNotIn("PASS__", status)
        self.assertIn(str(result.get("failure_class") or ""),
                      ("COMPOSED_STEP_UNRESOLVED", "STEP_RAISED_OUTCOME_UNKNOWN",
                       "STATED_ANSWER_NOT_PROVIDED", "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
                       "COMPOSED_CHAIN_NOT_VERIFIED", "NAMED_INPUT_REMOVED", ""))


if __name__ == "__main__":
    unittest.main()
