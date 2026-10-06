import unittest
from canonical.runtime import h100_answer_relevant_ambiguity_v1 as a

class T(unittest.TestCase):
    def test_worlds_same_output_need_zero_bits(self):
        self.assertEqual(a.exact_output_bits_lower_bound([["X","X","X"]]),0)
    def test_two_outputs_need_one_bit(self):
        self.assertEqual(a.exact_output_bits_lower_bound([["INPUT",None,None]]),1)
    def test_four_outputs_need_two_bits(self):
        self.assertEqual(a.exact_output_bits_lower_bound([[0,1,2,3]]),2)
    def test_selective_abstention(self):
        p=a.zero_bit_selective_policy([["A","A"],["B","C"]])
        self.assertEqual(p[0]["action"],"CLASSIFY")
        self.assertEqual(p[1]["action"],"ABSTAIN")
    def test_safe_coverage(self):
        self.assertEqual(a.zero_bit_safe_coverage([["A","A"],["B","C"]]),0.5)
    def test_multiple_runtime_classes(self):
        self.assertEqual(a.exact_output_bits_lower_bound([["A"],["B"],["C"]]),0)

if __name__=="__main__":
    unittest.main(verbosity=2)
