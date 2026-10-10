from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import minimum_information_origin_policy_v1 as origin
from canonical.runtime import regcap_candidate_ambiguity_control_v1 as control
from canonical.runtime import regcap_mrel_property_candidate_discovery_v1 as discover4
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel


IDS = sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL])
PROP = "DISPOSITION::LOSS_ABSORPTION"


def request(prop=PROP):
    return {
        "schema": discover4.REQUEST_SCHEMA,
        "scope_id": discover4.SCOPE_ID,
        "property_id": prop,
    }


def edge(concept, prop, passed=True):
    if not passed:
        return {
            "pass": False,
            "status": "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
            "reason": None,
        }
    return {
        "pass": True,
        "status": "PASS__AUTHENTICATED",
        "schema": "TEST_AUTHORITY",
        "edge_receipt": {
            "pass": True,
            "source_id": concept,
            "target_id": prop,
            "relation": "ENTAILS",
            "receipt_sha256": (concept + prop).encode().hex()[:64].ljust(64, "0"),
        },
    }


class Tests(unittest.TestCase):
    def test_shared_loss_absorption_discovers_all_four_bound_candidates(self):
        with patch.object(discover4, "_verify", side_effect=lambda c, p, repo_root=None: edge(c, p)):
            out = discover4.discover(request())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES")
        self.assertEqual(out["candidate_concept_ids"], IDS)
        self.assertTrue(out["candidate_set_complete_relative_to_bound_rivals"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertFalse(out["unique_identity_authorized"])
        self.assertFalse(out["necessary_property_is_sufficient_for_identity"])

    def test_four_way_discovery_unknown_is_not_refutation(self):
        def verify(concept, prop, repo_root=None):
            del repo_root
            return edge(concept, prop, passed=(concept == mrel.MREL))
        with patch.object(discover4, "_verify", side_effect=verify):
            out = discover4.discover(request("REGIME::RESOLUTION"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_concept_ids"], [mrel.MREL])
        self.assertFalse(out["unique_identity_authorized"])
        self.assertFalse(out["absence_means_refuted"])

    def test_four_way_authority_failure_fails_closed(self):
        def verify(concept, prop, repo_root=None):
            del repo_root
            if concept == regcap.CCOB:
                return {"pass": False, "status": "FAIL_CLOSED", "schema": "X", "reason": "SOURCE_DRIFT"}
            return edge(concept, prop)
        with patch.object(discover4, "_verify", side_effect=verify):
            out = discover4.discover(request())
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PROPERTY_AUTHORITY_FAILURE")

    def test_existing_ambiguity_controller_accepts_four_way_authenticated_schema(self):
        candidate = {
            "schema": discover4.SCHEMA,
            "pass": True,
            "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
            "candidate_generation_authority": True,
            "candidate_set_complete_relative_to_bound_rivals": True,
            "open_world_candidate_set_complete": False,
            "candidate_concept_ids": IDS,
            "candidates": [
                {"concept_id": cid, "positive_evidence_targets": ["AUTHENTICATED_CONTEXT::" + cid]}
                for cid in IDS
            ],
        }
        out = control.plan(
            candidate,
            mapping_scope={
                "kind": control.BOUND_SCOPE,
                "scope_complete": True,
                "candidate_ids": IDS,
            },
            observations=[],
            observation_set_complete=False,
            information_owner=origin.EXTERNAL_WORLD,
            discovery_delegated=True,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__OBSERVATION_MODEL_COMPLETENESS_REQUIRED")
        self.assertEqual(out["action"], "RESEARCH_MINIMUM_AUTHENTICATED_FACT")
        self.assertTrue(out["minimum_information_route"]["external_research_authorized"])
        self.assertEqual(out["candidate_concept_ids"], IDS)
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_user_owned_missing_four_way_discriminator_routes_to_minimum_clarification(self):
        candidate = {
            "schema": discover4.SCHEMA,
            "pass": True,
            "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
            "candidate_generation_authority": True,
            "candidate_set_complete_relative_to_bound_rivals": True,
            "candidate_concept_ids": IDS,
            "candidates": [{"concept_id": cid, "positive_evidence_targets": []} for cid in IDS],
        }
        out = control.plan(
            candidate,
            mapping_scope={
                "kind": control.BOUND_SCOPE,
                "scope_complete": True,
                "candidate_ids": IDS,
            },
            observations=[],
            observation_set_complete=False,
            information_owner=origin.USER_SPECIFICATION,
        )
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertTrue(out["minimum_information_route"]["ask_user_required"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
