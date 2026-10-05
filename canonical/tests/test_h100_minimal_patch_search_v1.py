import json, unittest
from canonical.runtime import h100_minimal_patch_search_v1 as e

class H100MinimalPatchSearchTests(unittest.TestCase):
    def test_precommit_freezes_distinct_transfer_before_outcome(self):
        d=json.loads(e.PRE.read_text())
        self.assertTrue(d["transfer_task"]["frozen_before_patch_outcome"])
        self.assertEqual([x["patch_id"] for x in d["patch_grammar"]],["AFFINE_PLUS_X2","AFFINE_PLUS_X3","AFFINE_PLUS_X4"])

    def test_current_registry_misses_seed_and_transfer(self):
        t=json.loads(e.TPRE.read_text())
        self.assertTrue(e._baseline_miss(e._rows("SEED",[float(x) for x in t["training_x"]])))
        self.assertTrue(e._baseline_miss(e._rows("TRANSFER",[float(x) for x in t["training_x"]])))

    def test_patch_search_selects_cubic_and_transfers(self):
        out=e.run()
        self.assertEqual(out["selected_patch_id"],"AFFINE_PLUS_X3")
        self.assertLessEqual(out["seed_holdout_nrmse"],1e-8)
        self.assertLessEqual(out["transfer_holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["compile_candidate"]["capability_id"],"CAP_AFFINE_CUBIC_V1")

if __name__=="__main__":
    unittest.main(verbosity=2)
