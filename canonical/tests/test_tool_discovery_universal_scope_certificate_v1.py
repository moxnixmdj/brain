import copy,unittest
from canonical.runtime.tool_discovery_universal_scope_certificate_v1 import evaluate

PROPS={
 "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH":True,
 "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE":True,
 "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH":True,
 "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE":True,
 "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS":True,
 "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND":True,
 "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE":True,
}
def report():
 return {
  "pass":True,"property_results":dict(PROPS),"new_reality_units_consumed":1,
  "incremental_spend_usd":0,"capability_credit_delta":0,"family_credit_delta":0,
  "epoch_stable":True,"source_count":4,"union_unique_tool_identity_count":50000,
  "safe_probe_receipt":{"pass":True},
 }

class Tests(unittest.TestCase):
 def test_valid_interface_premise_closes_scope_candidate(self):
  out=evaluate(report())
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["universal_scope_proved"])
  self.assertFalse(out["execution_authority"])
 def test_missing_property_fails_closed(self):
  r=report(); r["property_results"]["SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND"]=False
  self.assertFalse(evaluate(r)["pass"])
 def test_toy_ecosystem_rejected(self):
  r=report(); r["union_unique_tool_identity_count"]=12
  out=evaluate(r)
  self.assertFalse(out["pass"])
  self.assertIn("INTERFACE_NOT_NONTRIVIAL_EXTERNAL_ECOSYSTEM",out["errors"])
 def test_nonzero_credit_or_spend_fails(self):
  r=report(); r["family_credit_delta"]=1
  self.assertFalse(evaluate(r)["pass"])
  r=report(); r["incremental_spend_usd"]=0.01
  self.assertFalse(evaluate(r)["pass"])

if __name__=="__main__": unittest.main(verbosity=2)
