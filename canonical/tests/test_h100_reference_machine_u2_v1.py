import unittest
from canonical.runtime import h100_reference_machine_u2_v1 as u

class T(unittest.TestCase):
 def test_roundtrip(self):
  p=[("PUSH",-129),("STORE",2),("LOAD",2),("WRITE",),("HALT",)]
  self.assertEqual(u.decode(u.encode(p)),p)

 def test_arithmetic(self):
  p=[("PUSH",17),("PUSH",23),("MUL",),("PUSH",125),("SUB",),("PUSH",84),("PUSH",7),("FDIV",),("ADD",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p))["output"],(278,))

 def test_branch(self):
  p=[("READ",),("PUSH",5),("LT",),("JZ",7),("PUSH",1),("WRITE",),("JMP",9),("PUSH",0),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p),[3])["output"],(1,))
  self.assertEqual(u.execute(u.encode(p),[8])["output"],(0,))

 def test_signed_64_wrap(self):
  p=[("PUSH",(1<<63)-1),("PUSH",1),("ADD",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p))["output"],(-(1<<63),))

 def test_step_bound(self):
  p=[("JMP",0)]
  with self.assertRaisesRegex(u.U2Error,"STEP_LIMIT"): u.execute(u.encode(p),step_limit=5)

 def test_memory_bound(self):
  p=[("PUSH",7),("STORE",2),("HALT",)]
  with self.assertRaisesRegex(u.U2Error,"MEMORY_LIMIT"): u.execute(u.encode(p),memory_cells=2)

 def test_stack_bound(self):
  p=[("PUSH",1),("PUSH",2),("HALT",)]
  with self.assertRaisesRegex(u.U2Error,"STACK_LIMIT"): u.execute(u.encode(p),stack_limit=1)

 def test_output_bound(self):
  p=[("PUSH",1),("WRITE",),("PUSH",2),("WRITE",),("HALT",)]
  with self.assertRaisesRegex(u.U2Error,"OUTPUT_LIMIT"): u.execute(u.encode(p),output_limit=1)

 def test_deterministic(self):
  p=u.encode([("READ",),("PUSH",2),("MUL",),("WRITE",),("HALT",)])
  a=u.execute(p,[21],step_limit=10,memory_cells=8,stack_limit=8,output_limit=8)
  b=u.execute(p,[21],step_limit=10,memory_cells=8,stack_limit=8,output_limit=8)
  self.assertEqual(a,b)

if __name__=="__main__": unittest.main(verbosity=2)
