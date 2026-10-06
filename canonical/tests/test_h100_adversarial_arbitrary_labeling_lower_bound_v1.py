import unittest
from canonical.runtime import h100_adversarial_arbitrary_labeling_lower_bound_v1 as a
class T(unittest.TestCase):
 def test_class_size(self):
  self.assertEqual(a.labeling_class_size(8),256)
 def test_total_bits(self):
  self.assertEqual(a.total_target_adapted_bits_lower_bound(64),64)
 def test_learned_given_code_budget(self):
  self.assertEqual(a.learned_bits_lower_bound(64,0),64)
  self.assertEqual(a.learned_bits_lower_bound(64,16),48)
  self.assertEqual(a.learned_bits_lower_bound(64,64),0)
 def test_coverage_fraction(self):
  self.assertEqual(a.exact_universal_coverage_fraction(10,0),1/1024)
  self.assertEqual(a.exact_universal_coverage_fraction(10,10),1.0)
 def test_invalid(self):
  with self.assertRaises(a.ArbitraryLabelingBoundError): a.labeling_class_size(0)
if __name__=="__main__": unittest.main(verbosity=2)
