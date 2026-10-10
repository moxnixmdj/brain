from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_four_way_loss_absorption_nonseparation_guard_v1 as guard


def ok(concept):
    return {
        "pass": True,
        "semantic_truth_authority": True,
        "concept_id": concept,
        "property_id": guard.SHARED_PROPERTY,
        "relation": "ENTAILS",
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_all_four_shared_property_is_nonseparating(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok(req["concept_id"]),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            side_effect=lambda req, **_: ok(req["concept_id"]),
        ):
            out = guard.verify_shared_loss_absorption()

        self.assertTrue(out["pass"], out)
        self.assertEqual(set(out["candidate_concept_ids"]), set(guard.CONCEPTS))
        self.assertTrue(out["property_entails_all_bound_candidates"])
        self.assertFalse(out["property_separates_any_candidate"])
        self.assertFalse(out["reverse_classification_authorized"])
        self.assertTrue(out["additional_authenticated_discriminator_required"])

    def test_regcap_failure_fails_closed(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            return_value={"pass": False, "reason": "forced"},
        ):
            out = guard.verify_shared_loss_absorption()
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("REGCAP_PROPERTY_AUTHORITY_FAILED", out["reason"])

    def test_mrel_failure_fails_closed(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok(req["concept_id"]),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            return_value={"pass": False, "reason": "forced"},
        ):
            out = guard.verify_shared_loss_absorption()
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("MREL_PROPERTY_AUTHORITY_FAILED", out["reason"])

    def test_no_identity_or_completeness_authority(self):
        with patch.object(
            guard.regcap,
            "verify_property_request",
            side_effect=lambda req, **_: ok(req["concept_id"]),
        ), patch.object(
            guard.mrel,
            "verify_property_request",
            side_effect=lambda req, **_: ok(req["concept_id"]),
        ):
            out = guard.verify_shared_loss_absorption()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["concept_equivalence_authority"])
        self.assertFalse(out["concept_disjointness_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_real_bound_authorities_agree_on_shared_property(self):
        out = guard.verify_shared_loss_absorption()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__FOUR_WAY_LOSS_ABSORPTION_PROPERTY_AUTHENTICATED_NONSEPARATING",
        )
        self.assertEqual(
            set(out["authenticated_results"]),
            set(guard.CONCEPTS),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
