import unittest
from canonical.runtime import h100_nested_binary_transient_v1 as n

class H100NestedBinaryTransientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=n.run()

    def test_index_is_target_independent(self):
        self.assertFalse(self.out["terminal"]["uses_target_y"])
        self.assertGreater(self.out["inner"]["sign_class_count"],0)
        self.assertGreater(self.out["terminal"]["residual_key_count"],0)

    def test_all_five_nested_tasks_hash_verify_transfer(self):
        self.assertEqual(len(self.out["tasks"]),5)
        for row in self.out["tasks"]:
            self.assertGreater(row["solve"]["hash_bucket_size"],0,row["task_id"])
            self.assertIsNotNone(row["solve"]["selected"],row["task_id"])
            self.assertLessEqual(row["solve"]["selected"]["holdout_nrmse"],1e-8,row["task_id"])
            self.assertEqual(row["transfer"]["status"],"TRANSFER_OK",row["task_id"])
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8,row["task_id"])

    def test_no_persistent_fit_state(self):
        self.assertEqual(self.out["persistent_m_fit_bytes"],0)
        self.assertEqual(self.out["persistent_inner_binary_classes"],0)
        self.assertEqual(self.out["persistent_terminal_index"],0)
        self.assertEqual(self.out["persistent_selected_structure"],0)
        self.assertFalse(self.out["writes_discovery"])

if __name__=="__main__":
    unittest.main(verbosity=2)
