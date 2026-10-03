from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_universal_scope_formalism_cut_v1 as cut


class Tests(unittest.TestCase):
    def test_current_exact_terminal_formalism_fails_closed(self):
        out = cut.evaluate()
        self.assertEqual(out["source_blob_drift"], [], out)
        self.assertTrue(out["frozen_target"]["family_task_dimension_unknown_tool_discovery"])
        self.assertTrue(out["frozen_target"]["contract_requires_discover_candidate_tools_if_needed"])
        self.assertTrue(out["terminal_binding"]["preenumerated_tool_ids_visible"])
        self.assertFalse(out["terminal_binding"]["explicit_complete_tool_universe_semantics"])
        self.assertEqual(
            out["exact_terminal_candidate_action_vocabulary"],
            ["ESCALATE", "PROBE", "SELECT"],
        )
        self.assertFalse(out["terminal_candidate_has_discover_action"])
        self.assertTrue(out["broader_dynamic_candidate_has_discover_action"])
        self.assertTrue(out["formalism_gap_established"])
        self.assertEqual(
            out["classification"], "SPECIFICATION_OR_FORMALISM_RESIDUAL"
        )
        self.assertFalse(out["universal_scope_certificate_currently_admissible"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_broader_dynamic_candidate_is_not_promoted_by_presence_of_discover(self):
        out = cut.evaluate()
        self.assertIn("DISCOVER", out["broader_dynamic_candidate_action_vocabulary"])
        self.assertIn(
            "THIS_DOES_NOT_CLAIM_DYNAMIC_V3_IS_UNIVERSALLY_CORRECT",
            out["hard_nonclaims"],
        )
        self.assertFalse(out["promotion_authority"])

    def test_minimum_missing_fact_is_exact(self):
        out = cut.evaluate()
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_EXACT_SCOPE_SEMANTICS_PROVING_PREENUMERATED_TOOL_IDS_ARE_COMPLETE_FOR_THE_FROZEN_TARGET__"
            "OR_A_VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES",
        )
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertFalse(out["execution_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
