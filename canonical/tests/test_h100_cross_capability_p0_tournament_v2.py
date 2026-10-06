import json,unittest
from canonical.runtime import h100_cross_capability_p0_tournament_v2 as t
class T(unittest.TestCase):
 def test_boundary(self):
  s=json.loads(t.PRE.read_text()); self.assertTrue(all("gold" in x and "gold" not in x["public_input"] for x in s["tasks"]))
 def test_raw_vision_has_no_latent_bar_metadata(self):
  s=json.loads(t.PRE.read_text()); v=[x for x in s["tasks"] if x["family"]=="RASTER_VISION"][0]["public_input"]
  self.assertIn("rows",v); self.assertNotIn("bars",v)
 def test_eight_public_tasks(self):
  r=t.run(); self.assertEqual(r["nonsealed_passed"],8)
 def test_sealed(self):
  r=t.run(); self.assertTrue(r["sealed_control_pass"]); self.assertEqual(r["max_observed_information_lower_bound_bits"],2)
 def test_zero_target_bits(self):
  self.assertEqual(t.run()["target_adapted_persistent_bits"],0)
if __name__=="__main__": unittest.main(verbosity=2)
