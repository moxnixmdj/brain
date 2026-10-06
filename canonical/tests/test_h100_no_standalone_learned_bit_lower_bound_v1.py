import unittest
from canonical.runtime import h100_no_standalone_learned_bit_lower_bound_v1 as n

class T(unittest.TestCase):
    def test_learned_only_bound_collapses_without_code_budget(self):
        for f in (1,2,3,16,257,65536):
            self.assertEqual(n.standalone_learned_lower_bound(f),0)
    def test_code_budget_recovers_positive_bound(self):
        self.assertEqual(n.learned_lower_bound_under_code_budget(256,4),4)
    def test_certificate(self):
        c=n.certificate(1024)
        self.assertEqual(c["minimum_total_persistent_capability_bits"],10)
        self.assertEqual(c["standalone_learned_bit_lower_bound_without_code_budget"],0)
if __name__=="__main__": unittest.main(verbosity=2)
