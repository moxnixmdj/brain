import unittest
from canonical.runtime import h100_crosscap_g0_v1 as g

class T(unittest.TestCase):
 def test_csp(self):
  r=g.solve_finite_csp({"variables":["a","b"],"domains":{"a":[1,2],"b":[1,2]},"constraints":[{"op":"LT","vars":["a","b"]}]})
  self.assertEqual(r["status"],"UNIQUE")
  self.assertEqual(r["solutions"][0],{"a":1,"b":2})
 def test_synth(self):
  r=g.synthesize_unary_integer_program([{"x":x,"y":x*x+1} for x in (-2,-1,0,1,2)])
  self.assertEqual(r["status"],"PROGRAM_FOUND")
 def test_ppm(self):
  ppm="P3\n3 2\n255\n255 255 255 0 0 0 255 255 255 255 255 255 0 0 0 255 255 255\n"
  r=g.ppm_foreground_components(ppm)
  self.assertEqual(len(r["components"]),1)
  self.assertEqual(r["components"][0]["area"],2)
 def test_plan(self):
  r=g.plan_resources(["a"],"c",[{"operator_id":"x","requires":["a"],"provides":["b"]},{"operator_id":"y","requires":["b"],"provides":["c"]}])
  self.assertEqual(r["plan"],["x","y"])
 def test_snapshot(self):
  self.assertEqual(g.substrate_snapshot()["target_adapted_persistent_bits_for_future_suite"],0)
if __name__=="__main__": unittest.main(verbosity=2)
