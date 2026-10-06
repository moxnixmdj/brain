import unittest
from canonical.runtime import h100_u3_bar_fresh_holdout_generator_v1 as g
class T(unittest.TestCase):
 def test_deterministic(self):
  self.assertEqual(g.generate(),g.generate())
 def test_case_count_and_orientations(self):
  rows=g.generate()
  self.assertEqual(len(rows),10)
  self.assertEqual([x["gold"][0] for x in rows],[0,1,0,1,0,1,0,1,0,1])
 def test_input_shape(self):
  for x in g.generate():
   self.assertEqual(len(x["input"]),2+x["height"]*x["width"])
 def test_top_left_background_implicit(self):
  for x in g.generate():
   self.assertGreaterEqual(len(x["input"]),3)
if __name__=="__main__": unittest.main(verbosity=2)
