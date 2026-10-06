import unittest
from canonical.runtime import h100_conditional_bounded_capability_complexity_v1 as c
class T(unittest.TestCase):
 def test_interval(self):
  self.assertEqual(c.interval(3,10,time_budget=100,memory_bytes=1000)["gap_bits"],7)
 def test_tighten(self):
  x=c.interval(0,100,time_budget=10,memory_bytes=20)
  y=c.tighten(x,new_lower_bits=8,new_upper_bits=60)
  self.assertEqual((y["lower_bits"],y["upper_bits"]),(8,60))
 def test_representation_invariant(self):
  self.assertEqual(c.representation_invariant_total(learned_bits=800,deterministic_bits=0),c.representation_invariant_total(learned_bits=0,deterministic_bits=800))
 def test_explicit_program_upper_bound(self):
  self.assertEqual(c.explicit_upper_bound(3584),28672)
 def test_invalid_interval(self):
  with self.assertRaises(c.ComplexityBoundError): c.interval(9,8,time_budget=1,memory_bytes=1)
 def test_record_never_claims_exact(self):
  r=c.record("vision-bars","U1","raw-raster",lower_bits=0,upper_bits=28672,time_budget=1000,memory_bytes=1000000)
  self.assertFalse(r["exact_complexity_claimed"])
if __name__=="__main__": unittest.main(verbosity=2)
