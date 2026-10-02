from __future__ import annotations
import copy, unittest
from canonical.runtime import p1_v5_direct_surface_scope_superset_v1 as gate

class Tests(unittest.TestCase):
 def sources(self):
  return (gate._load(gate.P1_BINDING),gate._load(gate.MANIFEST),gate._load(gate.DIRECT_ROUTES),gate._load(gate.FOUR_CONTRACTS),
          gate._load(gate.V4_RESIDUAL),gate._load(gate.V5_RECEIPT),gate._load(gate.TERMINAL_WAVE))

 def historical_supersession(self):
  return {"status":"HISTORICAL_PRE_V6"}

 def test_live_v5_scope_gate_fails_closed_after_verified_v6_supersession(self):
  out=gate.evaluate()
  self.assertFalse(out["pass"],out)
  self.assertEqual(out["status"],"FAIL_CLOSED__V5_RESCUE_SUPERSEDED_BY_VERIFIED_V6")
  self.assertIn("V5_RESCUE_SUPERSEDED_BY_VERIFIED_V6",out["errors"])
  self.assertEqual(out["claim_bound_relations"],[])
  self.assertFalse(out["quarantine_lift_eligible"])
  self.assertEqual(out["new_reality_units_consumed"],0)

 def test_all_nine_frozen_mutations_are_executably_killed(self):
  a=gate._mutation_audit()
  self.assertTrue(a["all_frozen_mutations_killed"],a)
  self.assertEqual(set(a["results"]),gate.EXPECTED_MUTATIONS)
  self.assertTrue(all(a["results"].values()))

 def test_missing_surface_fails_closed(self):
  b,m,r,c,d,v,w=self.sources(); m=copy.deepcopy(m)
  m["portfolios"]["T0"]["surfaces"]=[x for x in m["portfolios"]["T0"]["surfaces"] if x.get("id")!="CURSORBENCH_4_0"]
  out=gate.evaluate(b,m,r,c,d,v,w,self.historical_supersession())
  self.assertFalse(out["pass"]); self.assertIn("MANIFEST_P1_SURFACE_SET_DRIFT",out["errors"])

 def test_v5_requires_independent_receipt(self):
  b,m,r,c,d,v,w=self.sources(); v=copy.deepcopy(v); v["status"]="CANDIDATE"
  out=gate.evaluate(b,m,r,c,d,v,w)
  self.assertFalse(out["pass"]); self.assertIn("V5_NOT_INDEPENDENT_PASS",out["errors"])

 def test_v4_residual_drift_fails_closed(self):
  b,m,r,c,d,v,w=self.sources(); d=copy.deepcopy(d)
  d["result"]["residual_obligations"]=["P1_EXPLICIT_SCOPE_FAILURE_CLASS"]
  out=gate.evaluate(b,m,r,c,d,v,w)
  self.assertFalse(out["pass"]); self.assertIn("V4_EXACT_RESIDUAL_SET_DRIFT",out["errors"])

 def test_terminal_receipt_contamination_fails_closed(self):
  b,m,r,c,d,v,w=self.sources(); w=copy.deepcopy(w)
  rows=w["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
  next(x for x in rows if x.get("behavior_id")==gate.BEHAVIOR)["tuning_replay"]=True
  out=gate.evaluate(b,m,r,c,d,v,w)
  self.assertFalse(out["pass"]); self.assertIn("TERMINAL_P1_RECEIPT_CONTAMINATED:T0:tuning_replay",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
