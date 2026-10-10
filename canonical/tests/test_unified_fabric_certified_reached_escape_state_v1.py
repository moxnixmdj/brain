from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import reached_escape_state_kernel_v1 as kernel


def state(*, policies, discriminators=()):
    return {
        "schema": kernel.STATE_SCHEMA,
        "state_id": "LIVE-CERTIFIED-ROUTE-TEST",
        "regions": [{"region_id": "r1"}, {"region_id": "r2"}],
        "policies": list(policies),
        "discriminators": list(discriminators),
    }


def policy(pid, covers):
    return {
        "policy_id": pid,
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": list(covers),
    }


class UnifiedFabricCertifiedReachedStateTests(unittest.TestCase):
    def _run(self, payload):
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
            return fabric.run(
                {
                    "mode": "REACHED_ESCAPE_STATE",
                    "payload": payload,
                    "options": {"learn": False},
                }
            )

    def test_catalog_names_proof_carrying_constructor(self):
        out = fabric.catalog()
        self.assertEqual(
            out["engines"]["REACHED_ESCAPE_STATE"],
            "certified_reached_escape_state_constructor_v1.construct",
        )

    def test_common_policy_state_is_admitted_through_live_fabric(self):
        out = self._run(
            state(policies=[policy("p_common", ("r1", "r2"))])
        )
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        result = out["result"]
        self.assertEqual(result["status"], "PASS__CERTIFIED_REACHED_STATE_ADMITTED")
        self.assertTrue(result["certified_reached_state_admitted"])
        self.assertTrue(result["reached_state_future_outcome_totality_proved"])
        self.assertFalse(result["global_escape_progress_totality_proved"])
        self.assertFalse(result["terminal_authority"])
        self.assertEqual(result["terminal_credit_delta"], 0)

    def test_unsplittable_state_is_rejected_with_deterministic_repair(self):
        payload = state(
            policies=[
                policy("p1", ("r1",)),
                policy("p2", ("r2",)),
            ]
        )
        a = self._run(payload)
        b = self._run(payload)
        for out in (a, b):
            self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
            self.assertFalse(out["inner_pass"], out)
            result = out["result"]
            self.assertEqual(
                result["status"],
                "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED",
            )
            self.assertFalse(result["certified_reached_state_admitted"])
            self.assertEqual(
                result["certificate_status"],
                "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY",
            )
            self.assertFalse(result["global_repair_acquirability_proved"])
            self.assertFalse(result["terminal_authority"])
            self.assertEqual(result["terminal_credit_delta"], 0)
        self.assertEqual(a["result"]["repair_sha256"], b["result"]["repair_sha256"])

    def test_uncovered_region_is_rejected_before_raw_kernel_admission(self):
        out = self._run(
            state(policies=[policy("p1", ("r1",))])
        )
        self.assertFalse(out["inner_pass"], out)
        result = out["result"]
        self.assertEqual(
            result["certificate_status"],
            "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
        )
        self.assertEqual(
            result["repair_request"]["kind"],
            "UNCOVERED_REGION_POLICY_REPAIR",
        )
        self.assertFalse(result["certified_reached_state_admitted"])

    def test_untrusted_state_fails_closed_without_repair_or_authority(self):
        bad = policy("p", ("r1", "r2"))
        bad["authenticated"] = False
        out = self._run(state(policies=[bad]))
        self.assertFalse(out["inner_pass"], out)
        result = out["result"]
        self.assertEqual(
            result["status"],
            "FAIL_CLOSED__REACHED_STATE_CERTIFICATION_FAILED",
        )
        self.assertFalse(result["certified_reached_state_admitted"])
        self.assertFalse(result["promotion_authority"])
        self.assertFalse(result["terminal_authority"])
        self.assertEqual(result["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
