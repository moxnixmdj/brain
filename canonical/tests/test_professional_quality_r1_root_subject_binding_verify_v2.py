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
    required = [
        {"path": path, "git_blob_sha": sha}
        for path, sha in sorted(v.REQUIRED_MATERIAL)
    ]
    extras = [
        {
            "path": f"canonical/governance/TEST_COMPONENT_{i}.json",
            "git_blob_sha": f"{i:040x}",
        }
        for i in range(1, 21 - len(required))
    ]
    rows = required + extras
    assert len(rows) == 20
    return {
        "subject_id": v.SUBJECT_ID,
        "subject_sha256": v.SUBJECT_SHA256,
        "system_material": {"components": rows},
    }


def docs():
    return {
        v.BINDING_PATH: binding(),
        v.SUBJECT_PATH: subject(),
        v.EXPECTED_REFS["subject_verification"][0]: {
            "real_subject_replay": {
                "pass": True,
                "component_count": 20,
                "component_currentness_verified": True,
                "subject_identity_verified": True,
            },
            "authority": {"root_subject_binding_authority": False},
        },
        v.EXPECTED_REFS["dependency_closure"][0]: {
            "replay": {
                "pass": True,
                "roots_dependency_classified": 12,
                "missing_subject_component_count": 0,
                "subject_component_count": 20,
            },
            "authority": {"root_subject_binding_authority": False},
        },
        v.EXPECTED_REFS["authenticated_target_handoff"][0]: {
            "replay": {
                "kernel_equivalence": {
                    "tests_passed": 7,
                    "tests_failed": 0,
                },
                "router_v6": {
                    "tests_passed": 10,
                    "tests_failed": 0,
                    "general_controller_import_absent": True,
                },
                "real_integration": {
                    "cases_passed": 2,
                },
            },
            "proved": [
                "MINIMAL_KERNEL_MATCHES_LEGACY_GOAL_BINDING_AUTHORITY_OUTPUTS_ON_VALID_OPEN_AND_FAIL_CLOSED_CASES",
                "V6_REMOVES_GENERAL_ADEQUATE_DECISION_CONTROLLER_FROM_ITS_DIRECT_IMPORT_GRAPH",
                "AUTHENTICATED_RAW_GOAL_TO_TARGET_HANDOFF_BEHAVIOR_IS_PRESERVED",
                "REAL_CLEAN_AND_BLANK_DOCX_V4_V3_BEHAVIOR_IS_PRESERVED",
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
    def test_final_v6_binding_grants_only_root_binding_authority(self):
        table = docs()
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__R1_ROOT_BOUND_TO_FINAL_DEPENDENCY_CLOSED_V6_SUBJECT",
        )
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["global_subject_identity_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_binding_cannot_self_authorize(self):
        table = docs()
        table[v.BINDING_PATH]["root_subject_binding_authority"] = True
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(
            out["reason"],
            "BINDING_SELF_AUTHORITY_FORBIDDEN:root_subject_binding_authority",
        )

    def test_missing_v6_kernel_material_fails_closed(self):
        table = docs()
        table[v.SUBJECT_PATH]["system_material"]["components"] = [
            row
            for row in table[v.SUBJECT_PATH]["system_material"]["components"]
            if row["path"]
            != "canonical/runtime/goal_to_decision_binding_authority_v1.py"
        ]
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(
            out["reason"],
            "R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT",
        )

    def test_incomplete_dependency_closure_fails_closed(self):
        table = docs()
        table[v.EXPECTED_REFS["dependency_closure"][0]][
            "replay"
        ]["missing_subject_component_count"] = 1
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(out["reason"], "DEPENDENCY_CLOSURE_INSUFFICIENT")

    def test_weak_v6_replay_fails_closed(self):
        table = docs()
        table[v.EXPECTED_REFS["authenticated_target_handoff"][0]][
            "replay"
        ]["router_v6"]["tests_passed"] = 9
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(out["reason"], "V6_HANDOFF_REPLAY_INSUFFICIENT")

    def test_missing_v6_proof_fails_closed(self):
        table = docs()
        table[v.EXPECTED_REFS["authenticated_target_handoff"][0]][
            "proved"
        ].remove(
            "AUTHENTICATED_RAW_GOAL_TO_TARGET_HANDOFF_BEHAVIOR_IS_PRESERVED"
        )
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(out["reason"], "V6_HANDOFF_PROOF_SET_INSUFFICIENT")

    def test_missing_anti_substitution_guarantee_fails_closed(self):
        table = docs()
        table[v.BINDING_PATH]["binding_scope"]["guarantees"].remove(
            "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_SUBSTITUTION_FAILS_CLOSED"
        )
        with patch.object(v, "_read", side_effect=reader(table)):
            out = v.verify()
        self.assertEqual(out["reason"], "BINDING_GUARANTEES_INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
