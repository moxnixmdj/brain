import unittest
from canonical.runtime import h100_compiled_macro_chain_search_v1 as m

class H100CompiledMacroChainSearchTests(unittest.TestCase):
    def test_three_fresh_depth8_macro_compositions(self):
        out=m.run()
        self.assertEqual(out["task_count"],3)
        self.assertEqual(out["macro_candidate_count_per_task"],12)
        self.assertEqual(out["primitive_depth8_complete_chain_count"],2015538)
        self.assertEqual(out["search_space_cardinality_ratio_primitive_over_macro"],167961.5)
        for row in out["tasks"]:
            self.assertTrue(row["baseline_registry_v8_miss"])
            self.assertEqual(row["primitive_sequence_length"],8)
            self.assertEqual(row["candidate_count"],12)
            self.assertEqual(row["count_by_depth"],{"1":3,"2":9})
            self.assertEqual(row["exact_count_by_depth"]["1"],0)
            self.assertEqual(row["first_exact_macro_depth"],2)
            self.assertLessEqual(row["selected"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["status"],"PASS__THREE_OF_THREE_DEPTH8_MACRO_COMPOSITIONS__TWELVE_CANDIDATE_SEARCH__ZERO_CREDIT")

if __name__=="__main__":
    unittest.main(verbosity=2)
