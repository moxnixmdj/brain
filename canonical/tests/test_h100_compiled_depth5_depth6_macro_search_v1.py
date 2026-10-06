import unittest
from canonical.runtime import h100_compiled_depth5_depth6_macro_search_v1 as m

class T(unittest.TestCase):
    def test_full(self):
        out=m.run()
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertEqual(out["task_count"],3)
        for row in out["tasks"]:
            self.assertTrue(row["baseline_registry_v8_miss"])
            self.assertEqual(row["candidate_count"],42)
            self.assertEqual(row["counts"],{"1":6,"2":36})
            self.assertEqual(row["exact_counts"]["1"],0)
            self.assertEqual(row["first_exact_macro_depth"],2)
            self.assertLessEqual(row["selected"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
