import unittest
from canonical.runtime import h100_complete_binary_root_search_v1 as b
class T(unittest.TestCase):
    def test_full(self):
        out=b.run()
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertEqual(out["task_count"],3)
        for r in out["tasks"]:
            self.assertTrue(r["baseline_registry_v8_miss"])
            self.assertEqual(r["candidate_count"],201502)
            self.assertIsNotNone(r["selected"])
            self.assertLessEqual(r["selected"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(r["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
