from __future__ import annotations

from unittest.mock import patch
import unittest

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


def _failed_decision_wrapper(*, durable_retry: bool = True):
    learning = None
    if durable_retry:
        learning = {
            "pass": False,
            "diagnosis": {
                "failure_fingerprint": "fp:auto-one-shot",
            },
            "retry_capsule_sha256": "a" * 64,
            "improvement_work_id": "work:auto-one-shot",
        }
    return {
        "schema": "PROJECT_BRAIN_UNIFIED_LIVE_RUNTIME_V1",
        "status": "UNIFIED_DECISION_EXECUTION_COMPLETE",
        "pass": False,
        "decision_output": {
            "pass": False,
            "status": "OPEN__NO_CURRENTLY_CERTIFIED_ADEQUATE_POLICY_COVER",
            "r2_fixed_point_status": "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
            "r2_meta_action": "REPAIR_OR_EXPAND_VERIFIABLE_ADEQUACY_COVER",
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
        },
        "learning": learning,
        "terminal_authority": False,
    }


def _successful_replay():
    return {
        "schema": "PROJECT_BRAIN_UNIFIED_LIVE_RUNTIME_V1",
        "status": "UNIFIED_DECISION_EXECUTION_COMPLETE",
        "pass": True,
        "decision_output": {
            "pass": True,
            "status": "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
            "r2_meta_action": "RETURN_VERIFIED_RESULT",
            "actual_goal_satisfaction_verified": True,
            "semantic_acceptance_complete": True,
            "terminal_authority": False,
        },
        "learning": None,
        "terminal_authority": False,
    }


class UnifiedCognitiveFabricOneShotAutoDefaultV1Tests(unittest.TestCase):
    def _request(self, **options):
        return {
            "mode": "AUTO",
            "payload": {
                "task_id": "AUTO-ONE-SHOT-001",
                "goal": "Do the adequate thing.",
            },
            "options": options,
        }

    def test_auto_decision_gap_uses_one_shot_and_accepts_only_safe_original_replay(self):
        events = []
        repair_receipt = {
            "schema": "PROJECT_BRAIN_UNIFIED_LIVE_RUNTIME_V1",
            "status": "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY",
            "pass": True,
            "original_replay": _successful_replay(),
            "terminal_authority": False,
        }

        def drain(**kwargs):
            events.append("drain")
            return {
                "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
                "terminal_authority": False,
            }

        def one_shot(**kwargs):
            events.append("one_shot")
            provider = kwargs["failure_repair_provider"]
            self.assertIsNotNone(provider)
            observed = provider({
                "payload": {
                    "failure_fingerprint": "fp:auto-one-shot",
                    "retry_capsule_sha256": "a" * 64,
                }
            })
            self.assertTrue(observed["pass"])
            return {
                "schema": "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V2",
                "status": "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
                "pass": True,
                "fixed_point": True,
                "terminal_authority": False,
            }

        with (
            patch.object(fabric.live_runtime, "run", return_value=_failed_decision_wrapper()),
            patch.object(fabric.improvement_driver, "drain", side_effect=drain),
            patch.object(
                fabric.live_runtime,
                "execute_failure_repair_cycle",
                return_value=repair_receipt,
            ) as repair_cycle,
            patch.object(fabric.one_shot_reality_closure, "run", side_effect=one_shot) as closure,
        ):
            out = fabric.run(self._request())

        self.assertEqual(events, ["drain", "one_shot"])
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["actual_goal_satisfaction_verified"])
        self.assertTrue(out["auto_one_shot"]["attempted"])
        self.assertTrue(out["auto_one_shot"]["recovered_by_original_replay"])
        self.assertEqual(
            out["auto_one_shot"]["closure_status"],
            "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
        )
        self.assertEqual(closure.call_count, 1)
        self.assertEqual(repair_cycle.call_count, 1)

    def test_closure_success_without_original_replay_never_upgrades_task_success(self):
        with (
            patch.object(fabric.live_runtime, "run", return_value=_failed_decision_wrapper()),
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                },
            ),
            patch.object(
                fabric.one_shot_reality_closure,
                "run",
                return_value={
                    "schema": "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V2",
                    "status": "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
                    "pass": True,
                    "fixed_point": True,
                    "terminal_authority": False,
                },
            ),
        ):
            out = fabric.run(self._request())

        self.assertFalse(out["inner_pass"], out)
        self.assertFalse(out["result"]["pass"])
        self.assertTrue(out["auto_one_shot"]["attempted"])
        self.assertFalse(out["auto_one_shot"]["recovered_by_original_replay"])

    def test_no_durable_retry_capsule_means_no_automatic_one_shot(self):
        with (
            patch.object(
                fabric.live_runtime,
                "run",
                return_value=_failed_decision_wrapper(durable_retry=False),
            ),
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                },
            ),
            patch.object(fabric.one_shot_reality_closure, "run") as closure,
        ):
            out = fabric.run(self._request())

        self.assertFalse(out["inner_pass"])
        self.assertFalse(out["auto_one_shot"]["attempted"])
        self.assertEqual(
            out["auto_one_shot"]["reason"],
            "CURRENT_TASK_DURABLE_RETRY_BINDING_REQUIRED",
        )
        closure.assert_not_called()

    def test_explicit_decision_mode_does_not_enable_auto_default(self):
        request = self._request()
        request["mode"] = "ADEQUATE_DECISION"
        with (
            patch.object(fabric.live_runtime, "run", return_value=_failed_decision_wrapper()),
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                },
            ),
            patch.object(fabric.one_shot_reality_closure, "run") as closure,
        ):
            out = fabric.run(request)

        self.assertFalse(out["auto_one_shot"]["attempted"])
        self.assertEqual(out["auto_one_shot"]["reason"], "AUTO_ROUTE_REQUIRED")
        closure.assert_not_called()

    def test_auto_one_shot_can_be_disabled_per_request(self):
        with (
            patch.object(fabric.live_runtime, "run", return_value=_failed_decision_wrapper()),
            patch.object(
                fabric.improvement_driver,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                },
            ),
            patch.object(fabric.one_shot_reality_closure, "run") as closure,
        ):
            out = fabric.run(self._request(auto_one_shot=False))

        self.assertFalse(out["auto_one_shot"]["attempted"])
        self.assertEqual(out["auto_one_shot"]["reason"], "DISABLED_BY_REQUEST")
        closure.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
