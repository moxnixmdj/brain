import unittest
from canonical.runtime import h100_text_chart_scale_repair_eval_v1 as e
class T(unittest.TestCase):
 def test_fresh_repair_holdout(self):
  r=e.run(); self.assertEqual(r["passed"],3,r)
 def test_total(self):
  self.assertEqual(e.run()["total"],3)
if __name__=="__main__": unittest.main(verbosity=2)
