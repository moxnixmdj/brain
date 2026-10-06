import unittest
from canonical.runtime import h100_crosscap_g1_v1 as g
class T(unittest.TestCase):
 def test_poly_cubic(self):
  r=g.synthesize_polynomial([{"x":x,"y":x**3+2} for x in range(-3,4)],3)
  self.assertEqual(r["degree"],3); self.assertEqual(g.predict_polynomial(r,4),66)
 def test_color_touching(self):
  p="P3\n2 1\n255\n10 20 30 30 20 10\n"
  self.assertEqual(len(g.ppm_color_components(p)["components"]),2)
 def test_metadata_tool(self):
  t={"tool_packs":[{"tool_id":"a","input_schema":{"x":"int"},"effects":["WRITE"],"purpose":"p"},{"tool_id":"b","input_schema":{"x":"int"},"effects":["WRITE"],"purpose":"q"}],"required_effect":"WRITE","required_keys":["x"],"purpose":"p"}
  self.assertEqual(g.select_tool(t)["matches"][0]["tool_id"],"a")
 def test_nonmonotonic_plan(self):
  t={"initial_resources":["s"],"goal_resource":"g","required_final_resources":["g","k"],"operators":[{"operator_id":"a","requires":["s"],"provides":["k"]},{"operator_id":"b","requires":["k"],"provides":["g"],"removes":["k"]},{"operator_id":"c","requires":["s"],"provides":["sp"]},{"operator_id":"d","requires":["sp","g"],"provides":["k"]}]}
  self.assertEqual(g.plan_nonmonotonic(t)["status"],"PLAN_FOUND")
 def test_history(self):
  self.assertEqual(g.query_history([{"op":"SET","key":"x","value":2},{"op":"SET","key":"x","value":9}],{"op":"MAX_SEEN","key":"x"}),9)
 def test_basis(self):
  rows=[{"x":x,"y":.2+.3*x+1.1*__import__("math").exp(-abs(x))} for x in (-3,-2,-1,0,1,2,3)]
  r=g.resolve_generic_numeric(rows); self.assertEqual(r["status"],"CAPABILITY_HIT__VERIFY_BEFORE_USE")
if __name__=="__main__": unittest.main(verbosity=2)
