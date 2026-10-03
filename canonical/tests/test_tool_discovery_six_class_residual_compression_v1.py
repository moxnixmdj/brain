from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_six_class_residual_compression_v1 as proof


class ToolDiscoverySixClassResidualCompressionV1Tests(unittest.TestCase):
    def test_live_exact_sources_compress_to_six_classes(self):
        out = proof.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["proved"]["frozen_generator_semantic_class_count"], 6)
        self.assertTrue(out["proved"]["all_frozen_generator_classes_pass"])
        self.assertEqual(out["six_class_score"]["classes_passed"], 6)
        self.assertEqual(out["six_class_score"]["classes_total"], 6)

    def test_randomness_is_only_identifier_suffix(self):
        out = proof.evaluate()
        self.assertTrue(out["pass"], out)
        r = out["randomness"]
        self.assertTrue(r["pass"])
        self.assertEqual(r["random_call_count"], 1)
        self.assertEqual(r["random_semantic_role"], "IDENTIFIER_SUFFIX_ALPHA_RENAMING")
        self.assertEqual(r["suffix_domain_size"], 89999)

    def test_scope_firewall_remains_fail_closed(self):
        out = proof.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["scope_relation"]["strict_acceptance_closed"])
        self.assertEqual(
            out["scope_relation"]["frozen_generator_to_open_domain_protocol"],
            "PROPER_SUBSET_OR_UNPROVED_EQUALITY",
        )
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_contamination_and_comparator_are_not_inferred(self):
        out = proof.evaluate()
        self.assertTrue(out["pass"], out)
        nonclaims = set(out["hard_nonclaims"])
        self.assertIn("NO_INFERENCE_FROM_180_OF_180_TO_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS", nonclaims)
        self.assertIn("NO_OPUS_COMPARATOR_EQUIVALENCE_CLAIM", nonclaims)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["terminal_results_replayed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
