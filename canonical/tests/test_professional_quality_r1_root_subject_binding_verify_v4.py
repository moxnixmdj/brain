from __future__ import annotations
from copy import deepcopy
from unittest.mock import patch
import unittest
from canonical.runtime import professional_quality_r1_root_subject_binding_verify_v4 as v

def binding():
    return {
      "schema":v.BINDING_SCHEMA,"root_id":v.ROOT_ID,
      "subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,
      "subject":{"path":v.SUBJECT_PATH,"git_blob_sha":v.SUBJECT_BLOB},
      "bridge_evidence":{k:{"path":p,"git_blob_sha":s} for k,(p,s) in v.REFS.items()},
      "binding_scope":{"limitations":["NO_GLOBAL_R1_ROOT_CLOSURE","NO_R2_THROUGH_R12_ROOT_SUBJECT_BINDING","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION"]},
      "root_subject_binding_authority":False,"global_subject_identity_authority":False,
      "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
      "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
    }
def docs():
    return {
      v.BINDING_PATH:binding(),
      v.SUBJECT_PATH:{"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA256,
        "system_material":{"components":[{"path":p,"git_blob_sha":s} for p,s in sorted(v.REQUIRED_MATERIAL)]}},
      v.REFS["subject_verification"][0]:{"real_subject_replay":{"pass":True,"component_count":22,"component_currentness_verified":True,"subject_identity_verified":True}},
      v.REFS["authenticated_target_handoff"][0]:{"replay":{"kernel_equivalence":{"tests_passed":7},"router_v6":{"tests_passed":10},"real_integration":{"cases_passed":2}}},
      v.REFS["proof_bound_profile_execution"][0]:{"replay":{"tests_passed":15},"proves":["CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY"],"quality_authority":False,"terminal_authority":False},
      v.REFS["r1_target_semantics"][0]:{"replay":{"tests_passed":5},"claim_scope":{"kind":"EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS","limitations":["NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS"]}},
      v.REFS["r1_structural_target"][0]:{"replay":{"tests_passed":21},"current_truth":{"semantic_truth_closed":False}},
    }
def reader(table):
    def _read(root,path,sha):
        return (deepcopy(table[path]),None) if path in table else (None,"MISSING:"+path)
    return _read

class R1V7BindingTests(unittest.TestCase):
    def test_valid_v7_binding_grants_only_root_binding_authority(self):
        table=docs()
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertTrue(out["pass"],out); self.assertTrue(out["root_subject_binding_authority"])
        for f in ("semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"): self.assertFalse(out[f])

    def test_self_authority_fails_closed(self):
        table=docs(); table[v.BINDING_PATH]["quality_authority"]=True
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertIn("BINDING_SELF_AUTHORITY_FORBIDDEN:quality_authority",out["reason"])

    def test_missing_v7_router_fails_closed(self):
        table=docs()
        table[v.SUBJECT_PATH]["system_material"]["components"]=[x for x in table[v.SUBJECT_PATH]["system_material"]["components"] if x["path"]!="canonical/runtime/professional_quality_p1_router_v7.py"]
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertEqual(out["reason"],"R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    def test_weak_step_provenance_fails_closed(self):
        table=docs(); table[v.REFS["proof_bound_profile_execution"][0]]["replay"]["tests_passed"]=14
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertEqual(out["reason"],"V7_STEP_PROVENANCE_REPLAY_INSUFFICIENT")

    def test_step_provenance_quality_overclaim_fails_closed(self):
        table=docs(); table[v.REFS["proof_bound_profile_execution"][0]]["quality_authority"]=True
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertEqual(out["reason"],"V7_PROVENANCE_AUTHORITY_OVERCLAIM")

    def test_subject_component_count_drift_fails_closed(self):
        table=docs(); table[v.REFS["subject_verification"][0]]["real_subject_replay"]["component_count"]=21
        with patch.object(v,"_read",side_effect=reader(table)): out=v.verify()
        self.assertEqual(out["reason"],"SUBJECT_VERIFICATION_INSUFFICIENT")

if __name__=="__main__": unittest.main()
