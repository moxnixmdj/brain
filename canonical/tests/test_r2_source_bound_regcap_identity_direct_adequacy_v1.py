from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_source_bound_regcap_identity_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as v19
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fp
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

def goal(path="canonical/tmp/ccob.json"):
 return ('Identify the regulatory-capital concept for "loss-absorbing cushion" in '
  'source NYFED_DUDLEY_BASEL_2010_10_10 and save the verified concept identity to '
  +path+'.')

def producer_ok():
 return {"pass":True,"mapped_concept_id":regcap.CCOB,
  "semantic_truth_authority":True,"global_phrase_identity_authority":False}

def independent_ok(root):
 return {"producer_independent":True,"verified":True,
  "mapped_concept_id":regcap.CCOB,"source_id":d.identity.SOURCE_ID,
  "exact_surface":d.identity.EXACT_SURFACE,"source_receipt_sha256":"a"*64}

class Tests(unittest.TestCase):
 def test_exact_case_closes_with_independent_acceptance(self):
  with tempfile.TemporaryDirectory() as td, patch.object(d.identity,"verify",return_value=producer_ok()):
   root=Path(td)
   out=d.run({"task_id":"x","goal":goal()},repo_root=root,independent_provider=independent_ok)
   self.assertTrue(out["pass"],out)
   self.assertEqual(out["mapped_concept_id"],regcap.CCOB)
   self.assertTrue(out["semantic_acceptance_complete"])
   self.assertTrue(out["actual_goal_satisfaction_verified"])
   self.assertTrue(out["direct_adequacy_authority"])
   self.assertFalse(out["terminal_authority"])
   saved=json.loads((root/"canonical/tmp/ccob.json").read_text())
   self.assertFalse(saved["global_phrase_identity_authority"])
   self.assertFalse(saved["open_world_ontology_complete"])

 def test_nonmatching_goal_is_not_applicable(self):
  out=d.preflight({"task_id":"x","goal":"What is a loss-absorbing cushion?"})
  self.assertFalse(out["matched"])
  self.assertEqual(out["status"],"NOT_APPLICABLE")

 def test_independent_disagreement_rolls_back(self):
  with tempfile.TemporaryDirectory() as td, patch.object(d.identity,"verify",return_value=producer_ok()):
   root=Path(td); p=root/"canonical/tmp/ccob.json"; p.parent.mkdir(parents=True)
   p.write_text('{"old":true}\n'); old=p.read_bytes()
   bad=lambda _root:{**independent_ok(_root),"mapped_concept_id":regcap.CCYB}
   out=d.run({"task_id":"x","goal":goal()},repo_root=root,independent_provider=bad)
   self.assertFalse(out["pass"],out)
   self.assertTrue(out["rollback_complete"])
   self.assertEqual(p.read_bytes(),old)

 def test_producer_failure_never_calls_independent_provider(self):
  called={"n":0}
  def independent(_root):
   called["n"]+=1
   return independent_ok(_root)
  with tempfile.TemporaryDirectory() as td, patch.object(d.identity,"verify",return_value={"pass":False}):
   out=d.run({"task_id":"x","goal":goal()},repo_root=Path(td),independent_provider=independent)
  self.assertFalse(out["pass"])
  self.assertEqual(called["n"],0)

 def test_v19_delegates_unrelated_request_to_v18(self):
  request={"task_id":"x","goal":"Unrelated task."}
  expected={"matched":False,"status":"V18"}
  with patch.object(v19.v18,"preflight",return_value=expected) as prior:
   out=v19.preflight(request)
  self.assertEqual(out,expected)
  prior.assert_called_once()

 def test_v19_selects_source_bound_route_before_v18(self):
  request={"task_id":"x","goal":goal()}
  with patch.object(v19.v18,"preflight") as prior:
   out=v19.preflight(request)
  self.assertTrue(out["matched"],out)
  self.assertEqual(out["route_id"],d.ROUTE_ID)
  prior.assert_not_called()

 def test_fixed_point_uses_v19_and_closes_exact_route(self):
  request={"task_id":"x","goal":goal()}
  direct={"pass":True,"matched":True,"status":"PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
   "route_id":d.ROUTE_ID,"execution_attempted":True}
  with patch.object(fp.direct_adequacy,"preflight",return_value={"matched":True,"route_id":d.ROUTE_ID}), patch.object(
   fp.direct_adequacy,"run",return_value=direct):
   out=fp.run(request)
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["r2_fixed_point_status"],"PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED")
  self.assertEqual(out["r2_fixed_point_trace"][0]["route_id"],d.ROUTE_ID)

if __name__=="__main__":
 unittest.main(verbosity=2)
