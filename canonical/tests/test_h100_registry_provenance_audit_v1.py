import unittest
from canonical.runtime import h100_registry_provenance_audit_v1 as a

class H100RegistryProvenanceAuditTests(unittest.TestCase):
    def test_cubic_is_persisted_data_selected_structure(self):
        row=a.cubic_witness()
        self.assertEqual(row["candidate_count"],3)
        self.assertEqual(row["selected_structure"],"AFFINE_PLUS_X3")
        self.assertEqual(row["fixed_length_selection_capacity_bits"],2)
        self.assertTrue(row["provenance_v1_learned_origin"])
        self.assertTrue(row["registry_persistence_verified"])

    def test_depth4_three_persisted_structures(self):
        row=a.chain_witness()
        self.assertEqual(row["candidate_count_per_task"],1554)
        self.assertEqual(row["persisted_structure_count"],3)
        self.assertEqual(row["fixed_length_selection_capacity_bits_per_structure"],11)
        self.assertEqual(row["aggregate_fixed_length_selection_capacity_bits"],33)
        self.assertTrue(row["all_provenance_v1_learned_origin"])

    def test_dual_ledgers_diverge(self):
        out=a.run()
        self.assertTrue(out["syntactic_v0"]["zero_learned_claim_survives_for_these_registry_entries"])
        self.assertFalse(out["provenance_v1"]["zero_learned_claim_survives_for_these_registry_entries"])
        self.assertTrue(out["provenance_v1"]["nonzero_learned_origin_state_established"])
        self.assertIsNone(out["provenance_v1"]["exact_learned_origin_bytes"])

    def test_exact_mutual_information_is_not_overclaimed(self):
        out=a.run()
        for row in out["witnesses"]:
            self.assertIsNone(row["exact_mutual_information_bits_claimed"])

    def test_zero_terminal_credit(self):
        self.assertEqual(a.run()["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
