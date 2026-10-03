from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_scope_quantifier_firewall_v1 as f


class ToolDiscoveryScopeQuantifierFirewallTests(unittest.TestCase):
    def test_current_state_detects_quantifier_mismatch(self):
        out = f.evaluate()
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__IDENTITY_COMPLETENESS_IS_NOT_PROTOCOL_POPULATION_COMPLETENESS",
        )
        self.assertTrue(out["identity_universe_complete_within_bound_case"])
        self.assertFalse(out["protocol_population_complete"])
        self.assertTrue(out["terminal_sample_explicitly_nonexhaustive"])
        self.assertTrue(out["receipt_claims_complete_target_case_set"])
        self.assertTrue(out["acceptance_input_injects_complete_target_case_set"])
        self.assertTrue(out["quantifier_mismatch"])
        self.assertFalse(out["tool_discovery_acceptance_promotion_allowed"])
        self.assertEqual(out["current_acceptance_must_remain"], "3_OF_19__8_OF_38")

    def test_identity_completeness_alone_never_discharge_population(self):
        scope = f._load(f.SCOPE_RECEIPT)
        scope = copy.deepcopy(scope)
        scope["complete_target_case_set"] = False
        out = f.evaluate(scope_override=scope)
        self.assertEqual(out["status"], "FAIL_CLOSED__PROTOCOL_POPULATION_COMPLETENESS_OPEN")
        self.assertTrue(out["identity_universe_complete_within_bound_case"])
        self.assertFalse(out["protocol_population_complete"])

    def test_true_universal_population_fact_can_discharge_after_nonexhaustive_sample_claim_is_replaced(self):
        scope = f._load(f.SCOPE_RECEIPT)
        binding = f._load(f.TERMINAL_BINDING)
        acceptance = f._load(f.ACCEPTANCE_INPUT)
        scope = copy.deepcopy(scope)
        binding = copy.deepcopy(binding)
        acceptance = copy.deepcopy(acceptance)

        scope["verified"] = list(scope["verified"]) + ["UNIVERSAL_FORMAL_PROTOCOL_SCOPE_PROVED"]
        binding["source_pool"]["terminal_scope_claim"] = "UNIVERSAL_FORMAL_PROTOCOL_SCOPE_PROVED"
        # The receipt may then legitimately carry a whole-population basis.
        scope["complete_target_case_set"] = True
        out = f.evaluate(
            scope_override=scope,
            binding_override=binding,
            acceptance_override=acceptance,
        )
        self.assertEqual(out["status"], "PASS__PROTOCOL_POPULATION_SCOPE_PROVED")
        self.assertTrue(out["protocol_population_complete"])
        self.assertTrue(out["tool_discovery_acceptance_promotion_allowed"])

    def test_removing_identity_fact_fails_closed_even_if_label_remains(self):
        scope = f._load(f.SCOPE_RECEIPT)
        scope = copy.deepcopy(scope)
        scope["verified"] = [
            x for x in scope["verified"]
            if x != "V1_PUBLIC_EXPOSES_COMPLETE_CASE_TOOL_IDENTITY_LIST"
        ]
        out = f.evaluate(scope_override=scope)
        self.assertEqual(out["status"], "FAIL_CLOSED__IDENTITY_SCOPE_NOT_PROVED")
        self.assertFalse(out["tool_discovery_acceptance_promotion_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
