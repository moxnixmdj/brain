from copy import deepcopy
from unittest.mock import patch
import unittest
from canonical.runtime import professional_quality_r2_root_subject_binding_verify_v1 as v

def binding():
 return {"schema":v.BINDING_SCHEMA,"root_id":v.ROOT_ID,"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,
 "subject":{"path":v.SUBJECT_PATH,"git_blob_sha":v.SUBJECT_BLOB},
 "bridge_evidence":{k:{"path":p,"git_blob_sha":s} for k,(p,s) in v.REFS.items()},
 "binding_scope":{"limitations":["NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_POLICY_GENERATION_COMPLETENESS","NO_POLICY_ADEQUACY_FROM_GENERATION","NO_GLOBAL_R2_ROOT_CLOSURE","NO_R3_THROUGH_R12_ROOT_SUBJECT_BINDING","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION"]},
 "root_subject_binding_authority":False,"global_subject_identity_authority":False,"semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False}

def docs():
 return {
 v.BINDING_PATH:binding(),
 v.SUBJECT_PATH:{"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,"system_material":{"components":[{"path":v.PROFILE_PATH,"git_blob_sha":v.PROFILE_BLOB}]}},
 v.REFS["subject_verification"][0]:{"real_subject_replay":{"pass":True,"component_count":22,"component_currentness_verified":True,"subject_identity_verified":True}},
 v.REFS["candidate_generator_verification"][0]:{"exact_candidate":{"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,"execution_profile_path":v.PROFILE_PATH,"execution_profile_git_blob_sha":v.PROFILE_BLOB},"independent_replay":{"tests_passed":7,"tests_failed":0,"real_profile_candidate_count":22},"proves":["FINITE_PROFILE_DERIVED_CANDIDATE_BASIS_IS_DETERMINISTIC_ON_V7_SUBJECT_IDENTITY","GENERATOR_OUTPUT_DOES_NOT_SELF_AUTHORIZE_THE_V7_PROFESSIONAL_STEP"],"hard_nonclaims":["NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS"]},
 v.REFS["r2_search_semantics"][0]:{"replay":{"tests_passed":8},"claim_scope":{"kind":"FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS","limitations":["NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_GLOBAL_R2_ROOT_CLOSURE","NO_POLICY_GENERATION_COMPLETENESS"]}},
 v.REFS["r2_scope_complete_execution"][0]:{"replay":{"tests_passed":9},"proved":["INDEPENDENT_POLICY_ADEQUACY_IS_REQUIRED"]}}

def reader(table):
 def f(root,path,sha):return (deepcopy(table[path]),None)
 return f

class Tests(unittest.TestCase):
 def runv(self,table):
  with patch.object(v,"_read",side_effect=reader(table)):return v.verify()
 def test_pass_only_root_binding_authority(self):
  o=self.runv(docs());self.assertTrue(o["pass"],o);self.assertTrue(o["root_subject_binding_authority"]);self.assertFalse(o["quality_authority"]);self.assertFalse(o["terminal_authority"])
 def test_subject_drift_fails(self):
  d=docs();d[v.REFS["candidate_generator_verification"][0]]["exact_candidate"]["subject_sha256"]="0"*64;self.assertEqual(self.runv(d)["reason"],"GENERATOR_SUBJECT_TUPLE_MISMATCH")
 def test_global_completeness_boundary_required(self):
  d=docs();d[v.REFS["r2_search_semantics"][0]]["claim_scope"]["limitations"]=[];self.assertEqual(self.runv(d)["reason"],"R2_SEMANTIC_SCOPE_TOO_BROAD")
 def test_policy_adequacy_independence_required(self):
  d=docs();d[v.REFS["r2_scope_complete_execution"][0]]["proved"]=[];self.assertEqual(self.runv(d)["reason"],"POLICY_ADEQUACY_INDEPENDENCE_UNPROVED")
 def test_self_authority_fails(self):
  d=docs();d[v.BINDING_PATH]["quality_authority"]=True;self.assertEqual(self.runv(d)["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN:quality_authority")

if __name__=="__main__":unittest.main()
