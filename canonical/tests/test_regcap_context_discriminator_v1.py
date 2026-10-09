from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_context_discriminator_v1 as ctx
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


def bound_scope():
    return {
        "kind": ctx.BOUND_SCOPE,
        "scope_complete": True,
        "candidate_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
    }


def phrase_span(text):
    start = text.index("loss-absorbing cushion")
    return start, start + len("loss-absorbing cushion")


class Tests(unittest.TestCase):
    def _resolve(self, text, scope=None):
        ps, pe = phrase_span(text)
        with patch.object(
            regcap,
            "verify_projection_pack",
            side_effect=fake_projection,
        ):
            return ctx.resolve(
                text,
                source_id="doc:A",
                phrase_start=ps,
                phrase_end=pe,
                context_start=0,
                context_end=len(text),
                mapping_scope=scope if scope is not None else bound_scope(),
                matrix_projection_verifier=fake_projection,
            )

    def test_ccyb_explicit_releasability_context_resolves_in_bound_scope(self):
        text = (
            "This loss-absorbing cushion is the only designated releasable "
            "buffer in the Basel Framework."
        )
        out = self._resolve(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["mapped_concept_id"], regcap.CCYB)
        self.assertTrue(out["bounded_scope_identity_authority"])
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])

    def test_tlac_explicit_framework_context_resolves_in_bound_scope(self):
        text = (
            "This loss-absorbing cushion is a Minimum External TLAC requirement "
            "alongside minimum regulatory capital requirements."
        )
        out = self._resolve(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["mapped_concept_id"], regcap.TLAC)

    def test_basel_buffer_context_reduces_but_does_not_resolve_ccob_vs_ccyb(self):
        text = (
            "This loss-absorbing cushion is an additional layer of capital "
            "above the regulatory minimums and must be met with CET1."
        )
        out = self._resolve(text)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__BOUND_CONTEXT_REDUCES_BUT_DOES_NOT_RESOLVE",
        )
        self.assertEqual(
            set(out["surviving_candidate_ids"]),
            {regcap.CCOB, regcap.CCYB},
        )
        self.assertIsNone(out["mapped_concept_id"])

    def test_generic_release_language_does_not_answer_matrix_observation(self):
        text = "This loss-absorbing cushion may be released during stress."
        out = self._resolve(text)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__NO_BOUND_CONTEXT_DISCRIMINATOR_PROVED",
        )

    def test_resolution_and_recapitalisation_words_do_not_auto_map_tlac(self):
        text = (
            "This loss-absorbing cushion provides recapitalisation capacity "
            "in resolution."
        )
        out = self._resolve(text)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__NO_BOUND_CONTEXT_DISCRIMINATOR_PROVED",
        )

    def test_open_world_scope_never_receives_identity(self):
        text = (
            "This loss-absorbing cushion is the only designated releasable "
            "buffer in the Basel Framework."
        )
        out = self._resolve(
            text,
            scope={"kind": "OPEN_WORLD", "scope_complete": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__CONTEXT_FACTS_CANNOT_GRANT_OPEN_WORLD_IDENTITY",
        )
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_bound_scope_candidate_mismatch_fails_closed(self):
        text = (
            "This loss-absorbing cushion is the only designated releasable "
            "buffer in the Basel Framework."
        )
        out = self._resolve(
            text,
            scope={
                "kind": ctx.BOUND_SCOPE,
                "scope_complete": True,
                "candidate_ids": [regcap.CCOB, regcap.CCYB],
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "BOUND_SCOPE_CANDIDATES_MISMATCH")

    def test_conflicting_exact_context_outcomes_fail_closed(self):
        text = (
            "This loss-absorbing cushion is the only designated releasable "
            "buffer in the Basel Framework and is also a Minimum External TLAC "
            "requirement alongside minimum regulatory capital requirements."
        )
        out = self._resolve(text)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "AUTHENTICATED_CONTEXT_CONTRADICTS_BOUND_CANDIDATE_SET",
        )

    def test_context_span_binding_prevents_outside_text_from_being_used(self):
        text = (
            "Outside note: only designated releasable buffer in the Basel Framework. "
            "Target: loss-absorbing cushion."
        )
        ps, pe = phrase_span(text)
        target_start = text.index("Target:")
        with patch.object(
            regcap,
            "verify_projection_pack",
            side_effect=fake_projection,
        ):
            out = ctx.resolve(
                text,
                source_id="doc:A",
                phrase_start=ps,
                phrase_end=pe,
                context_start=target_start,
                context_end=len(text),
                mapping_scope=bound_scope(),
                matrix_projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__NO_BOUND_CONTEXT_DISCRIMINATOR_PROVED",
        )

    def test_no_terminal_or_global_alias_authority(self):
        text = (
            "This loss-absorbing cushion is the only designated releasable "
            "buffer in the Basel Framework."
        )
        out = self._resolve(text)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
