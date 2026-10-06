import unittest
from canonical.runtime.current_terminal_authority_v3_k6_v4_verifier import verify
class T(unittest.TestCase):
    def test_v3(self):
        x=verify()
        self.assertTrue(x["pass"],x)
        self.assertEqual(x["truth_obligations"],29)
        self.assertEqual(x["k6_preproof_generic_implementation_generators"],0)
        self.assertEqual(x["k6_additional_terminal_truth_variables"],0)
        self.assertEqual(x["terminal_credit_delta"],0)
if __name__=="__main__":unittest.main(verbosity=2)
