import unittest
from canonical.runtime import h100_reference_machine_u3_v1 as u
class T(unittest.TestCase):
 def test_roundtrip(self):
  p=[("PUSH",-9),("LOADIND",),("HALT",)]
  self.assertEqual(u.decode(u.encode(p)),p)
 def test_indirect_memory(self):
  p=[("PUSH",3),("PUSH",99),("STOREIND",),("PUSH",3),("LOADIND",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p),memory_cells=8)["output"],(99,))
 def test_input_length(self):
  p=[("INLEN",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p),[1,2,3])["output"],(3,))
 def test_arithmetic(self):
  p=[("PUSH",17),("PUSH",23),("MUL",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p))["output"],(391,))
 def test_bounds(self):
  with self.assertRaisesRegex(u.U3Error,"MEMORY_LIMIT"): u.execute(u.encode([("PUSH",99),("LOADIND",),("HALT",)]),memory_cells=8)
  with self.assertRaisesRegex(u.U3Error,"STEP_LIMIT"): u.execute(u.encode([("JMP",0)]),step_limit=4)
  with self.assertRaisesRegex(u.U3Error,"STACK_LIMIT"): u.execute(u.encode([("PUSH",1),("PUSH",2),("HALT",)]),stack_limit=1)
  with self.assertRaisesRegex(u.U3Error,"OUTPUT_LIMIT"): u.execute(u.encode([("PUSH",1),("WRITE",),("PUSH",2),("WRITE",),("HALT",)]),output_limit=1)
 def test_deterministic(self):
  p=u.encode([("READ",),("PUSH",5),("ADD",),("WRITE",),("HALT",)])
  a=u.execute(p,[7],step_limit=10,memory_cells=8,stack_limit=8,output_limit=8)
  b=u.execute(p,[7],step_limit=10,memory_cells=8,stack_limit=8,output_limit=8)
  self.assertEqual(a,b)
if __name__=="__main__": unittest.main(verbosity=2)
