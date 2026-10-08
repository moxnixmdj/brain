"""Regression contract for the live raw-goal -> existing compound controller binding."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime.live_integrated_brain_v1 import run_raw_goal


class LiveCompoundBindingTests(unittest.TestCase):
    def test_verified_compound_controller_preserves_raw_obligation(self):
        actions = [
            {"type": "read_file", "args": {"path": "canonical/README.md"}},
            {"type": "finish", "args": {"summary": "DONE"}},
        ]
        compiled = {
            "compiler_mode": "DETERMINISTIC_COMPOUND_ACTION_PLAN",
            "controller_actions": actions,
            "compiled_parts": [],
        }
        trace = [
            {"cycle": i, "plan": action, "result": {"summary": "DONE"}}
            for i, action in enumerate(actions)
        ]
        with (
            patch("canonical.runtime.live_integrated_brain_v1.goal_compiler.compile_goal", return_value=compiled),
            patch("canonical.runtime.astra_runtime._run_compiled_plain_goal", return_value={"returncode": 0, "trace": trace}) as controller,
        ):
            output = run_raw_goal({"task_id": "BIND_COMPOUND_01", "goal": "Read the canonical README and finish."})
        self.assertTrue(output["pass"], output)
        self.assertTrue(output["raw_source_coverage_complete"])
        self.assertGreaterEqual(output["raw_acceptance_obligation_count"], 1)
        self.assertFalse(output["semantic_acceptance_complete"])
        self.assertFalse(output["routing_success_authority"])
        self.assertEqual(output["terminal_credit_delta"], 0)
        self.assertEqual(output["selected_plan"], ["read_file", "finish"])
        self.assertEqual(controller.call_count, 1)

    def test_invalid_compound_action_is_rejected_before_execution(self):
        with (
            patch("canonical.runtime.live_integrated_brain_v1.goal_compiler.compile_goal", return_value={
                "controller_actions": [{"type": "read_file", "args": {}}],
            }),
            patch("canonical.runtime.astra_runtime._run_compiled_plain_goal") as controller,
        ):
            output = run_raw_goal({"task_id": "BIND_COMPOUND_BAD", "goal": "Read an input."})
        self.assertFalse(output["pass"])
        self.assertIn("COMPILED_CONTROLLER_ACTIONS_INVALID", output["reason"])
        controller.assert_not_called()

    def test_unverified_controller_result_fails_closed(self):
        actions = [{"type": "finish", "args": {"summary": "DONE"}}]
        with (
            patch("canonical.runtime.live_integrated_brain_v1.goal_compiler.compile_goal", return_value={
                "controller_actions": actions,
                "compiler_mode": "DETERMINISTIC_COMPOUND_ACTION_PLAN",
            }),
            patch("canonical.runtime.astra_runtime._run_compiled_plain_goal", return_value={
                "returncode": 0, "trace": []
            }),
        ):
            output = run_raw_goal({"task_id": "BIND_COMPOUND_UNVERIFIED", "goal": "Finish the task."})
        self.assertFalse(output["pass"])
        self.assertEqual(output["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
