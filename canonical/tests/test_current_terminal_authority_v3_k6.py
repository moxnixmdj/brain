import unittest
from canonical.runtime.current_terminal_authority_v3_k6_verifier import verify

class TestAuthorityV3(unittest.TestCase):
    def test_current_reconciliation(self):
        out=verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["truth_obligations"],29)
        self.assertEqual(out["k6_preproof_implementation_generators"],0)
        self.assertEqual(out["k6_additional_terminal_truth_variables"],0)
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
