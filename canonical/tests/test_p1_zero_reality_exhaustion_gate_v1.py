from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_zero_reality_exhaustion_gate_v1 as gate


class P1ZeroRealityExhaustionGateTests(unittest.TestCase):
    def sources(self):
        return (
            gate._load(gate.P1_BINDING),
            gate._load(gate.P1_QUARANTINE),
            gate._load(gate.P1_V4_RESIDUAL),
            gate._load(gate.TYPED_V4),
            gate._load(gate.INFO_SAFE_V2),
        )

    def test_live_sources_reach_zero_reality_fixed_point_but_do_not_clear_p1(self):
        out = gate.evaluate()
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertTrue(out["zero_reality_fixed_point_reached"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])
        self.assertEqual(
            set(out["residual_obligations"]),
            {"P1_EXPLICIT_SCOPE_FAILURE_CLASS", "P1_HETEROGENEOUS_INTERVENTION_RESCUE"},
        )
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_bounded_additive_rescue_cannot_be_scope_transport(self):
        b, q, r, t, i = self.sources()
        i = copy.deepcopy(i)
        i["verified"] = list(i.get("verified") or []) + [
            "UNVERIFIED_NOTE_FULL_CROSS_DOMAIN_RESCUE"
        ]
        out = gate._evaluate(b, q, r, t, i)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertFalse(
            out["existing_evidence"]["information_safe_v2"][
                "scope_complete_for_typed_cross_domain_terminal_envelope"
            ]
        )
        self.assertFalse(out["can_clear_p1_scope_quarantine"])

    def test_spoofed_scope_kind_in_typed_v4_fails_closed(self):
        b, q, r, t, i = self.sources()
        t = copy.deepcopy(t)
        t["verified"]["mechanism_classes"] = list(t["verified"]["mechanism_classes"]) + ["SCOPE"]
        out = gate._evaluate(b, q, r, t, i)
        self.assertEqual(out["status"], "FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("TYPED_V4_MECHANISM_SET_DRIFT", out["errors"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])

    def test_disabling_synthetic_terminal_firewall_fails_closed(self):
        b, q, r, t, i = self.sources()
        b = copy.deepcopy(b)
        b["terminal_acceptance"]["standalone_synthetic_whole_domain_score_forbidden"] = False
        out = gate._evaluate(b, q, r, t, i)
        self.assertEqual(out["status"], "FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("SYNTHETIC_TERMINAL_SCORE_FIREWALL_MISSING", out["errors"])

    def test_v4_residual_can_clear_bit_is_not_authority(self):
        b, q, r, t, i = self.sources()
        r = copy.deepcopy(r)
        r["result"]["can_clear_p1_scope_quarantine"] = True
        out = gate._evaluate(b, q, r, t, i)
        self.assertEqual(out["status"], "FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("P1_V4_RESIDUAL_RECEIPT_UNEXPECTEDLY_CLEARABLE", out["errors"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
