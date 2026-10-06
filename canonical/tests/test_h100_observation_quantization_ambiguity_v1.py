import unittest
from canonical.runtime import h100_observation_quantization_ambiguity_v1 as a
class T(unittest.TestCase):
 def test_half_scale_preimages(self):
  self.assertEqual(a.integer_preimage(2,0.5,0,30),[3,4,5])
  self.assertEqual(a.integer_preimage(4,0.5,0,30),[7,8,9])
  self.assertEqual(a.integer_preimage(5,0.5,0,30),[10])
 def test_joint_chart_class(self):
  hs=[2,5,2,4,1,6]
  self.assertEqual(a.joint_class_size(hs,0.5,0,30),81)
  self.assertEqual(a.missing_instance_bits(hs,0.5,0,30),7)
 def test_unit_scale_is_injective_on_integer_heights(self):
  for h in range(0,16):
   self.assertEqual(a.integer_preimage(h,1.0,0,30),[h])
 def test_capability_delta_zero(self):
  c=a.certificate([2,5,2,4,1,6],0.5,0,30)
  self.assertEqual(c["persistent_capability_bits_lower_bound_delta"],0)
if __name__=="__main__": unittest.main(verbosity=2)
