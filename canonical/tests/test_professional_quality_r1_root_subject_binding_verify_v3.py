from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_r1_root_subject_binding_verify_v3 as v


def binding():
    return {
        "schema":v.BINDING_SCHEMA,
        "root_id":v.ROOT_ID,
        "subject_kind":"DECLARED_SYSTEM",
        "subject_id":v.SUBJECT_ID,
        "subject_sha256":v.SUBJECT_SHA256,
        "subject":{"path":v.SUBJECT_PATH,"git_blob_sha":v.SUBJECT_BLOB},
        "bridge_evidence":{
            key:{"path":path,"git_blob_sha":sha}
            for key,(path,sha) in v.EXPECTED_REFS.items()
        },
        "binding_scope":{
            "behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
            "limitations":[
                "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
                "NO_GLOBAL_R1_ROOT_CLOSURE",
                "NO_SAME_SUBJECT_COMPOSITION_PASS",
                "NO_LIVE_DEFAULT_PROMOTION",
            ],
        },
        "root_subject_binding_authority":False,
        "global_subject_identity_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
    }


def subject():
    return {
        "subject_id":v.SUBJECT_ID,
        "subject_sha256":v.SUBJECT_SHA256,
        "dependency_closure":{
            "v6_minimal_binding_kernel":{"broad_general_controller_in_subject":False}
        },
        "system_material":{
            "components":[{"path":p,"git_blob_sha":s} for p,s in sorted(v.REQUIRED_MATERIAL)]
        },
    }


def docs():
    return {
        v.BINDING_PATH:binding(),
        v.SUBJECT_PATH:subject(),
        v.EXPECTED_REFS["subject_verification"][0]:{
            "real_subject_replay":{
                "pass":True,"component_count":20,
                "component_currentness_verified":True,
                "subject_identity_verified":True,
            },
            "authority":{"root_subject_binding_authority":False},
        },
        v.EXPECTED_REFS["authenticated_target_handoff"][0]:{
            "replay":{
                "kernel_equivalence":{"tests_passed":7},
                "router_v6":{"tests_passed":10},
                "real_integration":{"cases_passed":2},
            },
            "quality_authority":False,
            "terminal_authority":False,
        },
        v.EXPECTED_REFS["r1_target_semantics"][0]:{
            "replay":{"tests_passed":5},
            "claim_scope":{
                "kind":"EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS",
                "limitations":["NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS"],
            },
        },
        v.EXPECTED_REFS["r1_structural_target"][0]:{
            "replay":{"tests_passed":21},
            "current_truth":{"semantic_truth_closed":False},
        },
    }


def reader(table):
    def _read(root,path,sha):
        if path not in table:
            return None,"MISSING:"+path
        return deepcopy(table[path]),None
    return _read


class R1RootSubjectBindingVerifyV3Tests(unittest.TestCase):
    def test_valid_v6_binding_grants_only_root_binding_authority(self):
        table=docs()
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["root_subject_binding_authority"])
        for field in ("global_subject_identity_authority","semantic_truth_authority",
                      "execution_authority","quality_authority","acceptance_authority",
                      "promotion_authority","terminal_authority"):
            self.assertFalse(out[field])

    def test_binding_cannot_self_authorize(self):
        table=docs(); table[v.BINDING_PATH]["root_subject_binding_authority"]=True
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN:root_subject_binding_authority")

    def test_subject_identity_mismatch_fails_closed(self):
        table=docs(); table[v.SUBJECT_PATH]["subject_sha256"]="0"*64
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"SUBJECT_DOCUMENT_IDENTITY_MISMATCH")

    def test_missing_v6_router_material_fails_closed(self):
        table=docs()
        table[v.SUBJECT_PATH]["system_material"]["components"]=[
            row for row in table[v.SUBJECT_PATH]["system_material"]["components"]
            if row["path"]!="canonical/runtime/professional_quality_p1_router_v6.py"
        ]
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    def test_weak_v6_router_replay_fails_closed(self):
        table=docs()
        table[v.EXPECTED_REFS["authenticated_target_handoff"][0]]["replay"]["router_v6"]["tests_passed"]=9
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"V6_ROUTER_REGRESSION_INSUFFICIENT")

    def test_arbitrary_prompt_semantic_overclaim_fails_closed(self):
        table=docs()
        table[v.EXPECTED_REFS["r1_target_semantics"][0]]["claim_scope"]["limitations"]=[]
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"R1_SEMANTIC_SCOPE_TOO_BROAD")

    def test_same_subject_composition_limitation_is_required(self):
        table=docs()
        table[v.BINDING_PATH]["binding_scope"]["limitations"].remove("NO_SAME_SUBJECT_COMPOSITION_PASS")
        with patch.object(v,"_read",side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"BINDING_LIMITATIONS_INSUFFICIENT")


if __name__=="__main__":
    unittest.main()
