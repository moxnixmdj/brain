from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from canonical.runtime.post_recovery_matched_child_receipt_miner_v1 import build_index

TARGETS=[
"AGENCY_MATCHED_SUCCESS_NONINFERIOR","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
"COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
"IF_SCOPE_BOUNDARY_NONINFERIOR","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","VISION_DENSE_NONCHART_SCOPE"]

def doc():
 return {"implications":[{"then":[t],"if_all":[
  t+"::WITNESS_TARGET_SEMANTIC_BINDING_INDEPENDENT_PASS",
  t+"::WITNESS_TARGET_EXACT_OR_SUPERSET_SCOPE_RELATION_INDEPENDENT_PASS"]} for t in TARGETS]}

class MinerTests(unittest.TestCase):
 def root(self):
  td=tempfile.TemporaryDirectory(); r=Path(td.name)
  for p in ["canonical/governance","canonical/verification","canonical/capabilities"]:
   (r/p).mkdir(parents=True)
  (r/"canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json").write_text(json.dumps(doc()))
  return td,r

 def test_16_and_zero_credit(self):
  td,r=self.root()
  try:
   o=build_index(root=r)
   self.assertEqual(o["child_fact_count"],16)
   self.assertTrue(all(x["proved"] is False for x in o["facts"]))
   self.assertEqual(o["new_reality_units_consumed"],0)
   self.assertFalse(o["execution_authority"]); self.assertFalse(o["promotion_authority"])
  finally: td.cleanup()

 def test_self_restatement_excluded_and_receipt_candidate_only(self):
  td,r=self.root()
  try:
   t=TARGETS[0]; prop=t+"::WITNESS_TARGET_SEMANTIC_BINDING_INDEPENDENT_PASS"
   (r/"canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").write_text(json.dumps({"requires":[prop]}))
   (r/"canonical/verification/x.json").write_text(json.dumps({"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","target_predicate_id":t,"semantic":"binding witness"}))
   o=build_index(root=r); row=next(x for x in o["facts"] if x["proposition"]==prop)
   self.assertEqual(row["exact_fact_occurrence_count"],0)
   self.assertGreaterEqual(row["candidate_receipt_count"],1)
   self.assertTrue(row["candidate_receipts"][0]["candidate_only"])
   self.assertFalse(row["proved"])
  finally: td.cleanup()

if __name__=="__main__": unittest.main(verbosity=2)
