import unittest
from canonical.runtime import h100_complete_unary_chain_search_v1 as s

class H100CompleteUnaryChainSearchTests(unittest.TestCase):
    def test_complete_fresh_depth4_chains_and_transfer(self):
        out=s.run()
        self.assertEqual(out["enumeration_count_per_task"],1554)
        self.assertEqual(out["total_chains_evaluated"],4662)
        self.assertEqual(out["task_count"],3)
        for row in out["tasks"]:
            self.assertTrue(row["baseline_registry_v7_miss"])
            self.assertEqual(row["counts_by_depth"],{"1":6,"2":36,"3":216,"4":1296})
            self.assertEqual(row["first_exact_depth"],4)
            self.assertEqual(row["exact_count_by_depth"]["1"],0)
            self.assertEqual(row["exact_count_by_depth"]["2"],0)
            self.assertEqual(row["exact_count_by_depth"]["3"],0)
            self.assertLessEqual(row["selected"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["status"],"PASS__THREE_OF_THREE_COMPLETE_DEPTH4_UNARY_CHAIN_SEARCH_AND_TRANSFER__ZERO_CREDIT")

if __name__=="__main__":
    unittest.main(verbosity=2)
