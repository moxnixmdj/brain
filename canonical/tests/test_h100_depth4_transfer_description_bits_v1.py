import unittest
from canonical.runtime import h100_depth4_transfer_description_bits_v1 as d
class T(unittest.TestCase):
 def test_structure_bits(self):
  self.assertEqual((1554-1).bit_length(),11)
 def test_all_tasks_meet_gate(self):
  r=d.run()
  self.assertEqual(len(r["rows"]),3)
  self.assertTrue(all(x["nrmse"]<=1e-8 for x in r["rows"]))
 def test_description_positive(self):
  self.assertTrue(all(x["target_adapted_description_bits"]>=17 for x in d.run()["rows"]))
 def test_zero_learned_provenance(self):
  self.assertEqual(d.run()["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
