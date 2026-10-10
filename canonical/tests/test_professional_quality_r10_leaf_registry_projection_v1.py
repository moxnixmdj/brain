from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_leaf_binder_v2 as binder

R10_EXECUTION="PQ::R10_ANALYSIS_DECISION::EXECUTION"


class R10LeafRegistryProjectionV1Tests(unittest.TestCase):
    def test_current_registry_derives_exactly_one_leaf(self):
        out=binder.evaluate()
        self.assertTrue(out["existing_evidence_current"], out)
        self.assertEqual(out["structural_errors"], [])
        self.assertEqual(out["rejected_receipt_count"], 0)
        self.assertEqual(out["verified_leaf_count"], 1)
        self.assertEqual(out["verified_semantic_leaf_ids"], [])
        self.assertEqual(out["verified_execution_leaf_ids"], [R10_EXECUTION])
        self.assertEqual(out["open_leaf_count"], 23)
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["pass"])

    def test_r10_receipt_is_admitted_without_extra_authority(self):
        out=binder.evaluate()
        rows=[x for x in out["receipt_results"] if x["leaf_id"]==R10_EXECUTION]
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["admitted"],rows[0])
        self.assertEqual(rows[0]["errors"],[])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
