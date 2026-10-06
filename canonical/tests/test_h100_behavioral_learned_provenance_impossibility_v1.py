import unittest
from canonical.runtime import h100_behavioral_learned_provenance_impossibility_v1 as p
class T(unittest.TestCase):
 def test_linear_state_compiles_behavior_identically(self):
  state={"w":2.5,"b":-1.0}
  f=lambda s,x:s["w"]*x+s["b"]
  r=p.behavioral_equivalence(state,f,[-3,-1,0,2,9])
  self.assertTrue(r["all_equal"])
  self.assertEqual(r["compiled_accounted_learned_bytes"],0)
  self.assertTrue(r["state_information_still_embedded"])
 def test_symbolic_table_compiles_identically(self):
  state={"a":"INPUT","b":"TARGET"}
  f=lambda s,x:s[x]
  self.assertTrue(p.behavioral_equivalence(state,f,["a","b"])["all_equal"])
 def test_compiled_state_is_frozen_copy(self):
  state={"w":2}
  f=lambda s,x:s["w"]*x
  g=p.compile_state_into_program(state,f)
  state["w"]=99
  self.assertEqual(g(3),6)
 def test_invalid_interpreter(self):
  with self.assertRaises(p.ProvenanceImpossibilityError): p.compile_state_into_program({},3)
if __name__=="__main__": unittest.main(verbosity=2)
