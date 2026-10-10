from __future__ import annotations

import unittest

from canonical.runtime import regcap_contextual_discriminator_binding_v1 as bind
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_ccob_structural_context_resolves_ccob_relative_to_three(self):
        text = "The buffer is 2.5% CET1 above the regulatory minimum."
        out = bind.resolve_relative(
            text,
            source_id="doc:A",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_id"], regcap.CCOB)
        self.assertTrue(out["relative_only"])
        self.assertFalse(out["global_concept_identity_authority"])
        self.assertFalse(out["candidate_universe_complete"])

    def test_ccyb_release_context_resolves_ccyb_relative_to_three(self):
        text = "The buffer is released when system-wide risk crystallises or dissipates."
        out = bind.resolve_relative(
            text,
            source_id="doc:B",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_id"], regcap.CCYB)

    def test_tlac_resolution_context_resolves_tlac_relative_to_three(self):
        text = (
            "A G-SIB has loss-absorbing and recapitalisation capacity "
            "available in resolution."
        )
        out = bind.resolve_relative(
            text,
            source_id="doc:C",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_id"], regcap.TLAC)

    def test_relative_subset_resolution_does_not_claim_completeness(self):
        text = "The buffer is released when system-wide risk crystallises or dissipates."
        out = bind.resolve_relative(
            text,
            source_id="doc:D",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_id"], regcap.CCYB)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["open_world_ontology_complete"])

    def test_naked_phrase_remains_unresolved(self):
        out = bind.resolve_relative(
            "loss-absorbing cushion",
            source_id="doc:E",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "UNRESOLVED__NO_BOUND_CONTEXT_PROFILE")

    def test_conflicting_profiles_do_not_force_candidate(self):
        text = (
            "The buffer is 2.5% CET1 above the regulatory minimum. "
            "It is released when system-wide risk crystallises or dissipates."
        )
        out = bind.resolve_relative(
            text,
            source_id="doc:F",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "CONFLICT__BOUND_CONTEXT_PROFILES_HAVE_NO_COMMON_MATRIX_CANDIDATE",
        )
        self.assertFalse(out["global_concept_identity_authority"])

    def test_candidate_outside_matrix_fails_closed(self):
        out = bind.resolve_relative(
            "The buffer is 2.5% CET1 above the regulatory minimum.",
            source_id="doc:G",
            declared_candidate_ids=[regcap.CCOB, "REGCAP::MREL"],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "DECLARED_CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    def test_matrix_authentication_failure_fails_closed(self):
        out = bind.resolve_relative(
            "The buffer is 2.5% CET1 above the regulatory minimum.",
            source_id="doc:H",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "DISCRIMINATOR_MATRIX_NOT_AUTHENTICATED")

    def test_no_terminal_promotion_or_acceptance_authority(self):
        out = bind.resolve_relative(
            "A G-SIB has loss-absorbing and recapitalisation capacity available in resolution.",
            source_id="doc:I",
            declared_candidate_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_concept_identity_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
