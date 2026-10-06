import unittest
from canonical.runtime import h100_p0_generative_tournament_v1 as g
class T(unittest.TestCase):
 def test_counts(self):
  r=g.run();self.assertEqual(r["total"],450)
 def test_all(self):
  r=g.run();self.assertTrue(r["all_pass"]);self.assertEqual(r["passed"],450)
 def test_each_class(self):
  r=g.run();self.assertEqual(set(r["by_class"]),set(g.COUNTS));self.assertTrue(all(v["passed"]==50 for v in r["by_class"].values()))
 def test_zero_target_bits(self):
  self.assertEqual(g.run()["target_adapted_persistent_bits"],0)
if __name__=="__main__":unittest.main(verbosity=2)
