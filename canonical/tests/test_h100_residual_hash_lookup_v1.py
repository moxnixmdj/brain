import unittest
from canonical.runtime import h100_residual_hash_lookup_v1 as h

class H100ResidualHashLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=h.run()

    def test_theorem_identity_holds(self):
        self.assertTrue(self.out["theorem_audit"]["feature_key_equals_target_key"])

    def test_index_is_target_independent(self):
        self.assertFalse(self.out["index"]["uses_target_y"])
        self.assertGreater(self.out["index"]["key_count"],0)

    def test_all_five_fresh_tasks_hash_and_verify(self):
        self.assertEqual(len(self.out["tasks"]),5)
        for row in self.out["tasks"]:
            self.assertGreater(row["solve"]["hash_bucket_size"],0,row["task_id"])
            self.assertIsNotNone(row["solve"]["selected"],row["task_id"])
            self.assertLessEqual(row["solve"]["selected"]["holdout_nrmse"],1e-8,row["task_id"])
            self.assertEqual(row["transfer"]["status"],"TRANSFER_OK",row["task_id"])
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8,row["task_id"])

    def test_lookup_is_fast(self):
        self.assertLess(self.out["median_lookup_plus_verification_seconds"],0.05)

    def test_no_persistent_fit_state_or_index(self):
        self.assertEqual(self.out["persistent_m_fit_bytes"],0)
        self.assertEqual(self.out["persistent_hash_index"],0)
        self.assertEqual(self.out["persistent_selected_structures"],0)
        self.assertFalse(self.out["writes_index_or_selection"])

if __name__=="__main__":
    unittest.main(verbosity=2)
