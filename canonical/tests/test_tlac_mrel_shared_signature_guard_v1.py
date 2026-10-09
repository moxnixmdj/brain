from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import tlac_mrel_shared_signature_guard_v1 as guard


def ok_result(concept, prop):
    return {
        "pass": True,
        "semantic_truth_authority": True,
        "concept_id": concept,
        "property_id": prop,
        "relation": "ENTAILS",
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_shared_bundle_is_authenticated_but_nonseparating(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok_result(
                guard.regcap.TLAC,
                req["property_id"],
            ),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            side_effect=lambda req, **_: ok_result(
                guard.mrel.MREL,
                req["property_id"],
            ),
        ):
            out = guard.verify_shared_signature()

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["shared_properties"]),
            set(guard.SHARED_PROPERTIES),
        )
        self.assertFalse(out["property_bundle_separates_pair"])
        self.assertFalse(out["reverse_classification_from_shared_bundle_authorized"])
        self.assertTrue(out["identity_discriminator_required"])

    def test_tlac_failure_fails_closed(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            return_value={"pass": False, "reason": "forced"},
        ):
            out = guard.verify_shared_signature()
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TLAC_PROPERTY_AUTHORITY_FAILED", out["reason"])

    def test_mrel_failure_fails_closed(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok_result(
                guard.regcap.TLAC,
                req["property_id"],
            ),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            return_value={"pass": False, "reason": "forced"},
        ):
            out = guard.verify_shared_signature()
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("MREL_PROPERTY_AUTHORITY_FAILED", out["reason"])

    def test_no_equivalence_disjointness_or_completeness_authority(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok_result(
                guard.regcap.TLAC,
                req["property_id"],
            ),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            side_effect=lambda req, **_: ok_result(
                guard.mrel.MREL,
                req["property_id"],
            ),
        ):
            out = guard.verify_shared_signature()

        self.assertTrue(out["pass"], out)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["concept_equivalence_authority"])
        self.assertFalse(out["concept_disjointness_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
