import unittest
from canonical.runtime import h100_binary_composition_transient_v1 as b

class H100BinaryCompositionTransientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=b.run()

    def test_sign_orientation_coverage(self):
        self.assertTrue(self.out["orientation_audit"]["all_pass"])
        self.assertEqual(set(self.out["orientation_audit"]["operators"]),{"add","sub","mul","stable_div"})

    def test_binary_index_is_target_independent(self):
        self.assertFalse(self.out["index"]["uses_target_y"])
        self.assertGreater(self.out["index"]["raw_binary_proposal_count"],0)
        self.assertGreater(self.out["index"]["terminal_residual_key_count"],0)

    def test_all_five_binary_tasks_hash_verify_and_transfer(self):
        self.assertEqual(len(self.out["tasks"]),5)
        for row in self.out["tasks"]:
            self.assertGreater(row["solve"]["hash_bucket_size"],0,row["task_id"])
            self.assertIsNotNone(row["solve"]["selected"],row["task_id"])
            self.assertLessEqual(row["solve"]["selected"]["holdout_nrmse"],1e-8,row["task_id"])
            self.assertEqual(row["transfer"]["status"],"TRANSFER_OK",row["task_id"])
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8,row["task_id"])

    def test_no_persistent_fit_state(self):
        self.assertEqual(self.out["persistent_m_fit_bytes"],0)
        self.assertEqual(self.out["persistent_binary_index"],0)
        self.assertEqual(self.out["persistent_selected_binary_structures"],0)
        self.assertFalse(self.out["writes_binary_index_or_selection"])

if __name__=="__main__":
    unittest.main(verbosity=2)
