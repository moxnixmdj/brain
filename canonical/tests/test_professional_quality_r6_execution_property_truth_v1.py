from __future__ import annotations
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r6_execution_property_truth_v1 as v

ROOT=Path(__file__).resolve().parents[2]

class R6ExecutionPropertyTruthTests(unittest.TestCase):
    def test_exact_challenge_set_closes_execution_leaf_only(self):
        out=v.verify(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["leaf_id"], v.LEAF_ID)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_count"], 10)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["r6_root_closed"])
        self.assertFalse(out["global_evidence_completeness_proved"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_challenge_matrix_contains_positive_near_miss_and_adversarial_boundaries(self):
        rows=v.run_challenges(repo_root=ROOT)
        by={row["case_id"]:row for row in rows}
        self.assertEqual(set(by), {
            "POSITIVE_EXACT_FROZEN_R6_BINDING",
            "NEAR_MISS_WRONG_SUBJECT_TUPLE",
            "ADVERSARIAL_MISSING_SUBJECT_EVIDENCE_COMPONENT",
            "ADVERSARIAL_SCOPE_WIDENING",
            "ADVERSARIAL_STATUS_STRING_AUTHORITY",
            "ADVERSARIAL_LEAF_ADMISSION_LAW_DRIFT",
            "ADVERSARIAL_LEAF_BINDER_PREMISE_REMOVAL",
            "ADVERSARIAL_PROOF_BOUND_STEP_PREMISE_REMOVAL",
            "ADVERSARIAL_SELF_AUTHORITY_ESCALATION",
            "ADVERSARIAL_BRIDGE_REFERENCE_DRIFT",
        })
        self.assertTrue(by["POSITIVE_EXACT_FROZEN_R6_BINDING"]["observed_pass"])
        for case_id,row in by.items():
            if case_id.startswith("POSITIVE_"):
                continue
            self.assertFalse(row["observed_pass"], row)
            self.assertEqual(row["observed_reason"], row["expected_reason"], row)

    def test_manifest_contract_and_scope_are_bound(self):
        out=v.verify(repo_root=ROOT)
        self.assertEqual(
            out["manifest_acceptance"],
            "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT",
        )
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertTrue(out["historical_r6_binding_receipt_pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
