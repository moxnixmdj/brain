"""A controller run that ended because the task was already complete must say so.

canonical/runtime/astra_runtime.py raised Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH")
for two different situations, only one of which is a plan without a finish step.  When the controller
checkpoint says the task already ran to the end, the cycle loop never executes because start_cycle is
already past the last action, so control falls through to the same raise.  The plan DID have a finish
step; it was reached on an earlier run.

The code therefore reported a false reason, and the cost was measured: scoring extended-goal
acceptance by reusing one task_id per goal produced 0 of 14 with seven goals blocked on
MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH, which reads as half the benchmark being broken.
With a fresh id per invocation the same goals give 7 of 14 and none of them has a missing finish
step.  canonical/tests/test_goal_compiler_world_binding_v1.py::_clear_runtime_state already
documents the behaviour and deletes its checkpoint to work around it; it could not say more because
the code it was handed could not.
"""

import pathlib
import shutil
import sys
import unittest
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "canonical" / "runtime"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

FINISHED = "MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED"
NO_FINISH = "MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH"
GOAL = "Create an xlsx table from JSON records."
STATE = ROOT / "canonical" / "astra_runtime" / "state"


class FinishedTaskReportsItselfTests(unittest.TestCase):
    """The blocker code must name the reason the run actually ended."""

    def setUp(self) -> None:
        self.task_id = "CTRLFIN_" + uuid.uuid4().hex[:12]
        self._created = []

    def tearDown(self) -> None:
        # Remove only this test's own checkpoints: the state dir holds tracked files.
        for path in self._created:
            if path.exists():
                path.unlink()

    def _record(self) -> None:
        for path in STATE.glob(self.task_id + "*"):
            if path not in self._created:
                self._created.append(path)

    def _run(self):
        from canonical.runtime import live_integrated_brain_v1 as lb

        result = lb.run_raw_goal({"task_id": self.task_id, "goal": GOAL})
        self._record()
        return result

    def test_first_run_executes_and_the_second_reports_already_finished(self):
        first = self._run()
        # The plan must genuinely reach a finish on the first run, otherwise the second run's
        # blocker would be about something else and this test would prove nothing.
        self.assertTrue(first.get("pass"), "first run did not pass: %s" % str(first.get("reason"))[:300])
        self.assertIn("PASS__", str(first.get("status")))

        second = self._run()
        self.assertFalse(second.get("pass"))
        reason = str(second.get("reason") or "")

        # The whole point: the true reason, not the false one.
        self.assertIn(FINISHED, reason, "second run did not report ALREADY_FINISHED: %s" % reason[:300])
        self.assertNotIn(NO_FINISH, reason, "second run still reports a missing finish step: %s" % reason[:300])

    def test_a_fresh_task_id_is_not_refused_as_already_finished(self):
        """The fix must not turn every run into a refusal."""
        fresh = "CTRLFRESH_" + uuid.uuid4().hex[:12]
        self.task_id = fresh
        result = self._run()
        self.assertTrue(result.get("pass"), "fresh id refused: %s" % str(result.get("reason"))[:300])
        self.assertNotIn(FINISHED, str(result.get("reason") or ""))


class MechanismTests(unittest.TestCase):
    """Pin the branch condition itself, not only its end-to-end symptom."""

    def test_the_branch_reads_state_the_function_already_had(self):
        source = (ROOT / "canonical" / "runtime" / "astra_runtime.py").read_text(encoding="utf-8")
        self.assertIn('raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED")', source)
        # It must be conditioned on the resume having consumed the whole plan, not unconditional.
        self.assertIn("if resumed and start_cycle>=len(actions):", source)
        # And the honest code must still exist for a plan that really has no finish.
        self.assertIn('raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH")', source)

    def test_the_already_finished_branch_precedes_the_generic_raise(self):
        source = (ROOT / "canonical" / "runtime" / "astra_runtime.py").read_text(encoding="utf-8")
        self.assertLess(
            source.index('raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED")'),
            source.index('raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH")'),
            "the specific reason must be raised before the generic one, or it is unreachable",
        )


if __name__ == "__main__":
    unittest.main()
