from __future__ import annotations
from copy import deepcopy
from unittest.mock import patch
import unittest
from canonical.runtime import professional_quality_r2_root_subject_binding_verify_v1 as v

def base_binding():
 return {"schema":v.BINDING_SCHEMA,"root_id":v.ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,
 "subject":{"path":v.SUBJECT_PATH,"git_blob_sha":v.SUBJECT_BLOB},
 "bridge_evidence":{k:{"path":p,"git_blob_sha":s} for k,(p,s) in v.REFS.items()},
 "binding_scope":{"behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001","guarantees":sorted(v.REQUIRED_GUARANTEES),"limitations":sorted(v.REQUIRED_LIMITS)},
 "subject_refresh_required":False,"generator_is_external_root_support":True,"candidate_generator_inside_subject_required":False,
 "root_subject_binding_authority":False,"global_subject_identity_authority":False,"semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False}

def docs():
 return {
  v.BINDING_PATH:base_binding(),
  v.SUBJECT_PATH:{"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256},
  v.REFS["generator_basis"][0]:{"scope":{"global_candidate_completeness":False,"artifact_realization_completeness":False,"policy_adequacy_inferred":False}},
  v.REFS["generator_verification"][0]:{"status":"PASS__X","independent_reimplementation":{"structural_checks_run":14,"structural_checks_passed":14,"generated_branch_count":22,"unique_candidate_ids":22,"incumbent_branch_count":1,"deterministic_ids":True,"target_sensitive_universe":True,"incumbent_sensitive_universe":True}},
  v.REFS["search_semantics"][0]:{"limitations":["NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS"]},
  v.REFS["search_execution"][0]:{"limitations":["NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS"]},
  v.REFS["search_semantic_verification"][0]:{"status":"PASS__X"},
  v.REFS["search_execution_verification"][0]:{"status":"PASS__X"},
 }
def reader(table):
 def r(root,path,sha):
  return (deepcopy(table[path]),None) if path in table else (None,"MISSING:"+path)
 return r

class Tests(unittest.TestCase):
 def test_valid(self):
  t=docs()
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertTrue(o["pass"],o);self.assertTrue(o["root_subject_binding_authority"]);self.assertFalse(o["quality_authority"])
 def test_self_authority_fails(self):
  t=docs();t[v.BINDING_PATH]["root_subject_binding_authority"]=True
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertIn("BINDING_SELF_AUTHORITY_FORBIDDEN",o["reason"])
 def test_generator_global_overclaim_fails(self):
  t=docs();t[v.REFS["generator_basis"][0]]["scope"]["global_candidate_completeness"]=True
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertEqual(o["reason"],"GENERATOR_SCOPE_OVERCLAIM")
 def test_weak_generator_verification_fails(self):
  t=docs();t[v.REFS["generator_verification"][0]]["independent_reimplementation"]["unique_candidate_ids"]=21
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertEqual(o["reason"],"GENERATOR_VERIFICATION_INSUFFICIENT")
 def test_missing_search_limit_fails(self):
  t=docs();t[v.REFS["search_semantics"][0]]["limitations"]=[]
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertEqual(o["reason"],"SEARCH_SEMANTIC_SCOPE_TOO_BROAD")
 def test_subject_refresh_required_fails(self):
  t=docs();t[v.BINDING_PATH]["subject_refresh_required"]=True
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertEqual(o["reason"],"EXTERNAL_GENERATOR_BOUNDARY_INVALID")
 def test_missing_limitation_fails(self):
  t=docs();t[v.BINDING_PATH]["binding_scope"]["limitations"].remove("NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS")
  with patch.object(v,"_read",side_effect=reader(t)):o=v.verify()
  self.assertEqual(o["reason"],"BINDING_LIMITATIONS_INSUFFICIENT")

if __name__=="__main__":unittest.main()
