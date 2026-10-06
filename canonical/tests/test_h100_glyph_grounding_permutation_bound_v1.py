import unittest
from canonical.runtime import h100_glyph_grounding_permutation_bound_v1 as g
class T(unittest.TestCase):
 def test_small(self):
  self.assertEqual(g.worlds(4),24)
  self.assertEqual(g.lower_bound_bits(4),5)
 def test_digits(self):
  self.assertEqual(g.lower_bound_bits(10),22)
 def test_letters(self):
  self.assertEqual(g.lower_bound_bits(26),89)
 def test_runtime_mapping_reduces_residual(self):
  self.assertEqual(g.residual_bits_after_runtime_mapping(10,10),0)
  self.assertLess(g.residual_bits_after_runtime_mapping(10,5),g.lower_bound_bits(10))
 def test_invalid(self):
  with self.assertRaises(g.GlyphGroundingError): g.worlds(0)
if __name__=="__main__": unittest.main(verbosity=2)
