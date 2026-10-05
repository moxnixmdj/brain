import copy,json,unittest
from pathlib import Path
from canonical.runtime import h100_declarative_operator_pack_acquisition_v1 as d

class H100DeclarativeOperatorPackTests(unittest.TestCase):
    def test_blob_binding_and_static_rejection(self):
        pre=json.loads(d.PRE.read_text())
        spec=pre["packs"][0]
        loaded=d.load_pack(d.ROOT/spec["path"],spec["git_blob_sha"],pre["pack_contract"])
        self.assertEqual(loaded["git_blob_sha"],spec["git_blob_sha"])
        with self.assertRaisesRegex(d.DeclarativePackError,"PACK_GIT_BLOB_SHA_MISMATCH"):
            d.load_pack(d.ROOT/spec["path"],"0"*40,pre["pack_contract"])
        bad=copy.deepcopy(loaded["pack"]["ast"])
        bad["op"]="EVAL"
        counter=[0]
        with self.assertRaisesRegex(d.DeclarativePackError,"AST_OPCODE_NOT_ALLOWED"):
            d._validate_node(bad,depth=1,max_depth=8,counter=counter)

    def test_domain_fail_closed(self):
        pre=json.loads(d.PRE.read_text()); spec=pre["packs"][0]
        loaded=d.load_pack(d.ROOT/spec["path"],spec["git_blob_sha"],pre["pack_contract"])
        with self.assertRaisesRegex(d.DeclarativePackError,"PACK_INPUT_OUT_OF_DOMAIN"):
            d.evaluate_pack(loaded,9.0)

    def test_two_nonstdlib_packs_acquire_and_transfer(self):
        out=d.run()
        self.assertEqual(out["status"],"PASS__CONTENT_ADDRESSED_NON_STDLIB_DECLARATIVE_OPERATOR_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT",out)
        self.assertEqual(len(out["packs"]),2)
        for row in out["packs"]:
            self.assertTrue(row["baseline_seed_registry_v6_miss"],row)
            self.assertTrue(row["baseline_transfer_registry_v6_miss"],row)
            self.assertNotEqual(row["baseline_expression"]["status"],"EXACT_CANDIDATE_FOUND",row)
            self.assertTrue(row["deterministic_replay"],row)
            self.assertTrue(row["pass"],row)
            self.assertLessEqual(row["seed_best"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer_best"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["arbitrary_code_execution"],0)
        self.assertEqual(out["arbitrary_imports"],0)
        self.assertEqual(out["subprocess_calls"],0)
        self.assertEqual(out["network_calls"],0)

if __name__=="__main__": unittest.main(verbosity=2)
