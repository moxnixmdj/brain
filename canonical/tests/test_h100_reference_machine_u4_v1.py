import unittest
from canonical.runtime import h100_reference_machine_u1 as u1
from canonical.runtime import h100_reference_machine_u4_v1 as u4
def P(v): return bytes([u1.OP["PUSH"]])+u1.encode_sleb(v)
def O(n): return bytes([u1.OP[n]])
class T(unittest.TestCase):
 def test_matches_u1_arithmetic(self):
  p=P(17)+P(23)+O("MUL")+O("WRITE")+O("HALT")
  self.assertEqual(u4.run(p)["output"],u1.run(p)["output"])
 def test_heap_and_input_match(self):
  p=P(0)+O("READ")+P(5)+O("SWAP")+O("STORE")+P(5)+O("LOAD")+O("WRITE")+O("HALT")
  self.assertEqual(u4.run(p,[99])["output"],[99])
 def test_large_integer_costs_more_bits(self):
  self.assertGreater(u4.int_bits(1<<1000),u4.int_bits(1))
 def test_live_bit_limit_blocks_giant_integer(self):
  p=P(1<<2000)+O("HALT")
  with self.assertRaisesRegex(u4.U4Error,"LIVE_BIT_LIMIT"): u4.run(p,max_live_bits=512)
 def test_same_program_passes_with_more_memory(self):
  p=P(1<<2000)+O("HALT")
  self.assertEqual(u4.run(p,max_live_bits=4096)["status"],"HALT")
 def test_peak_reported(self):
  p=P(7)+P(8)+O("ADD")+O("HALT")
  self.assertGreater(u4.run(p)["peak_live_bits"],0)
if __name__=="__main__": unittest.main(verbosity=2)
