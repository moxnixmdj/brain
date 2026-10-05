import unittest
from canonical.runtime import h100_finite_grammar_escape_v1 as e

class H100FiniteGrammarEscapeTests(unittest.TestCase):
    def test_registry_miss_expression_escape_and_transfer(self):
        out=e.run()
        self.assertTrue(out["baseline_seed_registry_v3_miss"])
        self.assertTrue(out["baseline_transfer_registry_v3_miss"])
        self.assertEqual(out["seed_search_status"],"EXACT_CANDIDATE_FOUND")
        self.assertTrue(out["transfer_structure_only_refit"])
        self.assertLessEqual(out["transfer_holdout_nrmse"],1e-8)
        self.assertEqual(out["status"],"PASS__FINITE_PATCH_GRAMMAR_ESCAPE_AND_STRUCTURE_TRANSFER__ZERO_CREDIT")
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
