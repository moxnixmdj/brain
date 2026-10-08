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
        self.assertIsNotNone(
            drain.call_args.kwargs["verification_frontier_acquisition_provider"]
        )
        self.assertEqual(
            drain.call_args.kwargs["verification_frontier_acquisition_provider_id"],
            "ROOT1_DEFAULT_ACQUISITION_PROVIDER_V1",
        )

    def test_normal_dispatch_auto_drains_episode_compounding_when_verifier_exists(self):
        verifier = object()
        skill_verifier = object()
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
                skill_verification_provider=skill_verifier,
                success_episode_adapter_provider=adapter,
            )
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["compounding_tick"], tick)
        self.assertEqual(
            out["episode_compounding_tick"]["status"],
            "MERGED_INTO_UNIFIED_COMPOUNDING_TICK",
        )
        drain.assert_called_once()
        kwargs = drain.call_args.kwargs
        self.assertIs(kwargs["episode_verification_provider"], verifier)
        self.assertIs(kwargs["success_episode_adapter_provider"], adapter)
        self.assertIs(kwargs["skill_verification_provider"], skill_verifier)
        self.assertIsNone(kwargs["failure_repair_provider"])
        self.assertEqual(kwargs["max_actions"], 2)

    def test_frontier_acquisition_provider_reaches_driver(self):
        provider = object()
        fake = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        with mock.patch.object(
            fabric.improvement_driver,
            "drain",
            return_value=fake,
        ) as drain:
            fabric.run(
                {"mode": "IMPROVEMENT_CYCLE", "payload": {}, "options": {}},
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="root1-worker-v1",
            )
        self.assertIs(
            drain.call_args.kwargs["verification_frontier_acquisition_provider"],
            provider,
        )
        self.assertEqual(
            drain.call_args.kwargs[
                "verification_frontier_acquisition_provider_id"
            ],
            "root1-worker-v1",
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
