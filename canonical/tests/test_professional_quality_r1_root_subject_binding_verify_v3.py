from __future__ import annotations
from copy import deepcopy
from unittest.mock import patch
import unittest
from canonical.runtime import professional_quality_r1_root_subject_binding_verify_v3 as v

def binding():
 return {"schema":v.BINDING_SCHEMA,"root_id":v.ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":v.SUBJECT_ID,
 "subject_sha256":v.SUBJECT_SHA256,"subject":{"path":v.SUBJECT_PATH,"git_blob_sha":v.SUBJECT_BLOB},
 "bridge_evidence":{k:{"path":p,"git_blob_sha":s} for k,(p,s) in v.EXPECTED_REFS.items()},
 "binding_scope":{"behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001","guarantees":sorted(v.REQUIRED_GUARANTEES),"limitations":sorted(v.REQUIRED_LIMITS)},
 "root_subject_binding_authority":False,"global_subject_identity_authority":False,"terminal_authority":False}

def subject():
 return {"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,"system_material":{"components":[{"path":p,"git_blob_sha":s} for p,s in sorted(v.REQUIRED_MATERIAL)]}}

def docs():
 return {
  v.BINDING_PATH:binding(),v.SUBJECT_PATH:subject(),
  v.EXPECTED_REFS["subject_verification"][0]:{"real_subject_replay":{"pass":True,"component_count":20,"component_currentness_verified":True,"subject_identity_verified":True},"authority":{"root_subject_binding_authority":False}},
  v.EXPECTED_REFS["v6_minimal_binding_kernel"][0]:{"replay":{"kernel_equivalence":{"tests_passed":7},"router_v6":{"tests_passed":10},"real_integration":{"cases_passed":2}},"proved":sorted(v.REQUIRED_V6_PROOFS)},
  v.EXPECTED_REFS["authenticated_target_handoff"][0]:{"replay":{"total_tests_passed":31,"total_tests_failed":0},"producer_id":"producer-a","independent_verifier":{"independent_verifier_id":"verifier-b"},"proves":sorted(v.REQUIRED_HANDOFF_PROOFS)},
  v.EXPECTED_REFS["r1_target_semantics"][0]:{"replay":{"tests_passed":5},"claim_scope":{"kind":"EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS","limitations":["NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS"]}},
  v.EXPECTED_REFS["r1_structural_target"][0]:{"replay":{"tests_passed":21},"current_truth":{"semantic_truth_closed":False}},
 }
def reader(table):
 def _read(root,path,sha):
  if path not in table:return None,"MISSING:"+path
  return deepcopy(table[path]),None
 return _read

class VerifyV3Tests(unittest.TestCase):
 def test_valid(self):
  t=docs()
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertTrue(out["pass"],out);self.assertTrue(out["root_subject_binding_authority"]);self.assertFalse(out["quality_authority"])
 def test_self_authority_fails(self):
  t=docs();t[v.BINDING_PATH]["root_subject_binding_authority"]=True
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertIn("BINDING_SELF_AUTHORITY_FORBIDDEN",out["reason"])
 def test_missing_v6_material_fails(self):
  t=docs();t[v.SUBJECT_PATH]["system_material"]["components"]=[x for x in t[v.SUBJECT_PATH]["system_material"]["components"] if x["path"]!="canonical/runtime/professional_quality_p1_router_v6.py"]
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertEqual(out["reason"],"R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")
 def test_weak_v6_replay_fails(self):
  t=docs();t[v.EXPECTED_REFS["v6_minimal_binding_kernel"][0]]["replay"]["router_v6"]["tests_passed"]=9
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertEqual(out["reason"],"V6_REPLAY_INSUFFICIENT")
 def test_same_producer_verifier_fails(self):
  t=docs();h=t[v.EXPECTED_REFS["authenticated_target_handoff"][0]];h["producer_id"]="same";h["independent_verifier"]["independent_verifier_id"]="same"
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertEqual(out["reason"],"HANDOFF_INDEPENDENCE_INVALID")
 def test_missing_guarantee_fails(self):
  t=docs();t[v.BINDING_PATH]["binding_scope"]["guarantees"].remove("FINAL_DECLARED_SYSTEM_SUBJECT_IS_CONTENT_ADDRESSED_AND_DEPENDENCY_CLOSED")
  with patch.object(v,"_read",side_effect=reader(t)):out=v.verify()
  self.assertEqual(out["reason"],"BINDING_GUARANTEES_INSUFFICIENT")
if __name__=="__main__":unittest.main()
