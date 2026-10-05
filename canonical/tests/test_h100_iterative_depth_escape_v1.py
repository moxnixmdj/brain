import unittest
from canonical.runtime import h100_iterative_depth_escape_v1 as e

class H100IterativeDepthEscapeTests(unittest.TestCase):
    def test_depth4_escape_and_transfer(self):
        out=e.run()
        self.assertTrue(out["baseline_seed_registry_v4_miss"])
        self.assertTrue(out["baseline_transfer_registry_v4_miss"])
        self.assertEqual(out["first_exact_depth"],4)
        self.assertEqual([r["status"] for r in out["search_by_depth"][:3]],[
            "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT",
            "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT",
            "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT",
        ])
        self.assertEqual(out["search_by_depth"][3]["status"],"EXACT_CANDIDATE_FOUND")
        self.assertTrue(out["transfer_structure_only_refit"])
        self.assertLessEqual(out["transfer_holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["status"],"PASS__DEPTH4_ESCAPE_AND_DISTINCT_TRANSFER__ZERO_CREDIT")

if __name__=="__main__":
    unittest.main(verbosity=2)
