from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class R3DirectExperienceTotalityV1Tests(unittest.TestCase):
    def _tick(self):
        return {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }

    def test_direct_mode_set_covers_non_r3_execution_surfaces(self):
        self.assertEqual(
            fabric.R3_DIRECT_EXPERIENCE_MODES,
            {
                "P3",
                "H100_INFERENCE",
                "MYSTERY_INFERENCE",
                "UNIVERSAL_ESCAPE",
                "CERTIFIED_ROUTE",
                "LIVE_CAPABILITY",
                "BOUND_CAPABILITY",
            },
        )
        self.assertNotIn("LIVE_COMPOSITION", fabric.R3_DIRECT_EXPERIENCE_MODES)
        self.assertNotIn("LEARNING_EPISODE", fabric.R3_DIRECT_EXPERIENCE_MODES)
        self.assertNotIn("ADAPTIVE_SOLVER", fabric.R3_DIRECT_EXPERIENCE_MODES)

    def test_direct_success_is_observed_once_before_compounding_without_payload_leak(self):
        raw = {
            "pass": True,
            "status": "PASS__DIRECT",
            "schema": "DIRECT_SCHEMA",
            "failure_class": None,
            "capability_id": "cap.direct",
            "private_payload": {"secret_like": "must-not-be-copied"},
        }
        learned = {
            "status": "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
            "pass": True,
            "permanent_reuse_authorized": False,
        }
        with (
            patch.object(fabric.p3, "evaluate", return_value=raw),
            patch.object(
                fabric.live_runtime,
                "observe_runtime_outcome",
                return_value=learned,
            ) as observe,
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=self._tick(),
            ) as drain,
        ):
            out = fabric.run({"mode": "P3", "payload": {}, "options": {}})

        self.assertTrue(out["direct_experience_observed"], out)
        self.assertEqual(out["direct_learning"], learned)
        observe.assert_called_once()
        observation = observe.call_args.args[0]
        self.assertTrue(observation["pass"])
        self.assertEqual(observation["source_mode"], "P3")
        self.assertEqual(observation["capability_id"], "cap.direct")
        self.assertIn("private_payload", observation["source_key_set"])
        self.assertNotIn("private_payload", {k for k in observation if k != "source_key_set"})
        self.assertNotIn("must-not-be-copied", repr(observation))
        self.assertEqual(
            observe.call_args.kwargs["surface"],
            "UNIFIED_FABRIC_DIRECT_P3",
        )
        drain.assert_called_once()

    def test_direct_failure_is_causal_experience_not_silently_dropped(self):
        raw = {
            "pass": False,
            "status": "FAIL__DIRECT",
            "failure_class": "DIRECT_FAILURE",
            "reason": "bounded failure",
        }
        learned = {
            "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
            "pass": False,
            "permanent_reuse_authorized": False,
        }
        with (
            patch.object(fabric.p3, "evaluate", return_value=raw),
            patch.object(
                fabric.live_runtime,
                "observe_runtime_outcome",
                return_value=learned,
            ) as observe,
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=self._tick(),
            ),
        ):
            out = fabric.run({"mode": "P3", "payload": {}, "options": {}})

        self.assertTrue(out["direct_experience_observed"], out)
        observation = observe.call_args.args[0]
        self.assertFalse(observation["pass"])
        self.assertEqual(observation["failure_class"], "DIRECT_FAILURE")
        self.assertNotIn("reason", observation)

    def test_learn_false_disables_direct_observation(self):
        with (
            patch.object(
                fabric.p3,
                "evaluate",
                return_value={"pass": True, "status": "PASS__DIRECT"},
            ),
            patch.object(fabric.live_runtime, "observe_runtime_outcome") as observe,
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=self._tick(),
            ),
        ):
            out = fabric.run({
                "mode": "P3",
                "payload": {},
                "options": {"learn": False},
            })

        observe.assert_not_called()
        self.assertFalse(out["direct_experience_observed"])
        self.assertIsNone(out["direct_learning"])
        self.assertIsNone(out["direct_learning_error"])

    def test_observation_failure_is_visible_and_does_not_mint_learning_credit(self):
        with (
            patch.object(
                fabric.p3,
                "evaluate",
                return_value={"pass": True, "status": "PASS__DIRECT"},
            ),
            patch.object(
                fabric.live_runtime,
                "observe_runtime_outcome",
                side_effect=RuntimeError("observer unavailable"),
            ),
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=self._tick(),
            ),
        ):
            out = fabric.run({"mode": "P3", "payload": {}, "options": {}})

        self.assertFalse(out["direct_experience_observed"])
        self.assertIsNone(out["direct_learning"])
        self.assertIn("RuntimeError:observer unavailable", out["direct_learning_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
