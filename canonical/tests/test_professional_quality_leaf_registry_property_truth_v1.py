from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_leaf_binder_v2 as binder

EXPECTED_EXECUTION={
    "PQ::R5_EVALUATOR_REFERENCE::EXECUTION",
    "PQ::R1_TARGET_SPECIFICATION::EXECUTION",
    "PQ::R2_CANDIDATE_SEARCH::EXECUTION",
    "PQ::R3_REALIZATION_OBSERVATION::EXECUTION",
    "PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION",
    "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION",
    "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
    "PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION",
    "PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION",
    "PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION",
    "PQ::R10_ANALYSIS_DECISION::EXECUTION",
    "PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
}


class ProfessionalLeafRegistryPropertyTruthV1Tests(unittest.TestCase):
    def test_current_registry_derives_all_twelve_execution_leaves(self):
        out=binder.evaluate()
        self.assertTrue(out["existing_evidence_current"],out)
        self.assertEqual(out["structural_errors"],[])
        self.assertEqual(out["rejected_receipt_count"],0)
        self.assertEqual(set(out["verified_execution_leaf_ids"]),EXPECTED_EXECUTION)
        self.assertEqual(out["verified_semantic_leaf_ids"],[])
        self.assertEqual(out["verified_leaf_count"],12)
        self.assertEqual(out["open_leaf_count"],12)
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["pass"])

    def test_admitted_receipts_grant_no_extra_authority(self):
        out=binder.evaluate()
        rows={x["leaf_id"]:x for x in out["receipt_results"]}
        self.assertEqual(set(rows),EXPECTED_EXECUTION)
        for leaf_id in EXPECTED_EXECUTION:
            self.assertTrue(rows[leaf_id]["admitted"],rows[leaf_id])
            self.assertEqual(rows[leaf_id]["errors"],[])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
