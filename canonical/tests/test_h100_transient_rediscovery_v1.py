import unittest
from canonical.runtime import h100_transient_rediscovery_v1 as r

class H100TransientRediscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=r.run()

    def test_five_tasks_are_evaluated(self):
        self.assertEqual(self.out["task_count"],5)

    def test_no_persistent_fit_state_is_written(self):
        self.assertEqual(self.out["persistent_m_fit_bytes"],0)
        self.assertEqual(self.out["persistent_search_selected_structures"],0)
        self.assertEqual(self.out["persistent_fitted_coefficients"],0)
        self.assertFalse(self.out["writes_discovered_structure_to_registry"])

    def test_all_searches_are_complete_through_depth4(self):
        for row in self.out["tasks"]:
            self.assertEqual(row["rediscovery"]["cumulative_count"],1554)
            self.assertEqual(row["rediscovery"]["counts_by_depth"],{"1":6,"2":36,"3":216,"4":1296})

    def test_every_task_finds_an_exact_structure(self):
        for row in self.out["tasks"]:
            s=row["rediscovery"]["selected"]
            self.assertIsNotNone(s,row["task_id"])
            self.assertLessEqual(s["train_nrmse"],1e-10,row["task_id"])
            self.assertLessEqual(s["holdout_nrmse"],1e-8,row["task_id"])

    def test_every_transient_structure_transfers(self):
        for row in self.out["tasks"]:
            t=row["transfer"]
            self.assertIsNotNone(t,row["task_id"])
            self.assertEqual(t["status"],"TRANSFER_OK")
            self.assertLessEqual(t["holdout_nrmse"],1e-8,row["task_id"])

if __name__=="__main__":
    unittest.main(verbosity=2)
