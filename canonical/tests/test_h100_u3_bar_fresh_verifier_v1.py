import unittest
from canonical.runtime import h100_u3_bar_fresh_verifier_v1 as v
class T(unittest.TestCase):
 def test_fresh_gate(self):
  r=v.run()
  self.assertEqual(r["passed"],10)
  self.assertEqual(r["total"],10)
 def test_frozen_program_size(self):
  r=v.run()
  self.assertEqual(r["program_bits"],3032)
if __name__=="__main__": unittest.main(verbosity=2)
