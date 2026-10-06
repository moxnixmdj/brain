import unittest
from canonical.runtime import h100_p0_generic_declarative_substrate_v1 as s
class T(unittest.TestCase):
 def test_conjunction(self):
  self.assertTrue(s.logic_forward(["A","B"],[{"all":["A","B"],"then":"C"},{"all":["C"],"then":"F"}],"F"))
 def test_delete_planner(self):
  o=s.plan(["TOKEN"],"DONE",[{"id":"TAKE","preconditions":["TOKEN"],"add":["ITEM"],"delete":["TOKEN"]},{"id":"USE","preconditions":["ITEM"],"add":["DONE"],"delete":["ITEM"]}])
  self.assertEqual(o["plan"],["TAKE","USE"])
 def test_mul_memory(self):
  self.assertEqual(s.reduce_events([{"op":"SET","key":"x","value":3},{"op":"MUL","key":"x","value":6}])["x"],18)
 def test_tool_objective(self):
  tools=[{"id":"S","effects":["WRITE"],"fields":["x"],"cost":9},{"id":"F","effects":["WRITE"],"fields":["x"],"cost":1}]
  self.assertEqual(s.select_tool("WRITE",["x"],tools,{"field":"cost","direction":"MIN"}),"F")
 def test_context_role(self):
  rel=[["q","INPUT"],["q","TARGET"]]
  self.assertEqual(s.lexical_role("q",rel,"USED_AS_OUTPUT"),"TARGET")
 def test_touching_bars(self):
  g=["..........","..##..##..","..##..##..","..######..","..##..##.."]
  self.assertEqual(len(s.segment_bars(g)),2)
 def test_string_shift(self):
  self.assertEqual(s.synthesize_string([("abc","bcd"),("def","efg")],"hij")["answer"],"ijk")
 def test_numeric(self):
  self.assertEqual(s.synthesize_numeric([(-2,9),(-1,3),(2,9),(3,19)],5)["answer"],51)
if __name__=="__main__":unittest.main(verbosity=2)
