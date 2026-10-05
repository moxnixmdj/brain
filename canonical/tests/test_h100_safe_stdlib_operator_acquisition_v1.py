import unittest
from canonical.runtime import h100_safe_stdlib_operator_acquisition_v1 as a

class H100SafeStdlibOperatorAcquisitionTests(unittest.TestCase):
    def test_policy_rejects_private_and_noncallable(self):
        pre=__import__("json").loads(a.PRE.read_text())
        policy=pre["acquisition_policy"]
        with self.assertRaisesRegex(a.SafeOperatorAcquisitionError,"ATTRIBUTE_NOT_PUBLIC_IDENTIFIER"):
            a.acquire_operator({"attribute":"__dict__","probes":[0.0]},policy)
        with self.assertRaisesRegex(a.SafeOperatorAcquisitionError,"ATTRIBUTE_NOT_CALLABLE"):
            a.acquire_operator({"attribute":"pi","probes":[0.0]},policy)

    def test_generic_two_operator_acquisition_and_transfer(self):
        out=a.run()
        self.assertEqual(out["status"],"PASS__GENERIC_SAFE_STDLIB_OPERATOR_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT",out)
        self.assertEqual(len(out["operators"]),2)
        for row in out["operators"]:
            self.assertTrue(row["baseline_seed_registry_v5_miss"],row)
            self.assertTrue(row["baseline_transfer_registry_v5_miss"],row)
            self.assertNotEqual(row["baseline_expression"]["status"],"EXACT_CANDIDATE_FOUND",row)
            self.assertTrue(row["pass"],row)
            self.assertLessEqual(row["seed_best"]["holdout_nrmse"],1e-8)
            self.assertLessEqual(row["transfer_best"]["holdout_nrmse"],1e-8)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertEqual(out["arbitrary_module_imports"],0)
        self.assertEqual(out["arbitrary_code_execution"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
