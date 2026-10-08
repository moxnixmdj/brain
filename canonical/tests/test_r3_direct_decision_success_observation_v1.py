from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_runtime_v1 as live


class R3DirectDecisionSuccessObservationV1Tests(unittest.TestCase):
    def _direct_success(self):
        return {
            "schema": "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "pass": True,
            "r2_fixed_point_status": "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "terminal_authority": False,
        }

    def test_verified_direct_r2_success_is_observed_by_r3(self):
        learned = {
            "schema": "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1",
            "status": "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
            "pass": True,
            "permanent_reuse_authorized": False,
        }
        with (
            patch.object(live, "_decision_run", return_value=self._direct_success()),
            patch.object(
                live,
                "_observe_runtime_outcome",
                return_value=learned,
            ) as observe,
        ):
            out = live.run_decision(
                {"task_id": "direct-r3-observe", "goal": "bounded direct goal"},
                learn=True,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(out["learning"], learned)
        observe.assert_called_once()
        observed = observe.call_args.args[0]
        self.assertTrue(observed["pass"])
        self.assertEqual(
            observed["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        )
        self.assertEqual(
            observe.call_args.kwargs["surface"],
            "ADEQUATE_DECISION_DIRECT_SUCCESS",
        )
        retry = observe.call_args.kwargs["retry_context"]
        self.assertEqual(retry["mode"], "decision")
        self.assertEqual(retry["request"]["task_id"], "direct-r3-observe")
        self.assertTrue(retry["learn"])

    def test_learn_false_does_not_observe_direct_success(self):
        with (
            patch.object(live, "_decision_run", return_value=self._direct_success()),
            patch.object(live, "_observe_runtime_outcome") as observe,
        ):
            out = live.run_decision(
                {"task_id": "direct-r3-no-learn", "goal": "bounded direct goal"},
                learn=False,
            )

        self.assertTrue(out["pass"], out)
        self.assertIsNone(out["learning"])
        observe.assert_not_called()

    def test_non_direct_success_without_inner_learning_keeps_prior_behavior(self):
        nondirect = dict(self._direct_success())
        nondirect["r2_fixed_point_status"] = "PASS__R2_ADAPTIVE_FIXED_POINT_CLOSED"
        with (
            patch.object(live, "_decision_run", return_value=nondirect),
            patch.object(live, "_observe_runtime_outcome") as observe,
        ):
            out = live.run_decision(
                {"task_id": "nondirect-no-duplicate", "goal": "bounded goal"},
                learn=True,
            )

        self.assertTrue(out["pass"], out)
        self.assertIsNone(out["learning"])
        observe.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
