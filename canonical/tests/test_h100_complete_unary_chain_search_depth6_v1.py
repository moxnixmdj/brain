import unittest
from canonical.runtime import h100_complete_unary_chain_search_depth6_v1 as d

class T(unittest.TestCase):
    def test_full(self):
        out=d.run()
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertEqual(out["task_count"],3)
        for row in out["tasks"]:
            self.assertTrue(row["baseline_registry_v8_miss"])
            self.assertEqual(row["cumulative"],55986)
            self.assertEqual(row["first_exact_depth"],6)
            self.assertTrue(all(row["exact_counts"][str(k)]==0 for k in (1,2,3,4,5)))
            self.assertLessEqual(row["selected"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
