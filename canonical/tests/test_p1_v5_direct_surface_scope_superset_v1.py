from __future__ import annotations
import copy, unittest
from canonical.runtime import p1_v5_direct_surface_scope_superset_v1 as gate

class Tests(unittest.TestCase):
 def sources(self):
  return (gate._load(gate.P1_BINDING),gate._load(gate.MANIFEST),gate._load(gate.DIRECT_ROUTES),gate._load(gate.FOUR_CONTRACTS),
          gate._load(gate.V4_RESIDUAL),gate._load(gate.V5_RECEIPT),gate._load(gate.TERMINAL_WAVE))

 def test_live_scope_relation_passes_without_private_population_claim(self):
  out=gate.evaluate()
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["surface_count"],3)
  self.assertEqual(set(out["surfaces"]),gate.EXPECTED_SURFACES)
  self.assertIn("SUPERSET_OF_FROZEN_P1_DIRECT_PROOF_CONTRACT_SEMANTICS",out["scope_relation"])
  self.assertFalse(out["private_benchmark_population_scope_claimed"])
  self.assertEqual(len(out["claim_bound_relations"]),3)
  self.assertEqual({x["direct_surface"] for x in out["claim_bound_relations"]},gate.EXPECTED_SURFACES)
  self.assertEqual(len({x["claim_id"] for x in out["claim_bound_relations"]}),3)
  self.assertTrue(all(x["relation"]=="SUPERSET" for x in out["claim_bound_relations"]))
  self.assertTrue(all(x["private_benchmark_population_scope_claimed"] is False for x in out["claim_bound_relations"]))
  self.assertFalse(out["quarantine_lift_eligible"])
  self.assertEqual(out["new_reality_units_consumed"],0)
  self.assertEqual(out["terminal_receipts_preserved"]["terminal_results_replayed"],0)

 def test_all_nine_frozen_mutations_are_executably_killed(self):
  a=gate._mutation_audit()
  self.assertTrue(a["all_frozen_mutations_killed"],a)
  self.assertEqual(set(a["results"]),gate.EXPECTED_MUTATIONS)
  self.assertTrue(all(a["results"].values()))

 def test_missing_surface_fails_closed(self):
  b,m,r,c,d,v,w=self.sources(); m=copy.deepcopy(m)
  m["portfolios"]["T0"]["surfaces"]=[x for x in m["portfolios"]["T0"]["surfaces"] if x.get("id")!="CURSORBENCH_4_0"]
  out=gate.evaluate(b,m,r,c,d,v,w)
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
