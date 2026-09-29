#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class AntiDriftIntegrationWiringTests(unittest.TestCase):
    def test_astra_runtime_is_guarded_at_all_execution_choke_points(self):
        text=(ROOT/"canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "from anti_drift_interlock import authorize_action_from_env, authorize_step_from_env, require_runtime_context",
            text,
        )
        self.assertIn("def _goal_action(action):\n    authorize_action_from_env(ROOT, action)", text)
        self.assertIn(
            "def execute_step(step, prior_results=None, mission=None):\n    authorize_step_from_env(ROOT, step)",
            text,
        )
        self.assertIn("a=ap.parse_args()\n    require_runtime_context(ROOT)", text)

    def test_supervisor_binds_tasks_before_claim_and_before_execution(self):
        text=(ROOT/"canonical/runtime/same_identity_supervisor.py").read_text(encoding="utf-8")
        self.assertIn(
            "from anti_drift_interlock import DriftDenied, authorize_task, binding_environment",
            text,
        )
        self.assertIn(
            "task = _validate_task(_read_json(task_path), agent_id)\n    authorize_task(root, task)",
            text,
        )
        self.assertIn(
            "binding = authorize_task(root, task)\n    state_path = _state_path",
            text,
        )
        self.assertIn("env.update(binding_environment(binding))", text)
        self.assertIn("except (SupervisorError, DriftDenied) as exc:", text)

    def test_no_wildcard_authority_is_encoded_in_interlock(self):
        text=(ROOT/"canonical/runtime/anti_drift_interlock.py").read_text(encoding="utf-8")
        self.assertIn('if any(x == "*" for x in out):', text)
        self.assertIn('raise DriftDenied(code + "_WILDCARD_FORBIDDEN")', text)


if __name__ == "__main__":
    unittest.main()
