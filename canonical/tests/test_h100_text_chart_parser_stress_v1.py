import unittest
from canonical.runtime import h100_text_chart_parser_stress_v1 as s
class T(unittest.TestCase):
 def test_parser_is_unchanged_subject(self):
  self.assertFalse(s.run()["parser_modified"])
 def test_stress_runs_all_three(self):
  self.assertEqual(s.run()["total"],3)
if __name__=="__main__": unittest.main(verbosity=2)
