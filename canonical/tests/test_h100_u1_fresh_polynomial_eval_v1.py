import unittest
from canonical.runtime import h100_u1_fresh_polynomial_eval_v1 as e
class T(unittest.TestCase):
 def test_fresh_holdout(self):
  r=e.run(); self.assertEqual((r["passed"],r["total"]),(12,12),r)
 def test_program_bytes(self):
  self.assertEqual(e.run()["raw_u1_program_bytes"],17)
 def test_zero_aux_and_learned(self):
  r=e.run(); self.assertEqual(r["target_adapted_auxiliary_bytes"],0); self.assertEqual(r["learned_target_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
