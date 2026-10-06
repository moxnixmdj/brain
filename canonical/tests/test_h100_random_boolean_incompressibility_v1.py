import unittest
from canonical.runtime import h100_random_boolean_incompressibility_v1 as r

class T(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(r.truth_table_bits(3),8)
        self.assertEqual(r.log2_total_boolean_functions(3),8)
    def test_fraction_bound(self):
        self.assertEqual(r.log2_short_description_fraction_upper_bound(10,100),100-1024)
    def test_h100_100mb_fails_for_some_30bit_functions(self):
        c=r.certificate(30,100_000_000)
        self.assertTrue(c["some_function_exceeds_budget"])
        self.assertEqual(c["truth_table_bits"],1_073_741_824)
        self.assertEqual(c["minimum_total_bytes_for_universal_exact_coverage"],134_217_728)
    def test_code_budget_implies_residual_learned_bits(self):
        self.assertEqual(r.minimum_learned_bits_given_code_budget_for_universal_exact_coverage(10,100),924)
    def test_invalid(self):
        with self.assertRaises(r.IncompressibilityError): r.truth_table_bits(-1)
if __name__=="__main__": unittest.main(verbosity=2)
