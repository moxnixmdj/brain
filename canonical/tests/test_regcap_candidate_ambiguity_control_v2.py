from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import minimum_information_origin_policy_v1 as origin
from canonical.runtime import regcap_candidate_ambiguity_control_v1 as v1
from canonical.runtime import regcap_candidate_ambiguity_control_v2 as v2
from canonical.runtime import regcap_property_candidate_discovery_v1 as discovery


IDS = ["REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC"]


def candidates():
    return {
        "schema": discovery.SCHEMA,
        "pass": True,
        "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
        "candidate_generation_authority": True,
        "candidate_set_complete_relative_to_bound_rivals": True,
        "open_world_candidate_set_complete": False,
        "candidate_concept_ids": list(IDS),
        "candidates": [
            {"concept_id": "REGCAP::CCOB", "positive_evidence_targets": []},
            {"concept_id": "REGCAP::CCYB", "positive_evidence_targets": []},
            {"concept_id": "REGCAP::TLAC", "positive_evidence_targets": []},
        ],
    }


def scope():
    return {
        "kind": v1.BOUND_SCOPE,
        "scope_complete": True,
        "candidate_ids": list(IDS),
    }


def matrix():
    return {
        "pass": True,
        "source_authority": True,
        "semantic_truth_authority": True,
        "candidate_domain": list(IDS),
        "matrix_sha256": "m" * 64,
        "observations": [
            {
                "observation_id": "FRAMEWORK_CLASS",
                "outcomes": {
                    "REGCAP::CCOB": "BASEL",
                    "REGCAP::CCYB": "BASEL",
                    "REGCAP::TLAC": "TLAC",
                },
            },
            {
                "observation_id": "RELEASABILITY_CLASS",
                "outcomes": {
                    "REGCAP::CCOB": "NOT_RELEASABLE",
                    "REGCAP::CCYB": "RELEASABLE",
                    "REGCAP::TLAC": "OUTSIDE",
                },
            },
        ],
    }


class Tests(unittest.TestCase):
    def test_open_world_behavior_is_preserved_without_matrix_upgrade(self):
        with patch.object(v2.matrix, "verify_matrix") as verify:
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope={"kind": "OPEN_WORLD", "scope_complete": False},
                observation_cost_units=None,
                information_owner=origin.USER_SPECIFICATION,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__OPEN_WORLD_MAPPING_REQUIRES_MINIMUM_ADDITIONAL_INFORMATION",
        )
        self.assertFalse(out["authenticated_matrix_reused"])
        verify.assert_not_called()
        self.assertFalse(out["semantic_identity_authority"])

    def test_authenticated_outcomes_do_not_invent_acquisition_costs(self):
        with patch.object(v2.matrix, "verify_matrix", return_value=matrix()):
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope=scope(),
                observation_cost_units=None,
                information_owner="SYSTEM_MODEL",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_MATRIX_COST_BINDING_REQUIRED",
        )
        self.assertEqual(
            out["required_observation_cost_ids"],
            ["FRAMEWORK_CLASS", "RELEASABILITY_CLASS"],
        )
        self.assertTrue(out["authenticated_matrix_reused"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_exact_cost_binding_reuses_matrix_and_selects_minimax_separator(self):
        with patch.object(v2.matrix, "verify_matrix", return_value=matrix()):
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope=scope(),
                observation_cost_units={
                    "FRAMEWORK_CLASS": 1,
                    "RELEASABILITY_CLASS": 2,
                },
                information_owner="SYSTEM_MODEL",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__MINIMUM_POLICY_CHANGING_DISCRIMINATOR_READY",
        )
        self.assertEqual(out["next_observation_id"], "RELEASABILITY_CLASS")
        self.assertEqual(out["minimum_worst_case_cost_units"], 2.0)
        self.assertTrue(out["authenticated_matrix_reused"])
        self.assertTrue(out["matrix_source_authority"])
        self.assertTrue(out["matrix_semantic_truth_authority"])
        self.assertEqual(
            out["observation_cost_authority"],
            "CALLER_BOUND_TASK_LOCAL_ONLY",
        )
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_one_cost_stays_open_instead_of_partial_minimax(self):
        with patch.object(v2.matrix, "verify_matrix", return_value=matrix()):
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope=scope(),
                observation_cost_units={"FRAMEWORK_CLASS": 1},
                information_owner="SYSTEM_MODEL",
            )
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_MATRIX_COST_BINDING_REQUIRED",
        )
        self.assertEqual(out["invalid_or_missing_cost_ids"], ["RELEASABILITY_CLASS"])

    def test_matrix_domain_mismatch_fails_closed(self):
        bad = matrix()
        bad["candidate_domain"] = IDS[:-1]
        with patch.object(v2.matrix, "verify_matrix", return_value=bad):
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope=scope(),
                observation_cost_units={},
                information_owner="SYSTEM_MODEL",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "AUTHENTICATED_MATRIX_DOMAIN_MISMATCH")

    def test_matrix_authentication_failure_fails_closed(self):
        with patch.object(
            v2.matrix,
            "verify_matrix",
            return_value={"pass": False, "status": "FAIL_CLOSED"},
        ):
            out = v2.plan_with_authenticated_matrix(
                candidates(),
                mapping_scope=scope(),
                observation_cost_units={},
                information_owner="SYSTEM_MODEL",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHENTICATED_DISCRIMINATOR_MATRIX_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
