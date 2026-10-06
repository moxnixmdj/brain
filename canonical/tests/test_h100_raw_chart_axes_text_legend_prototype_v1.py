import unittest
from canonical.runtime import h100_raw_chart_axes_text_legend_prototype_v1 as p
class T(unittest.TestCase):
 def test_discovery_holdout(self):
  r=p.run(); self.assertEqual((r["passed"],r["total"]),(4,4))
 def test_no_credit_label(self):
  self.assertIn("NO_GENERALIZATION",p.run()["hard_nonclaim"])
if __name__=="__main__": unittest.main(verbosity=2)
