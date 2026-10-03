from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.tool_discovery_acceptance_reduction_v1 import (
 EXPECTED_SCOPE_BLOBS,TARGET,evaluate,
)
ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())

def receipt():
 return {
  "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TOOL_DISCOVERY_UNIVERSAL_FORMAL_SCOPE__ZERO_CREDIT",
  "source_brain_pr":1133,
  "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "target_proof_atom":"INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL",
  "exact_brain_blobs":dict(EXPECTED_SCOPE_BLOBS),
  "public_runner":{"conclusion":"success"},
  "result":{"universal_scope_proved":True,"scope_atom_satisfied_candidate":True,"basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF"},
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
 }

class Tests(unittest.TestCase):
 def setUp(self):
  self.protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
  self.tool=load("canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json")
  self.deleg=load("canonical/governance/OPUS55_DELEGATION_SCOPE_COMPLETE_ACCEPTANCE_INPUT_V1.json")
 def test_valid_receipt_compiles_exactly_four_families(self):
  out=evaluate(receipt(),self.protocols,self.tool,self.deleg)
  self.assertTrue(out["promotion_eligible"],out)
  self.assertEqual(len(out["closed_families"]),4)
  self.assertEqual(out["newly_closed_families"],[TARGET])
  self.assertEqual(out["compiled"]["open_family_count"],15)
 def test_blob_drift_fails(self):
  r=receipt(); r["exact_brain_blobs"][next(iter(EXPECTED_SCOPE_BLOBS))]="bad"
  self.assertFalse(evaluate(r,self.protocols,self.tool,self.deleg)["promotion_eligible"])
 def test_nonzero_reality_fails(self):
  r=receipt(); r["new_reality_units_consumed"]=1
  self.assertFalse(evaluate(r,self.protocols,self.tool,self.deleg)["promotion_eligible"])
 def test_wrong_target_fails(self):
  r=receipt(); r["source_brain_pr"]=1
  self.assertFalse(evaluate(r,self.protocols,self.tool,self.deleg)["promotion_eligible"])
 def test_scope_false_fails(self):
  r=receipt(); r["result"]["universal_scope_proved"]=False
  self.assertFalse(evaluate(r,self.protocols,self.tool,self.deleg)["promotion_eligible"])

if __name__=="__main__":unittest.main(verbosity=2)
