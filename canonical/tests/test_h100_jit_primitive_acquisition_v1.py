import unittest
from canonical.runtime import h100_jit_primitive_acquisition_v1 as p

class H100JITPrimitiveAcquisitionTests(unittest.TestCase):
    def test_fixed_operator_miss_then_jit_erf_transfer(self):
        out=p.run()
        self.assertTrue(out["baseline_seed_registry_v4_miss"])
        self.assertTrue(out["baseline_transfer_registry_v4_miss"])
        self.assertNotEqual(out["baseline_expression_status"],"EXACT_CANDIDATE_FOUND")
        self.assertEqual(out["seed_best"]["gamma"],0.8)
        self.assertLessEqual(out["seed_best"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["transfer_best"]["gamma"],1.6)
        self.assertLessEqual(out["transfer_best"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["status"],"PASS__FIXED_OPERATOR_SET_ESCAPE_VIA_JIT_VERIFIED_PRIMITIVE__ZERO_CREDIT")
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
