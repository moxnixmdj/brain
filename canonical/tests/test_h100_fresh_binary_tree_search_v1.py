import unittest
from canonical.runtime import h100_fresh_binary_tree_search_v1 as b

class T(unittest.TestCase):
    def test_full(self):
        out=b.run()
        self.assertEqual(len(out["tasks"]),3)
        self.assertTrue(all(x["baseline_registry_v8_miss"] for x in out["tasks"]))
        self.assertTrue(out["status"].startswith("PASS__"),out)
        for row in out["tasks"]:
            self.assertEqual(row["search_status"],"EXACT_CANDIDATE_FOUND")
            self.assertLessEqual(row["best_candidate"]["validation_nrmse"],1e-8)
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
