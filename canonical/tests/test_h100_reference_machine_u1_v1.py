import unittest
from canonical.runtime import h100_reference_machine_u1_v1 as u
class T(unittest.TestCase):
 def test_roundtrip(self):
  p=[("PUSH",-129),("STORE",2),("LOAD",2),("WRITE",),("HALT",)]
  self.assertEqual(u.decode(u.encode(p)),p)
 def test_arithmetic(self):
  p=[("PUSH",17),("PUSH",23),("MUL",),("PUSH",125),("SUB",),("PUSH",84),("PUSH",7),("FDIV",),("ADD",),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p))["output"],[278])
 def test_branch(self):
  p=[("READ",),("PUSH",5),("LT",),("JZ",6),("PUSH",1),("WRITE",),("JMP",8),("PUSH",0),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p),[3])["output"],[1])
  self.assertEqual(u.execute(u.encode(p),[8])["output"],[0])
 def test_loop(self):
  p=[("READ",),("STORE",0),("PUSH",0),("STORE",1),("PUSH",1),("STORE",2),("LOAD",0),("LOAD",2),("LT",),("JZ",11),("JMP",20),("LOAD",1),("LOAD",2),("ADD",),("STORE",1),("LOAD",2),("PUSH",1),("ADD",),("STORE",2),("JMP",6),("LOAD",1),("WRITE",),("HALT",)]
  self.assertEqual(u.execute(u.encode(p),[5],step_limit=1000)["output"],[15])
 def test_fail_closed(self):
  with self.assertRaises(u.U1Error): u.execute(u.encode([("JMP",0)]),step_limit=5)
if __name__=="__main__": unittest.main(verbosity=2)
