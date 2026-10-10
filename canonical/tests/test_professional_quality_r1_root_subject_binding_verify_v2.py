from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_r1_root_subject_binding_verify_v2 as v


def binding():
    return {
        "schema": v.BINDING_SCHEMA,
        "root_id": v.ROOT_ID,
        "subject_kind": "DECLARED_SYSTEM",
        "subject_id": v.SUBJECT_ID,
        "subject_sha256": v.SUBJECT_SHA256,
        "subject": {"path": v.SUBJECT_PATH, "git_blob_sha": v.SUBJECT_BLOB},
        "bridge_evidence": {
            key: {"path": path, "git_blob_sha": sha}
            for key, (path, sha) in v.EXPECTED_REFS.items()
        },
        "binding_scope": {
            "behavior_id": "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
            "limitations": [
                "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
                "NO_GLOBAL_R1_ROOT_CLOSURE",
                "NO_LIVE_DEFAULT_PROMOTION",
            ],
        },
        "root_subject_binding_authority": False,
        "global_subject_identity_authority": False,
        "terminal_authority": False,
    }


def subject():
    return {
        "subject_id": v.SUBJECT_ID,
        "subject_sha256": v.SUBJECT_SHA256,
        "dependency_closed_generation": True,
        "system_material": {
            "components": [
                {"path": p, "git_blob_sha": s}
                for p, s in [
                    ("canonical/runtime/professional_quality_p1_router_v4.py","8e5d473b5606251752c4968dfd35290e9b991f16"),
                    ("canonical/runtime/professional_quality_p1_router_v3.py","cdb6716ac6d562d1ab222242d07aeecc5cdfac78"),
                    ("canonical/runtime/professional_target_semantic_certificate_v1.py","583612b0e2226053ac758683087b5c5d0f510996"),
                    ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
                    ("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
                ]
            ] + [
                {"path": f"canonical/runtime/extra_{i}.py", "git_blob_sha": f"{i:040x}"[-40:]}
                for i in range(31)
            ]
        },
    }


def docs():
    return {
        v.BINDING_PATH: binding(),
        v.SUBJECT_PATH: subject(),
        v.EXPECTED_REFS["subject_verification"][0]: {
            "pass": True,
            "component_count": 36,
            "component_currentness_verified": True,
            "root_subject_binding_authority": False,
        },
        v.EXPECTED_REFS["target_bound_router_regression"][0]: {
            "replay": {"tests_passed": 21, "tests_failed": 0},
            "live_default": False,
            "quality_authority": False,
        },
        v.EXPECTED_REFS["r1_target_semantics"][0]: {
            "replay": {"tests_passed": 5},
            "claim_scope": {
                "kind": "EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS",
                "limitations": ["NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS"],
            },
        },
        v.EXPECTED_REFS["r1_structural_target"][0]: {
            "replay": {"tests_passed": 21},
            "current_truth": {"semantic_truth_closed": False},
        },
    }


def reader(table):
    def _read(root, path, sha):
        if path not in table:
            return None, "MISSING"
        return deepcopy(table[path]), None
    return _read


class R1RootSubjectBindingVerifyV2Tests(unittest.TestCase):
    def test_valid_dependency_closed_binding_grants_only_root_binding_authority(self):
        table=docs()
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_dependency_closed_generation_required(self):
        table=docs()
        table[v.SUBJECT_PATH]["dependency_closed_generation"]=False
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"], "SUBJECT_DEPENDENCY_CLOSURE_REQUIRED")

    def test_subject_verification_requires_36_current_components(self):
        table=docs()
        table[v.EXPECTED_REFS["subject_verification"][0]]["component_count"]=35
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"], "SUBJECT_VERIFICATION_INSUFFICIENT")

    def test_binding_cannot_self_authorize(self):
        table=docs()
        table[v.BINDING_PATH]["root_subject_binding_authority"]=True
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"], "BINDING_SELF_AUTHORITY_FORBIDDEN")

    def test_missing_r1_material_fails_closed(self):
        table=docs()
        table[v.SUBJECT_PATH]["system_material"]["components"]=table[v.SUBJECT_PATH]["system_material"]["components"][1:]
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"], "R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    def test_arbitrary_prompt_semantic_overclaim_fails_closed(self):
        table=docs()
        table[v.EXPECTED_REFS["r1_target_semantics"][0]]["claim_scope"]["limitations"]=[]
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"], "R1_SEMANTIC_SCOPE_TOO_BROAD")


if __name__=="__main__":
    unittest.main()
