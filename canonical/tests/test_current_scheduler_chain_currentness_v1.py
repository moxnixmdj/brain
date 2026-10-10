import json,unittest
from pathlib import Path
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as adapter

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class T(unittest.TestCase):
 def test_live_planner_reconciles_supported_current_pointer_drift(self):
  frontier=load("canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json")
  professional=load(adapter.PROF_SOURCE)["property_truth_frontier"]
  bytes_state=load(adapter.BYTES_SOURCE)["exact_symbolic_state"]
  refreshed,p,b=adapter._refresh_supported_sources(frontier)
  self.assertEqual(p["closed"],professional["verified_leaf_count"])
  self.assertEqual(p["open_exec"],professional["open_execution_leaf_count"])
  self.assertEqual(p["open_sem"],professional["open_semantic_leaf_count"])
  self.assertEqual(b["raw"],bytes_state["raw_python_source_bytes"])
  self.assertEqual(adapter._assert_post_composition(refreshed)["closed"],p["closed"])
  current=adapter.core.verify_frontier_currentness(refreshed,root=ROOT)
  self.assertTrue(current["currentness_verified"])
  out=adapter.plan_current_post_composition_frontier()
  self.assertTrue(out["dynamic_professional_currentness_verified"])
  self.assertTrue(out["dynamic_bytes_currentness_verified"])
  self.assertEqual(out["professional_property_truth_closed_count"],p["closed"])
  self.assertEqual(out["bytes_raw_python_source_bytes"],b["raw"])
  self.assertFalse(out["execution_authority"])
  self.assertFalse(out["promotion_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)
