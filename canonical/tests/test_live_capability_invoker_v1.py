from __future__ import annotations

import unittest

from canonical.runtime import live_capability_invoker_v1 as invoker
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run


class LiveCapabilityInvokerV1Tests(unittest.TestCase):
    def test_classifier_covers_every_ownership_kind(self):
        rows = {
            "engine:RAW_GOAL": "ENGINE",
            "bound:archive.tar_gz.create_from_manifest": "BOUND_CAPABILITY",
            "h100:CAP_X": "H100_VERIFIED_CAPABILITY",
            "h100:CAP_X@ROUTE_A": "H100_VERIFIED_CAPABILITY",
            "skill:abc": "ACTIVE_VERIFIED_LEARNED_SKILL",
            "certified_route:ROUTE_A": "CERTIFIED_ROUTE",
        }
        for cid, kind in rows.items():
            self.assertEqual(invoker.classify(cid)["kind"], kind)

    def test_catalog_proves_universal_invocation_contract_coverage(self):
        c = catalog()
        coverage = c["live_capability_invocation_coverage"]
        self.assertTrue(coverage["pass"], coverage)
        self.assertEqual(
            coverage["capability_count"],
            c["live_owned_capability_count"],
        )
        self.assertEqual(coverage["missing_capability_count"], 0)
        self.assertTrue(c["all_live_owned_capabilities_universally_invocable"])
        self.assertTrue(c["r1_structural_closure"], c)
        self.assertEqual(c["known_r1_residuals"], [])

    def test_one_front_door_can_invoke_an_owned_engine_by_ownership_id(self):
        out = run({
            "payload": {
                "capability_id": "engine:OWNERSHIP_CATALOG",
                "capability_payload": {},
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["mode"], "LIVE_CAPABILITY")
        self.assertTrue(out["auto_routed"])
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "PASS__EXACT_ENGINE_CAPABILITY_DISPATCHED",
        )
        nested = out["result"]["result"]
        self.assertEqual(nested["mode"], "OWNERSHIP_CATALOG")
        self.assertTrue(nested["inner_pass"], nested)
        self.assertTrue(nested["result"]["live_owned_equals_fabric_reachable"])

    def test_unknown_ownership_identity_fails_closed(self):
        out = run({
            "mode": "LIVE_CAPABILITY",
            "payload": {
                "capability_id": "unknown:nope",
                "capability_payload": {},
            },
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OWNED_CAPABILITY_ID_KIND_UNKNOWN", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
