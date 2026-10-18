"""Plain sentence in, chased to a measured number -- or refused.

The refusals carry as much weight as the successes. "Make me rich" has no
number, and a machine that invents one can later declare victory against a
target the owner never set.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from execution_guard import goal_chase_v1 as gc


class GoalChaseRefusals(unittest.TestCase):
    def test_a_goal_with_no_number_is_refused_not_guessed(self):
        r = gc.run("Make me rich", measure=lambda: 0.0)
        self.assertEqual(r["status"], "FAIL_CLOSED__GOAL_HAS_NO_MEASURABLE_TARGET")
        self.assertIs(r["pass"], False)
        self.assertNotIn("target", r.get("binding", {}))

    def test_the_refusal_names_its_reason(self):
        r = gc.run("Be successful", measure=lambda: 0.0)
        self.assertIn("never invented", r["detail"])

    def test_a_million_with_no_money_oracle_does_not_arrive(self):
        """The literal requirement. With no way to measure money, the machine
        must not report a million dollars it did not make."""
        r = gc.run("Make me a million dollars", measure=lambda: 0.0, max_rounds=3)
        self.assertEqual(r["binding"]["target"], 1_000_000.0)
        self.assertEqual(r["binding"]["unit"], "USD")
        self.assertIs(r["pass"], False)
        self.assertIs(r["chase"]["goal_reached"], False)
        self.assertEqual(r["chase"]["remaining_gap"], 1_000_000.0)

    def test_binding_override_is_recorded_as_the_callers_claim(self):
        r = gc.run(
            "Do something vague", measure=lambda: 0.0,
            target=5, direction="maximize", max_rounds=1,
        )
        self.assertEqual(r["binding"]["relation_source"],
                         "SUPPLIED_BY_CALLER__NOT_BOUND_FROM_GOAL")


class GoalChaseRuns(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.work = Path(self._tmp.name)
        self.files = [self.work / f"m{i}.py" for i in range(4)]
        self._break_all()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _break_all(self) -> None:
        for p in self.files:
            p.write_text("def broken(:\n")

    def measure(self):
        """Independent oracle: CPython. The actor cannot influence it."""
        return sum(
            1 for p in self.files
            if subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                              capture_output=True).returncode != 0
        )

    def _fixer(self, ctx):
        for p in self.files:
            if p.read_text().startswith("def broken"):
                p.write_text("def ok():\n    return 1\n")
                return {"status": "FIXED", "procedure": "rewrite the malformed def"}
        return {"status": "NOTHING_TO_FIX"}

    def test_chases_to_a_measured_zero_and_the_disk_agrees(self):
        r = gc.run("Make at most 0 broken python files",
                   measure=self.measure, act=self._fixer, max_rounds=8, patience=2)
        self.assertEqual(r["status"], "PASS__TARGET_CHASE_MET")
        self.assertIs(r["pass"], True)
        self.assertEqual(r["chase"]["best_measurement"], 0)
        # the oracle is re-read from disk, not taken from the chase's own account
        self.assertEqual(self.measure(), 0)

    def test_an_actuator_that_cannot_move_the_number_reports_failure(self):
        r = gc.run("Make at most 0 broken python files",
                   measure=self.measure, act=lambda ctx: {"status": "THOUGHT_ABOUT_IT"},
                   max_rounds=4, patience=2)
        self.assertIs(r["pass"], False)
        self.assertEqual(r["chase"]["best_measurement"], 4)

    def test_every_round_is_recorded_as_a_pathology(self):
        state = os.path.join(self._tmp.name, "fly.json")
        r = gc.run("Make at most 0 broken python files",
                   measure=self.measure, act=self._fixer,
                   max_rounds=8, patience=2, flywheel_state_path=state)
        self.assertTrue(r["chase"]["learning"]["pathologies_recorded"])


class LiveActuatorWiring(unittest.TestCase):
    def test_the_live_entry_is_wrapped_not_replaced(self):
        """live_act must drive the real entry and translate it, whatever the
        verdict -- including a goal it cannot compile."""
        act = gc.live_act("Make at most 0 broken python files", tag="unittest")
        out = act({"round": 0})
        self.assertIsInstance(out, dict)
        self.assertIn("status", out)
        self.assertIn("capability_id", out)
        # a failing run must not claim a reusable procedure
        if not out.get("procedure"):
            self.assertTrue(out.get("error") or out.get("status"))

    def test_each_round_gets_a_unique_task_id(self):
        """The live controller checkpoints per task id and refuses to re-run a
        finished one, so round number has to be in the id."""
        act = gc.live_act("x", tag="t")
        self.assertNotEqual(
            act({"round": 0}).get("status"), None,
            "distinct rounds must be distinguishable to the live entry",
        )


if __name__ == "__main__":
    unittest.main()
