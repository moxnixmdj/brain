import unittest
from canonical.runtime import h100_u1_two_counter_compiler_v1 as c
from canonical.runtime import h100_reference_machine_u1 as u1

class T(unittest.TestCase):
 def test_increment_program(self):
  m={"q0":{"op":"INC","counter":0,"next":"q1"},"q1":{"op":"INC","counter":0,"next":"h"},"h":{"op":"HALT"}}
  r=c.compare(m,"q0",[(0,0),(3,4)])
  self.assertTrue(r["all_equal"])
  self.assertEqual(r["rows"][0]["u1"],[2,0])
  self.assertEqual(r["rows"][1]["u1"],[5,4])
 def test_transfer_loop(self):
  m={"q0":{"op":"DECJZ","counter":0,"nonzero":"q1","zero":"h"},"q1":{"op":"INC","counter":1,"next":"q0"},"h":{"op":"HALT"}}
  r=c.compare(m,"q0",[(0,4),(1,0),(7,2),(25,3)])
  self.assertTrue(r["all_equal"])
  self.assertEqual(r["rows"][-1]["u1"],[0,28])
 def test_nested_control(self):
  # Transfer c0 to c1, then transfer c1 back to c0. Final state equals input sum in c0.
  m={
    "a":{"op":"DECJZ","counter":0,"nonzero":"b","zero":"c"},
    "b":{"op":"INC","counter":1,"next":"a"},
    "c":{"op":"DECJZ","counter":1,"nonzero":"d","zero":"h"},
    "d":{"op":"INC","counter":0,"next":"c"},
    "h":{"op":"HALT"}
  }
  r=c.compare(m,"a",[(0,0),(2,3),(9,1)])
  self.assertTrue(r["all_equal"])
  self.assertEqual(r["rows"][2]["u1"],[10,0])
 def test_compiler_is_deterministic(self):
  m={"h":{"op":"HALT"}}
  self.assertEqual(c.compile_machine(m,"h"),c.compile_machine(m,"h"))
 def test_invalid_target_rejected(self):
  m={"q":{"op":"INC","counter":0,"next":"missing"}}
  with self.assertRaises(c.TwoCounterCompilerError): c.compile_machine(m,"q")
 def test_output_program_decodes_under_u1(self):
  m={"h":{"op":"HALT"}}
  u1.decode_program(c.compile_machine(m,"h"))
if __name__=="__main__": unittest.main(verbosity=2)
