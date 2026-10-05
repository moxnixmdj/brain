import unittest
from canonical.runtime import h100_generic_patch_search_transfer_v1 as g

class H100GenericPatchSearchTransferTests(unittest.TestCase):
    def test_all_four_families_transfer(self):
        out=g.run()
        self.assertEqual(out["status"],"PASS__FOUR_OF_FOUR_MULTI_FAMILY_PATCH_TRANSFER__ZERO_CREDIT")
        self.assertEqual(out["tasks_passed"],4)
        self.assertEqual({x["selected_family"] for x in out["tasks"]},{"POWER","HINGE","GAUSSIAN","TANH"})
        for x in out["tasks"]:
            self.assertTrue(x["baseline_seed_registry_miss"])
            self.assertTrue(x["baseline_transfer_registry_miss"])
            self.assertLessEqual(x["seed_holdout_nrmse"],1e-8)
            self.assertLessEqual(x["transfer_holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
