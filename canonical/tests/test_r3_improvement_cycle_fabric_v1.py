from __future__ import annotations

import unittest
from unittest import mock

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class R3ImprovementCycleFabricTests(unittest.TestCase):
    def test_canonical_fabric_exposes_improvement_cycle(self):
        fake = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        with mock.patch.object(fabric.improvement_driver, "drain", return_value=fake) as drain:
            out = fabric.run(
                {
                    "mode": "IMPROVEMENT_CYCLE",
                    "payload": {},
                    "options": {"max_improvement_actions": 3},
                }
            )
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["mode"], "IMPROVEMENT_CYCLE")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"], fake)
        drain.assert_called_once()
        self.assertEqual(drain.call_args.kwargs["max_actions"], 3)

    def test_normal_dispatch_auto_drains_episode_compounding_when_verifier_exists(self):
        verifier = object()
        adapter = object()
        tick = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        with (
            mock.patch.object(
                fabric,
                "execute_bound",
                return_value={"pass": True, "status": "BOUND_OK"},
            ),
            mock.patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=tick,
            ) as drain,
        ):
            out = fabric.run(
                {
                    "mode": "BOUND_CAPABILITY",
                    "payload": {"capability_id": "cap.test", "inputs": {}},
                    "options": {"self_improvement_max_actions": 2},
                },
                episode_verification_provider=verifier,
                success_episode_adapter_provider=adapter,
            )
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["episode_compounding_tick"], tick)
        drain.assert_called_once()
        kwargs = drain.call_args.kwargs
        self.assertIs(kwargs["episode_verification_provider"], verifier)
        self.assertIs(kwargs["success_episode_adapter_provider"], adapter)
        self.assertIsNone(kwargs["skill_verification_provider"])
        self.assertIsNone(kwargs["failure_repair_provider"])
        self.assertEqual(kwargs["max_actions"], 2)

    def test_normal_dispatch_auto_revisits_safe_pending_repair_when_authority_exists(self):
        expander = object()
        component = {"id": "repairer"}
        tick = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        repaired = {
            "pass": False,
            "status": "AUTONOMOUS_REPAIR_BLOCKED__REPLAY_NOT_PROVED_SAFE",
        }
        with (
            mock.patch.object(
                fabric,
                "execute_bound",
                return_value={"pass": True, "status": "BOUND_OK"},
            ),
            mock.patch.object(
                fabric.improvement_driver,
                "drain",
                return_value=tick,
            ) as drain,
            mock.patch.object(
                fabric.live_runtime,
                "execute_failure_repair_cycle",
                return_value=repaired,
            ) as repair_cycle,
        ):
            out = fabric.run(
                {
                    "mode": "BOUND_CAPABILITY",
                    "payload": {"capability_id": "cap.test", "inputs": {}},
                    "options": {
                        "repair_components": [component],
                        "self_improvement_max_actions": 2,
                    },
                },
                capability_expander=expander,
            )

        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["episode_compounding_tick"], tick)
        kwargs = drain.call_args.kwargs
        self.assertIsNotNone(kwargs["failure_repair_provider"])
        self.assertEqual(kwargs["max_actions"], 2)

        provider = kwargs["failure_repair_provider"]
        provider(
            {
                "payload": {
                    "failure_fingerprint": "fp:pending",
                    "retry_capsule_sha256": "retry:pending",
                }
            }
        )
        request = repair_cycle.call_args.args[0]
        self.assertEqual(request["failure_fingerprint"], "fp:pending")
        self.assertEqual(request["retry_capsule_sha256"], "retry:pending")
        self.assertEqual(request["components"], [component])
        self.assertTrue(request["autonomous"])
        self.assertIs(
            repair_cycle.call_args.kwargs["capability_expander"],
            expander,
        )

    def test_success_adapter_provider_reaches_driver(self):
        adapter = object()
        fake = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        with mock.patch.object(fabric.improvement_driver, "drain", return_value=fake) as drain:
            fabric.run(
                {"mode": "IMPROVEMENT_CYCLE", "payload": {}, "options": {}},
                success_episode_adapter_provider=adapter,
            )
        self.assertIs(
            drain.call_args.kwargs["success_episode_adapter_provider"],
            adapter,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
