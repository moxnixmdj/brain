from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import reached_escape_finite_totality_certificate_v1 as certificate


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
    def test_live_fabric_reaches_valid_state_outside_finite_totality_preconditions(self):
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
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "UNSPLITTABLE_POLICY_CONFLICT",
            out,
        )
        self.assertFalse(out["result"]["reached_state_progress_proved"], out)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
