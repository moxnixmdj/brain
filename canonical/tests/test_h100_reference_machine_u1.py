import unittest
from canonical.runtime import h100_reference_machine_u1 as u

def P(v): return bytes([u.OP["PUSH"]])+u.encode_sleb(v)
def O(name): return bytes([u.OP[name]])

class U1Tests(unittest.TestCase):
 def test_push_add_write(self):
  prog=P(7)+P(5)+O("ADD")+O("WRITE")+O("HALT")
  self.assertEqual(u.run(prog)["output"],[12])
 def test_read_two_sum(self):
  prog=P(0)+O("READ")+P(1)+O("READ")+O("ADD")+O("WRITE")+O("HALT")
  self.assertEqual(u.run(prog,[11,31])["output"],[42])
 def test_store_load(self):
  prog=P(9)+P(123)+O("STORE")+P(9)+O("LOAD")+O("WRITE")+O("HALT")
  self.assertEqual(u.run(prog)["output"],[123])
 def test_branch(self):
  # PUSH 0; JZ skips PUSH 99/WRITE; PUSH 7; WRITE; HALT
  tail=P(99)+O("WRITE")
  jz=O("JZ")+u.encode_sleb(len(tail))
  prog=P(0)+jz+tail+P(7)+O("WRITE")+O("HALT")
  self.assertEqual(u.run(prog)["output"],[7])
 def test_sleb_roundtrip(self):
  for v in (-100000,-65,-64,-1,0,1,63,64,127,128,999999):
   b=u.encode_sleb(v); got,pc=u.decode_sleb(b,0); self.assertEqual((got,pc),(v,len(b)))
 def test_bad_jump_fails_closed(self):
  prog=O("JMP")+u.encode_sleb(1)+O("HALT")
  with self.assertRaises(u.U1Error): u.run(prog)
 def test_div_zero_fails_closed(self):
  prog=P(1)+P(0)+O("FDIV")+O("HALT")
  with self.assertRaises(u.U1Error): u.run(prog)
 def test_step_limit(self):
  # JMP back to itself: immediate target = pc 0, next_pc 2 -> offset -2
  prog=O("JMP")+u.encode_sleb(-2)
  with self.assertRaises(u.U1Error): u.run(prog,max_steps=5)
if __name__=="__main__": unittest.main(verbosity=2)
