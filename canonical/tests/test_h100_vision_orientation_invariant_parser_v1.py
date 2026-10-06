import unittest
from canonical.runtime import h100_vision_orientation_invariant_parser_v1 as v
class T(unittest.TestCase):
 def test_holdout(self):
  r=v.run(); self.assertEqual(r["passed"],4); self.assertEqual(r["total"],4)
 def test_zero_target_bits(self):
  self.assertEqual(v.run()["target_adapted_persistent_bits"],0)
 def test_background_is_inferred(self):
  rows=[".....","..A..","..A..",".....","..B..","..B.."]
  with self.assertRaises(v.VisionParserError):
   v.parse(rows)
if __name__=="__main__": unittest.main(verbosity=2)
