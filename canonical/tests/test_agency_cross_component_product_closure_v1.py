import unittest
from canonical.runtime.agency_cross_component_product_closure_v1 import verify_product

D=["multi-step planning with at least three distinct tool/action types","state change after actions requiring replanning","long-horizon state retention","tool failure/recovery","subtask dependency and fan-in","minimal-oversight completion"]
M=["terminal_task_success","invalid_action_rate","unrecovered_failure_rate","duplicate_or_conflicting_work_rate"]

def base():
 return {"covered_dimensions":D,"covered_metrics":M,"identity":{"agent_id":"A","task_id":"T","mission_id":"M"},"initial_facts":["m"],"target_facts":["z"],"resource_capacities":{"r":1},"recovery_scope_complete_for_declared_failures":True,"fail_closed_before_next_material_action":True,"current_receipt_replan_required":True,"required_terminal_evidence":["e1","e2","e3"],"stages":[
 {"id":"a","action_type":"browser","requires":["m"],"provides":["x"],"writes":["r"],"evidence":["e1"],"wave":0,"reads_state_version":0,"emits_state_version":1,"outcome":"PASS","checkpoint":{"agent_id":"A","task_id":"T","mission_id":"M","revalidated_current_context":True}},
 {"id":"b","action_type":"tool","requires":["x"],"provides":["y"],"writes":[],"evidence":["e2"],"wave":1,"reads_state_version":1,"emits_state_version":2,"outcome":"PASS"},
 {"id":"c","action_type":"delegate","requires":["y"],"provides":["z"],"writes":[],"evidence":["e3"],"wave":2,"reads_state_version":2,"emits_state_version":3,"outcome":"PASS"}]}

class T(unittest.TestCase):
 def test_pass(self):
  self.assertTrue(verify_product(base())["pass"])
 def test_stale_fails(self):
  x=base();x["stages"][1]["reads_state_version"]=0
  self.assertIn("STALE_STATE_READ:b",verify_product(x)["errors"])
 def test_identity_fails(self):
  x=base();x["stages"][0]["checkpoint"]["agent_id"]="B"
  self.assertIn("CHECKPOINT_IDENTITY_DRIFT:a",verify_product(x)["errors"])
 def test_dimension_fails(self):
  x=base();x["covered_dimensions"]=D[:-1]
  self.assertIn("DIMENSION_COVERAGE_MISMATCH",verify_product(x)["errors"])

if __name__=="__main__":unittest.main()
