from __future__ import annotations
import copy,json,unittest
from canonical.runtime.p1_shared_failure_semantics_batch_freeze_v1 import FREEZE,evaluate

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.base=json.loads(FREEZE.read_text())
 def test_live_freeze_passes_without_execution_authority(self):
  out=evaluate(self.base); self.assertTrue(out["status"].startswith("PASS"),out)
  self.assertFalse(out["execution_ready"]); self.assertFalse(out["execution_authority"])
  self.assertTrue(out["three_surface_mapping_frozen"])
  self.assertTrue(out["failure_semantics_normalizer_frozen"])
 def test_missing_surface_fails(self):
  x=copy.deepcopy(self.base); x["surface_slots"]=x["surface_slots"][:2]
  self.assertEqual(evaluate(x)["status"],"FAIL_CLOSED")
 def test_missing_semantics_rule_fails(self):
  x=copy.deepcopy(self.base); x["normalization_contract"]["failure_semantics_required_on_every_failed_check"]=False
  self.assertEqual(evaluate(x)["status"],"FAIL_CLOSED")
 def test_prebeacon_selection_fails(self):
  x=copy.deepcopy(self.base); x["selection_contract"]["case_selection_before_beacon"]=True
  self.assertEqual(evaluate(x)["status"],"FAIL_CLOSED")
 def test_partial_promotion_fails(self):
  x=copy.deepcopy(self.base); x["acceptance_rule"]["promotion_from_partial_batch"]=True
  self.assertEqual(evaluate(x)["status"],"FAIL_CLOSED")
 def test_commitment_mutation_fails(self):
  x=copy.deepcopy(self.base); x["scoring_contract"]["required_outcomes"].append("INVENTED")
  self.assertIn("PACKAGE_COMMITMENT_MISMATCH",evaluate(x)["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
