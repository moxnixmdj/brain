from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import live_brain_runtime_v1 as live
from canonical.runtime import r3_verified_fixed_point_driver_v1 as fixed


class DirectSuccessLearningBridgeTest(unittest.TestCase):
    def test_verified_direct_success_is_observed_for_r3_compounding(self):
        direct = {
            "schema": "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V1",
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "pass": True,
            "direct_adequacy_authority": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
        }
        observed = {
            "status": "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
            "pass": True,
        }
        with patch.object(live, "_decision_run", return_value=direct), patch.object(
            live, "_observe_runtime_outcome", return_value=observed
        ) as observe:
            result = live.run_decision(
                {"task_id": "direct-learning", "goal": "bounded direct goal"},
                learn=True,
            )

        self.assertTrue(result["pass"])
        self.assertEqual(result["learning"], observed)
        observe.assert_called_once()
        kwargs = observe.call_args.kwargs
        self.assertTrue(kwargs["learn"])
        self.assertEqual(kwargs["surface"], "R2_DIRECT_END_TO_END_ADEQUACY")
        self.assertEqual(observe.call_args.args[0], direct)

    def test_success_observation_can_be_disabled(self):
        direct = {
            "schema": "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V1",
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "pass": True,
            "direct_adequacy_authority": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
        }
        with patch.object(live, "_decision_run", return_value=direct), patch.object(
            live, "_observe_runtime_outcome"
        ) as observe:
            result = live.run_decision(
                {"task_id": "direct-no-learning", "goal": "bounded direct goal"},
                learn=False,
            )
        self.assertTrue(result["pass"])
        self.assertIsNone(result["learning"])
        observe.assert_not_called()


class VerifiedFixedPointDriverTest(unittest.TestCase):
    def test_drains_until_durable_state_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state_path.write_text('{"generation":0}\n', encoding="utf-8")
            calls = {"count": 0}

            def fake_drain(**kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    state_path.write_text('{"generation":1}\n', encoding="utf-8")
                    return {
                        "status": "IMPROVEMENT_QUEUE_ADVANCED",
                        "pass": True,
                        "progress_count": 1,
                        "next_improvement_action": {"kind": "VERIFY_EPISODE"},
                    }
                return {
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "next_improvement_action": None,
                }

            final_state = {
                "improvement_queue": {},
                "stats": {"pending_improvement_count": 0},
            }
            with patch.object(fixed.queue_driver, "drain", side_effect=fake_drain), patch.object(
                fixed.learning, "load_state", return_value=final_state
            ), patch.object(
                fixed.learning, "next_improvement_action", return_value=None
            ):
                result = fixed.run(
                    state_path=state_path,
                    repo_root=td,
                    max_rounds=4,
                    max_actions_per_round=8,
                )

        self.assertTrue(result["pass"])
        self.assertTrue(result["fixed_point"])
        self.assertEqual(result["round_count"], 2)
        self.assertEqual(calls["count"], 2)
        self.assertIsNone(result["residual_boundary"])
        self.assertFalse(result["terminal_authority"])

    def test_safety_bound_is_not_misreported_as_fixed_point(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state_path.write_text('{"generation":0}\n', encoding="utf-8")
            calls = {"count": 0}

            def fake_drain(**kwargs):
                calls["count"] += 1
                state_path.write_text(
                    json.dumps({"generation": calls["count"]}) + "\n",
                    encoding="utf-8",
                )
                return {
                    "status": "IMPROVEMENT_QUEUE_ADVANCED",
                    "pass": True,
                    "progress_count": 1,
                    "next_improvement_action": {"kind": "VERIFY_EPISODE"},
                }

            final_state = {
                "improvement_queue": {
                    "w1": {
                        "status": "PENDING",
                        "kind": "VERIFY_EPISODE",
                        "priority": 10,
                    }
                },
                "stats": {"pending_improvement_count": 1},
            }
            with patch.object(fixed.queue_driver, "drain", side_effect=fake_drain), patch.object(
                fixed.learning, "load_state", return_value=final_state
            ), patch.object(
                fixed.learning,
                "next_improvement_action",
                return_value={"kind": "VERIFY_EPISODE"},
            ):
                result = fixed.run(
                    state_path=state_path,
                    repo_root=td,
                    max_rounds=2,
                    max_actions_per_round=8,
                )

        self.assertFalse(result["pass"])
        self.assertFalse(result["fixed_point"])
        self.assertEqual(
            result["status"], "VERIFIED_R3_FIXED_POINT_SAFETY_BOUND_REACHED"
        )
        self.assertEqual(
            result["residual_boundary"],
            "CURRENT_R3_WORK_REMAINS_PENDING_OR_PROVIDER_BOUND",
        )


if __name__ == "__main__":
    unittest.main()
