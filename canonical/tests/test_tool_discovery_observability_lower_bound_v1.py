from __future__ import annotations

import copy
import unittest

from canonical.runtime.tool_discovery_observability_lower_bound_v1 import (
    canonical_public_observation,
    prove_lower_bound,
)


class ToolDiscoveryObservabilityLowerBoundV1Tests(unittest.TestCase):
    def test_canonical_indistinguishable_worlds_prove_lower_bound(self):
        out = prove_lower_bound()
        self.assertTrue(out["lower_bound_proved"], out)
        self.assertTrue(out["cheap_hidden_fact_unobservable"])
        self.assertEqual(out["required_action_world_0"], "SELECT_EXPENSIVE")
        self.assertEqual(out["required_action_world_1"], "SELECT_CHEAP")
        self.assertFalse(out["identity_completeness_alone_sufficient"])

    def test_safe_probe_permission_breaks_indistinguishability(self):
        public = canonical_public_observation()
        public["tools"][0]["safe_probe_capabilities"] = ["CAP_A"]
        out = prove_lower_bound(public)
        self.assertFalse(out["lower_bound_proved"], out)
        self.assertFalse(out["cheap_hidden_fact_unobservable"])

    def test_authoritative_supported_declaration_breaks_indistinguishability(self):
        public = canonical_public_observation()
        public["tools"][0]["public_schema"]["capability_CAP_A"] = "SUPPORTED"
        out = prove_lower_bound(public)
        self.assertFalse(out["lower_bound_proved"], out)

    def test_authoritative_unsupported_declaration_breaks_indistinguishability(self):
        public = canonical_public_observation()
        public["tools"][0]["public_schema"]["capability_CAP_A"] = "UNSUPPORTED"
        out = prove_lower_bound(public)
        self.assertFalse(out["lower_bound_proved"], out)

    def test_current_epoch_receipt_breaks_indistinguishability(self):
        public = canonical_public_observation()
        public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "CHEAP",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        })
        out = prove_lower_bound(public)
        self.assertFalse(out["lower_bound_proved"], out)

    def test_stale_receipt_does_not_break_indistinguishability(self):
        public = canonical_public_observation()
        public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "CHEAP",
            "capability": "CAP_A",
            "epoch": -1,
            "supported": True,
        })
        out = prove_lower_bound(public)
        self.assertTrue(out["lower_bound_proved"], out)

    def test_zero_credit(self):
        out = prove_lower_bound()
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
