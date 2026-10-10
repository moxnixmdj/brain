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
            "guarantees": sorted(v.REQUIRED_GUARANTEES),
            "limitations": sorted(v.REQUIRED_LIMITS),
        },
        "root_subject_binding_authority": False,
        "global_subject_identity_authority": False,
        "terminal_authority": False,
    }


def subject():
    return {
        "subject_id": v.SUBJECT_ID,
        "subject_sha256": v.SUBJECT_SHA256,
        "system_material": {
            "components": [
                {"path": path, "git_blob_sha": sha}
                for path, sha in sorted(v.REQUIRED_MATERIAL)
            ]
        },
    }


def docs():
    return {
        v.BINDING_PATH: binding(),
        v.SUBJECT_PATH: subject(),
        v.EXPECTED_REFS["subject_verification"][0]: {
            "real_subject_replay": {
                "pass": True,
                "component_count": 16,
                "component_currentness_verified": True,
                "subject_identity_verified": True,
            },
            "root_subject_binding_authority": False,
        },
        v.EXPECTED_REFS["authenticated_target_handoff"][0]: {
            "subject": {
                "git_blob_sha": "8583b63571b5bfe86a473dcba1a716b98821cd5c"
            },
            "producer_id": "producer-a",
            "independent_verifier": {
                "independent_verifier_id": "verifier-b"
            },
            "replay": {
                "total_tests_passed": 31,
                "total_tests_failed": 0,
            },
            "proves": [
                "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_CANNOT_ENTER_V5",
                "CALLER_CANNOT_SELF_ATTEST_COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS",
                "TARGET_INSTANCE_IS_EXTRACTED_ONLY_FROM_EXACT_DECISION_PAYLOAD_BOUND_TO_EXACT_RAW_GOAL",
                "GOAL_OR_DECISION_PAYLOAD_TAMPER_BREAKS_CONTENT_BINDING_BEFORE_V4",
                "PRODUCER_AND_VERIFIER_IDENTITIES_MUST_BE_DISTINCT",
            ],
            "quality_authority": False,
            "terminal_authority": False,
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
            return None, "MISSING:" + path
        return deepcopy(table[path]), None
    return _read


class R1RootSubjectBindingVerifyV2Tests(unittest.TestCase):
    def test_valid_stronger_binding_grants_only_root_binding_authority(self):
        table=docs()
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["global_subject_identity_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_binding_cannot_self_authorize(self):
        table=docs()
        table[v.BINDING_PATH]["root_subject_binding_authority"]=True
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN:root_subject_binding_authority")

    def test_missing_v5_material_fails_closed(self):
        table=docs()
        table[v.SUBJECT_PATH]["system_material"]["components"]=[
            row for row in table[v.SUBJECT_PATH]["system_material"]["components"]
            if row["path"]!="canonical/runtime/professional_quality_p1_router_v5.py"
        ]
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    def test_weak_v5_replay_fails_closed(self):
        table=docs()
        table[v.EXPECTED_REFS["authenticated_target_handoff"][0]]["replay"]["total_tests_passed"]=30
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"V5_HANDOFF_REPLAY_INSUFFICIENT")

    def test_same_handoff_producer_and_verifier_fails_closed(self):
        table=docs()
        handoff=table[v.EXPECTED_REFS["authenticated_target_handoff"][0]]
        handoff["producer_id"]="same"
        handoff["independent_verifier"]["independent_verifier_id"]="same"
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"V5_HANDOFF_INDEPENDENCE_INVALID")

    def test_missing_anti_substitution_guarantee_fails_closed(self):
        table=docs()
        table[v.BINDING_PATH]["binding_scope"]["guarantees"].remove(
            "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_SUBSTITUTION_FAILS_CLOSED"
        )
        with patch.object(v, "_read", side_effect=reader(table)):
            out=v.verify()
        self.assertEqual(out["reason"],"BINDING_GUARANTEES_INSUFFICIENT")


if __name__=="__main__":
    unittest.main()
