from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_leaf_binder_v1 as binder


class ProfessionalQualityLeafBinderV1Tests(unittest.TestCase):
    def test_manifest_has_exact_24_leaf_partition(self):
        out = binder.evaluate()
        self.assertEqual(out["root_count"], 12)
        self.assertEqual(out["semantic_leaf_count"], 12)
        self.assertEqual(out["execution_leaf_count"], 12)
        self.assertEqual(out["open_leaf_count"], 24)
        self.assertEqual(len(out["open_semantic_leaf_ids"]), 12)
        self.assertEqual(len(out["open_execution_leaf_ids"]), 12)

    def test_open_domain_leaves_cannot_promote(self):
        out = binder.evaluate()
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["promotion_ready"], out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_structure_itself_is_valid(self):
        out = binder.evaluate()
        self.assertEqual(out["structural_errors"], [], out)

    def test_evidence_freshness_is_explicit_not_promotional(self):
        out = binder.evaluate()
        self.assertIn("evidence_current", out)
        self.assertIn("stale_evidence", out)
        self.assertIn("missing_evidence", out)
        self.assertGreater(out["fresh_evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
