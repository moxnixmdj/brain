import unittest
from canonical.runtime.r2_current_pointer_bounded_concept_registry_verify_v1 import evaluate

class CurrentR2PointerBoundedConceptRegistryVerifyV1Tests(unittest.TestCase):
    def test_current_r2_pointer_binds_bounded_concept_registry_without_false_closure(self):
        out=evaluate()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["bounded_registry_coverage_live"])
        self.assertTrue(out["finance_residual_still_open"])
        self.assertFalse(out["global_open_world_closure_claimed"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
