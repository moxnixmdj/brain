from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import regcap_property_candidate_discovery_v1 as discover


def request(prop):
    return {
        "schema": discover.REQUEST_SCHEMA,
        "scope_id": regcap.SCOPE_ID,
        "property_id": prop,
    }


def property_result(concept, prop, *, passed):
    if passed:
        return {
            "pass": True,
            "status": "PASS__REGCAP_NECESSARY_PROPERTY_AUTHENTICATED",
            "edge_receipt": {
                "pass": True,
                "source_id": concept,
                "target_id": prop,
                "relation": "ENTAILS",
                "receipt_sha256": (concept + prop).encode().hex()[:64].ljust(64, "0"),
            },
        }
    return {
        "pass": False,
        "status": "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        "reason": None,
    }


class Tests(unittest.TestCase):
    def test_shared_loss_absorption_property_returns_three_nonunique_candidates(self):
        prop = "DISPOSITION::LOSS_ABSORPTION"

        def verify(req, repo_root=None):
            del repo_root
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=True,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(request(prop))

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
        )
        self.assertEqual(
            out["candidate_concept_ids"],
            sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC]),
        )
        self.assertTrue(out["non_unique_property_witness"])
        self.assertFalse(out["unique_identity_authorized"])
        self.assertFalse(out["necessary_property_is_sufficient_for_identity"])

    def test_single_property_candidate_still_does_not_authorize_identity(self):
        prop = "REGIME::RESOLUTION"

        def verify(req, repo_root=None):
            del repo_root
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=req["concept_id"] == regcap.TLAC,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(request(prop))

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__SINGLE_PROPERTY_CANDIDATE_NOT_IDENTITY",
        )
        self.assertEqual(out["candidate_concept_ids"], [regcap.TLAC])
        self.assertFalse(out["unique_identity_authorized"])

    def test_no_candidate_is_not_nonexistence(self):
        def verify(req, repo_root=None):
            del repo_root
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=False,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(request("PROPERTY::UNKNOWN"))

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_VERIFIED_PROPERTY_CANDIDATES_IN_BOUND_RIVAL_SET",
        )
        self.assertFalse(out["no_candidate_means_nonexistence"])
        self.assertFalse(out["open_world_candidate_set_complete"])

    def test_authority_failure_fails_closed(self):
        def verify(req, repo_root=None):
            del repo_root
            if req["concept_id"] == regcap.CCOB:
                return {
                    "pass": False,
                    "status": "FAIL_CLOSED",
                    "reason": "SOURCE_DRIFT",
                }
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=True,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(
                request("DISPOSITION::LOSS_ABSORPTION")
            )

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PROPERTY_AUTHORITY_FAILURE")

    def test_positive_targets_are_search_targets_not_decisive_discriminators(self):
        prop = "DISPOSITION::LOSS_ABSORPTION"

        def verify(req, repo_root=None):
            del repo_root
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=True,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(request(prop))

        self.assertFalse(
            out["positive_evidence_targets_are_decisive_discriminators"]
        )
        by_id = {row["concept_id"]: row for row in out["candidates"]}
        self.assertIn(
            "REGIME::RESOLUTION",
            by_id[regcap.TLAC]["positive_evidence_targets"],
        )
        self.assertIn(
            "TRIGGER::EXCESS_CREDIT_GROWTH_SYSTEM_WIDE_RISK",
            by_id[regcap.CCYB]["positive_evidence_targets"],
        )
        self.assertIn(
            "POSITION::ABOVE_REGULATORY_MINIMUM",
            by_id[regcap.CCOB]["positive_evidence_targets"],
        )

    def test_no_semantic_or_terminal_authority(self):
        prop = "DISPOSITION::LOSS_ABSORPTION"

        def verify(req, repo_root=None):
            del repo_root
            return property_result(
                req["concept_id"],
                req["property_id"],
                passed=True,
            )

        with patch.object(
            discover.regcap,
            "verify_property_request",
            side_effect=verify,
        ):
            out = discover.discover(request(prop))

        self.assertTrue(out["candidate_generation_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
