import unittest
from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import relaxed_correct

class PreservationScorerTests(unittest.TestCase):
    def test_text_is_case_insensitive_exact(self):
        self.assertTrue(relaxed_correct("Blue","blue"))
        self.assertFalse(relaxed_correct("Blue","blue line"))
    def test_numeric_relative_tolerance(self):
        self.assertTrue(relaxed_correct("100","105"))
        self.assertFalse(relaxed_correct("100","105.01"))
    def test_zero_gold_requires_zero(self):
        self.assertTrue(relaxed_correct("0","0.0"))
        self.assertFalse(relaxed_correct("0","0.01"))
    def test_percent_and_commas_parse(self):
        self.assertTrue(relaxed_correct("1,000","1000"))
        self.assertTrue(relaxed_correct("50%","49"))

if __name__=="__main__":
    unittest.main(verbosity=2)
