from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import reached_escape_finite_totality_certificate_v1 as certificate
from canonical.runtime import reached_escape_repair_cycle_v1 as repair_cycle


def counterexample_state():
    return {
        "schema": "PROJECT_BRAIN_REACHED_ESCAPE_STATE_V1",
        "state_id": "LIVE_FABRIC_UNSPLITTABLE_COUNTEREXAMPLE_V1",
        "regions": [
            {"region_id": "r1"},
            {"region_id": "r2"},
        ],
        "policies": [
            {
                "policy_id": "p1",
                "authenticated": True,
                "safe": True,
                "adequate_region_ids": ["r1"],
            },
            {
                "policy_id": "p2",
                "authenticated": True,
                "safe": True,
                "adequate_region_ids": ["r2"],
            },
        ],
        "discriminators": [],
    }


class ReachedEscapeConstructionInvariantBoundaryV1Tests(unittest.TestCase):
    def test_live_fabric_rejects_uncertified_state_with_exact_repair(self):
        state = counterexample_state()
        with patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = fabric.run(
                {
                    "mode": "REACHED_ESCAPE_STATE",
                    "payload": state,
                    "options": {"learn": False},
                }
            )

        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertEqual(out["mode"], "REACHED_ESCAPE_STATE", out)
        self.assertFalse(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED",
            out,
        )
        self.assertFalse(out["result"]["certified_reached_state_admitted"], out)
        self.assertEqual(
            out["result"]["repair_request"]["kind"],
            "UNSPLITTABLE_EQUIVALENCE_CLASS_REPAIR",
            out,
        )
        self.assertFalse(out["result"]["terminal_authority"], out)

        cert = certificate.certify(state)
        self.assertFalse(cert["pass"], cert)
        self.assertEqual(
            cert["status"],
            "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY",
            cert,
        )
        self.assertFalse(cert["reached_state_future_outcome_totality_proved"], cert)
        self.assertFalse(cert["global_escape_progress_totality_proved"], cert)

    def test_live_fabric_admits_certified_state_and_preserves_kernel_result(self):
        state = counterexample_state()
        state["discriminators"] = [
            {
                "discriminator_id": "d1",
                "authenticated": True,
                "safe": True,
                "truthful": True,
                "complete": True,
                "outcomes": {"r1": "A", "r2": "B"},
            }
        ]
        with patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = fabric.run(
                {
                    "mode": "REACHED_ESCAPE_STATE",
                    "payload": state,
                    "options": {"learn": False},
                }
            )

        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["certified_reached_state_admitted"], out)
        self.assertTrue(
            out["result"]["reached_state_future_outcome_totality_proved"], out
        )
        self.assertEqual(
            out["result"]["kernel_result"]["status"],
            "STRICT_PROGRESS_WITH_DISCRIMINATOR",
            out,
        )
        self.assertFalse(out["result"]["terminal_authority"], out)


    def test_counterexample_is_repaired_by_exact_two_allowed_mechanism_classes(self):
        state = counterexample_state()

        with_common = {
            **state,
            "policies": [
                *state["policies"],
                {
                    "policy_id": "p_common",
                    "authenticated": True,
                    "safe": True,
                    "adequate_region_ids": ["r1", "r2"],
                },
            ],
        }
        common = certificate.certify(with_common)
        self.assertTrue(common["pass"], common)

        with_splitter = {
            **state,
            "discriminators": [
                {
                    "discriminator_id": "d1",
                    "authenticated": True,
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": {"r1": "A", "r2": "B"},
                }
            ],
        }
        split = certificate.certify(with_splitter)
        self.assertTrue(split["pass"], split)


    def test_live_fabric_can_close_uncertified_state_through_verified_repair_provider(self):
        state = counterexample_state()

        def capability_expander(request):
            return {
                "schema": repair_cycle.CANDIDATE_SCHEMA,
                "pass": True,
                "repair_sha256": request["repair_sha256"],
                "candidate_kind": "DISCRIMINATOR",
                "candidate": {
                    "discriminator_id": "d_verified",
                    "outcomes": {"r1": "A", "r2": "B"},
                },
                "truth_authority": False,
                "verification_authority": False,
                "promotion_authority": False,
                "acceptance_authority": False,
                "terminal_authority": False,
            }

        def semantic_verifier(request):
            return {
                "schema": repair_cycle.VERIFY_SCHEMA,
                "pass": True,
                "state_sha256": request["state_sha256"],
                "repair_sha256": request["repair_sha256"],
                "candidate_sha256": request["candidate_sha256"],
                "candidate_kind": request["candidate_kind"],
                "verified_properties": [request["required_verified_property"]],
                "promotion_authority": False,
                "acceptance_authority": False,
                "terminal_authority": False,
            }

        with patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = fabric.run(
                {
                    "mode": "REACHED_ESCAPE_STATE",
                    "payload": state,
                    "options": {"learn": False},
                },
                capability_expander=capability_expander,
                semantic_authority_verifier=semantic_verifier,
            )

        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "PASS__REACHED_ESCAPE_REPAIR_CYCLE_CLOSED",
            out,
        )
        self.assertTrue(out["result"]["repair_cycle_closed"], out)
        self.assertEqual(out["result"]["repair_rounds_completed"], 1, out)
        self.assertTrue(
            out["result"]["final_result"]["certified_reached_state_admitted"],
            out,
        )
        self.assertFalse(out["result"]["global_repair_acquirability_proved"], out)
        self.assertFalse(out["result"]["terminal_authority"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
