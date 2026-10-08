from __future__ import annotations

import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_direct_adequacy_success_adapter_v1 as adapter
from canonical.runtime import r3_direct_adequacy_readback_verifier_v1 as verifier
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


class R3DirectAdequacyLearningV1Tests(unittest.TestCase):
    def direct_output(self, goal: str):
        return {
            "schema": "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V1",
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "pass": True,
            "route_id": "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
            "capability_id": None,
            "selected_policy_id": "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "semantic_scope": "STRICT_REPLY_OR_RESPOND_WITH_EXACTLY_LITERAL_GOAL_ONLY",
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": ["RAWREQ:0"],
            "raw_acceptance_obligation_count": 1,
            "acceptance_receipt": {
                "pass": True,
                "semantic_acceptance_complete": True,
                "actual_goal_satisfaction_verified": True,
                "accepted_obligation_ids": ["RAWREQ:0"],
            },
            "raw_result": {
                "pass": True,
                "raw_goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            },
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": "EXACT_LITERAL_ONLY",
        }

    def test_direct_success_gets_proof_capsule_without_controller_checkpoint(self):
        goal = 'Reply with exactly "ok"'
        capsule = learning._make_success_proof_capsule(self.direct_output(goal))
        self.assertIsNotNone(capsule)
        self.assertEqual(
            capsule["material"]["proof_kind"],
            "R2_DIRECT_ADEQUACY_READBACK_V1",
        )
        self.assertEqual(
            capsule["material"]["route_id"],
            "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
        )

    def test_direct_success_adapts_to_candidate_without_effect_replay(self):
        goal = 'Reply with exactly "ok"'
        capsule = learning._make_success_proof_capsule(self.direct_output(goal))
        request = {
            "observation": {"proof_capsule": capsule},
            "replay_context": {
                "request": {"task_id": "direct-1", "goal": goal},
            },
        }
        out = adapter.adapt(request, repo_root=Path("."))
        self.assertIsNotNone(out)
        self.assertTrue(out["solver_output"]["pass"])
        self.assertFalse(out["execution_replayed"])
        self.assertEqual(
            out["problem"]["verification_kind"],
            "R2_DIRECT_ADEQUACY_READBACK_V1",
        )

    def test_exact_literal_readback_reverifies_without_direct_execution(self):
        goal = 'Reply with exactly "ok"'
        material = learning._make_success_proof_capsule(
            self.direct_output(goal)
        )["material"]
        problem = {
            "verification_kind": "R2_DIRECT_ADEQUACY_READBACK_V1",
            "raw_request": {"task_id": "direct-2", "goal": goal},
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "route_id": "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
            "retained_direct_proof": material,
        }
        with mock.patch.object(
            verifier.direct,
            "preflight",
            return_value={
                "matched": True,
                "route_id": verifier.direct.EXACT_LITERAL_ROUTE_ID,
                "goal_sha256": problem["goal_sha256"],
            },
        ), mock.patch.object(
            verifier.literal_acceptance,
            "verify",
            return_value={
                "pass": True,
                "semantic_acceptance_complete": True,
                "actual_goal_satisfaction_verified": True,
                "accepted_obligation_ids": ["RAWREQ:0"],
            },
        ):
            out = verifier.verify_material(
                problem=problem,
                episode={},
                trace=[],
                fact_capsule_head_hash="a" * 64,
                value_capsule_head_hash="b" * 64,
                repo_root=Path("."),
            )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["execution_replayed"])
        self.assertTrue(out["producer_independent_readback"])

    def test_direct_adapter_and_verifier_are_part_of_owned_frontier(self):
        self.assertIn(
            "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py",
            driver.SUCCESS_ADAPTER_FRONTIER_PATHS,
        )
        self.assertIn(
            "canonical/runtime/r3_direct_adequacy_readback_verifier_v1.py",
            driver.SUCCESS_VERIFICATION_AUTHORITY_PATHS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
