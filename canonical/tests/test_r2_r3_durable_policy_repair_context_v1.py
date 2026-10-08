from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


def context(policy_id: str) -> dict:
    return {
        "schema": "PROJECT_BRAIN_R2_POLICY_REPAIR_CONTEXT_V1",
        "loop_status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
        "required_artifact": "POSITIVE_POLICY_ADEQUACY_COVERAGE",
        "selected_policy_id": None,
        "authenticated_policy_ids": [],
        "rejected_policy_candidates": [
            {"policy_id": policy_id, "reason": "ADEQUACY_BINDING_MISSING"}
        ],
        "certified_common_policies": [],
        "uncovered_model_ids": ["m0"],
        "conflicting_policy_region_witness": [],
        "selected_discriminator": None,
        "alternative_resolving_discriminators": [],
        "surviving_model_count": 1,
    }


def failure(policy_id: str) -> dict:
    return {
        "pass": False,
        "status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
        "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_COVERAGE",
        "policy_repair_context": context(policy_id),
    }


class R2R3DurablePolicyRepairContextV1Tests(unittest.TestCase):
    def test_policy_frontier_participates_in_failure_identity(self):
        a = learning._diagnose_failure(failure("BOUND_CAPABILITY_POLICY::a"))
        b = learning._diagnose_failure(failure("BOUND_CAPABILITY_POLICY::b"))
        self.assertEqual(
            a["repair_class"],
            "SYNTHESIZE_OR_AUTHENTICATE_POLICY_ADEQUACY_COVER",
        )
        self.assertEqual(
            a["policy_repair_context"],
            context("BOUND_CAPABILITY_POLICY::a"),
        )
        self.assertNotEqual(a["failure_fingerprint"], b["failure_fingerprint"])

    def test_failure_queue_persists_compact_policy_frontier(self):
        ctx = context("BOUND_CAPABILITY_POLICY::python.tests.audit.unittest")
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            out = learning.integrate_solver_output(
                {
                    "pass": False,
                    "status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
                    "next_required_edge": (
                        "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_COVERAGE"
                    ),
                    "policy_repair_context": ctx,
                },
                state_path=state_path,
                retry_context={
                    "mode": "decision",
                    "request": {"task_id": "t", "goal": "audit tests"},
                },
            )
            self.assertFalse(out["pass"])
            state = learning.load_state(state_path)
            queued = [
                row
                for row in state["improvement_queue"].values()
                if row.get("kind") == "REPAIR_FAILURE_CLASS"
            ]
            self.assertEqual(len(queued), 1)
            self.assertEqual(
                queued[0]["payload"]["policy_repair_context"],
                ctx,
            )
            rendered = repr(queued[0]["payload"]["policy_repair_context"])
            self.assertNotIn("valuation", rendered)

    def test_internal_queue_retry_forwards_persisted_context(self):
        ctx = context("BOUND_CAPABILITY_POLICY::python.tests.audit.unittest")
        work = {
            "payload": {
                "failure_fingerprint": "f" * 64,
                "retry_capsule_sha256": "r" * 64,
                "policy_repair_context": ctx,
            }
        }
        expected = {"pass": False, "status": "OPEN__REPAIR_STILL_REQUIRED"}
        with patch(
            "canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle",
            return_value=expected,
        ) as repair:
            out = driver._internal_failure_repair(
                work,
                state_path=Path("/tmp/unused-r3-state.json"),
                repo_root=driver.ROOT,
            )
        self.assertEqual(out, expected)
        request = repair.call_args.args[0]
        self.assertEqual(request["repair_context"], ctx)
        self.assertTrue(request["autonomous"])

    def test_fabric_improvement_provider_forwards_persisted_context(self):
        ctx = context("BOUND_CAPABILITY_POLICY::python.tests.audit.unittest")
        work = {
            "payload": {
                "failure_fingerprint": "f" * 64,
                "retry_capsule_sha256": "r" * 64,
                "policy_repair_context": ctx,
            }
        }

        def drain_side_effect(**kwargs):
            provider = kwargs["failure_repair_provider"]
            repaired = provider(work)
            return {
                "pass": repaired.get("pass") is True,
                "status": "TEST_DRAIN_COMPLETE",
                "progress_count": 0,
            }

        with patch.object(
            fabric.live_runtime,
            "execute_failure_repair_cycle",
            return_value={"pass": False, "status": "OPEN"},
        ) as repair, patch.object(
            fabric.improvement_driver,
            "drain",
            side_effect=drain_side_effect,
        ):
            out = fabric.run(
                {
                    "mode": "IMPROVEMENT_CYCLE",
                    "payload": {},
                    "options": {"repair_components": []},
                }
            )
        self.assertEqual(out["inner_status"], "TEST_DRAIN_COMPLETE")
        request = repair.call_args.args[0]
        self.assertEqual(request["repair_context"], ctx)

    def test_invalid_persisted_context_fails_closed_before_repair(self):
        work = {
            "payload": {
                "failure_fingerprint": "f" * 64,
                "retry_capsule_sha256": "r" * 64,
                "policy_repair_context": {"schema": "FORGED"},
            }
        }
        with patch(
            "canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle"
        ) as repair:
            with self.assertRaisesRegex(
                driver.ImprovementDriverError,
                "FAILURE_REPAIR_POLICY_CONTEXT_INVALID",
            ):
                driver._internal_failure_repair(
                    work,
                    state_path=Path("/tmp/unused-r3-state.json"),
                    repo_root=driver.ROOT,
                )
        repair.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
