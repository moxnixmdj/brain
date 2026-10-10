from __future__ import annotations
import unittest
from pathlib import Path
from canonical.runtime import professional_quality_leaf_binder_v2 as binder

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V2.json"

EXPECTED_EXECUTION={
"PQ::R1_TARGET_SPECIFICATION::EXECUTION","PQ::R2_CANDIDATE_SEARCH::EXECUTION",
"PQ::R3_REALIZATION_OBSERVATION::EXECUTION","PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION",
"PQ::R5_EVALUATOR_REFERENCE::EXECUTION","PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION",
"PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION","PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION",
"PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION","PQ::R10_ANALYSIS_DECISION::EXECUTION",
"PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION","PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
}

class ProfessionalLeafRegistryV2PropertyTruthTests(unittest.TestCase):
    def test_v2_derives_all_twelve_execution_leaves(self):
        out=binder.evaluate(registry_path=REGISTRY)
        self.assertTrue(out["existing_evidence_current"],out)
        self.assertEqual(out["structural_errors"],[])
        self.assertEqual(out["rejected_receipt_count"],0)
        self.assertEqual(set(out["verified_execution_leaf_ids"]),EXPECTED_EXECUTION)
        self.assertEqual(out["verified_semantic_leaf_ids"],[])
        self.assertEqual(out["verified_leaf_count"],12)
        self.assertEqual(out["open_leaf_count"],12)
        self.assertEqual(out["open_execution_leaf_ids"],[])
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["pass"])

    def test_v2_grants_no_extra_authority(self):
        out=binder.evaluate(registry_path=REGISTRY)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
