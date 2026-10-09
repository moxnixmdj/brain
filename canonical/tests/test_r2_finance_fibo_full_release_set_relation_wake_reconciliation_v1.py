import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
REC = ROOT / "canonical/governance/R2_FINANCE_FIBO_FULL_RELEASE_SET_RELATION_WAKE_RECONCILIATION_20261009_V1.json"
SCHED = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V51.json"
VERIFY = ROOT / "canonical/verification/FIBO_Q2_2026_FULL_RELEASE_AUTHORITY_VERIFY_20261009_V1.json"

class TestFiboFullReleaseSetRelationWakeReconciliation(unittest.TestCase):
    def test_bounded_wake_reconciliation_is_sound(self):
        rec = json.loads(REC.read_text())
        sched = json.loads(SCHED.read_text())
        verify = json.loads(VERIFY.read_text())

        wake = rec["target_wake_condition"]
        finance = sched["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertIn(wake, finance["wake_on"])

        self.assertTrue(rec["proved"]["bounded_set_relation_evidence_available"])
        self.assertEqual(rec["proved"]["concept_count"], 2671)
        self.assertEqual(rec["proved"]["direct_entailment_edge_count"], 3443)
        self.assertTrue(rec["proved"]["missing_relation_path_remains_unknown"])

        pack = verify["source_pack"]
        self.assertEqual(pack["source_file_count"], 295)
        self.assertEqual(pack["concept_count"], 2671)
        self.assertEqual(pack["direct_entailment_edge_count"], 3443)

        replay = verify["independent_source_reextraction"]
        self.assertTrue(replay["exact_manifest_match"])
        self.assertTrue(replay["exact_concept_set_match"])
        self.assertTrue(replay["exact_edge_set_match"])

        invariants = verify["verified_invariants"]
        self.assertTrue(invariants["direct_subclass_edges_positive_entailment_only"])
        self.assertTrue(invariants["missing_path_remains_unknown"])

        effect = rec["scheduler_effect"]
        self.assertTrue(effect["wake_condition_satisfied_within_bound_scope"])
        self.assertFalse(effect["remove_global_wake_condition"])
        self.assertEqual(effect["finance_primary_unsolved_count_delta"], 0)
        self.assertIn("OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE", effect["refined_wake_condition"])

        self.assertIn("NO_CLAIM_OPEN_WORLD_FINANCE_ONTOLOGY_COMPLETENESS", rec["hard_nonclaims"])
        self.assertIn("NO_CLAIM_FINANCE_SEMANTIC_TAIL_IS_EMPTY", rec["hard_nonclaims"])
        self.assertEqual(rec["accounting"]["terminal_credit_delta"], 0)

if __name__ == "__main__":
    unittest.main()
