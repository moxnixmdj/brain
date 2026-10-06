import unittest
from canonical.runtime import h100_capability_information_relocation_bound_v1 as r
class T(unittest.TestCase):
 def test_eight(self): self.assertEqual(r.class_bits(8),3)
 def test_relocation(self): self.assertTrue(all(x["sufficient"] for x in r.relocation_example(8,3)))
 def test_insufficient(self):
  self.assertFalse(r.total_capacity_sufficient(8,0,2,0))
  self.assertEqual(r.minimum_missing_bits(8,0,2,0),1)
 def test_symmetric(self):
  self.assertTrue(r.total_capacity_sufficient(16,1,1,2))
  self.assertTrue(r.total_capacity_sufficient(16,0,4,0))
  self.assertTrue(r.total_capacity_sufficient(16,4,0,0))
if __name__=="__main__": unittest.main(verbosity=2)
