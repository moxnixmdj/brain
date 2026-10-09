from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_context_signature_v1 as ctx
from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v3 as v3
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

RAW = "loss-absorbing cushion"


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


def compile_text(text):
    start = text.index(RAW)
    return ctx.compile_context(
        text,
        source_id="doc:A",
        start=start,
        end=start + len(RAW),
    )


def resolve_text(text):
    start = text.index(RAW)
    return ctx.resolve_relative(
        text,
        source_id="doc:A",
        start=start,
        end=start + len(RAW),
        candidate_concept_ids=[regcap.CCOB, regcap.CCYB, regcap.TLAC],
        projection_verifier=fake_projection,
    )


def open_base():
    return {
        "schema": "V2",
        "status": "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
        "pass": True,
        "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
        "mapped_concept_id": None,
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "semantic_identity_authority": False,
        "terminal_authority": False,
    }


class ContextSignatureTests(unittest.TestCase):
    def test_ccob_functional_signature(self):
        text = "The loss-absorbing cushion can be drawn down as losses are incurred."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.CCOB)

    def test_ccyb_functional_signature(self):
        text = "The loss-absorbing cushion is released when system-wide risk crystallises or dissipates."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.CCYB)

    def test_tlac_functional_signature(self):
        text = "For a G-SIB, the loss-absorbing cushion provides loss-absorbing and recapitalisation capacity available in resolution."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.TLAC)

    def test_ccob_structural_signature(self):
        text = "The loss-absorbing cushion is a 2.5% CET1 buffer above the regulatory minimum capital requirement."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.CCOB)

    def test_ccyb_structural_signature(self):
        text = "The loss-absorbing cushion extends the size of the capital conservation buffer and is met with CET1."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.CCYB)

    def test_tlac_structural_signature(self):
        text = "The loss-absorbing cushion is a Minimum External TLAC requirement alongside minimum regulatory capital requirements."
        out = compile_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_candidate_hint"], regcap.TLAC)

    def test_naked_phrase_stays_open(self):
        out = compile_text(RAW)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__NO_BOUND_CONTEXT_SIGNATURE")

    def test_clue_in_other_sentence_does_not_leak(self):
        text = "The loss-absorbing cushion remains available. It can be drawn down as losses are incurred."
        out = compile_text(text)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__NO_BOUND_CONTEXT_SIGNATURE")

    def test_conflicting_functional_signatures_fail_closed(self):
        text = (
            "The loss-absorbing cushion can be drawn down as losses are incurred "
            "and is released when system-wide risk crystallises or dissipates."
        )
        out = compile_text(text)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CONFLICTING_CONTEXT_SIGNATURES")

    def test_context_outcome_selects_ccyb_relative_to_three_rivals(self):
        text = "The loss-absorbing cushion is released when system-wide risk crystallises or dissipates."
        out = resolve_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__UNIQUE_CANDIDATE_RELATIVE_TO_DECLARED_BOUND_RIVALS",
        )
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCYB)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["open_world_identity_authorized"])

    def test_context_outcome_selects_tlac_relative_to_three_rivals(self):
        text = "For a G-SIB, the loss-absorbing cushion provides loss-absorbing and recapitalisation capacity available in resolution."
        out = resolve_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_selected_concept_id"], regcap.TLAC)

    def test_context_outcome_selects_ccob_relative_to_three_rivals(self):
        text = "The loss-absorbing cushion is a 2.5 percent Common Equity Tier 1 buffer above the regulatory minimum."
        out = resolve_text(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCOB)

    def test_candidate_outside_matrix_fails_closed(self):
        text = "The loss-absorbing cushion can be drawn down as losses are incurred."
        start = text.index(RAW)
        out = ctx.resolve_relative(
            text,
            source_id="doc:A",
            start=start,
            end=start + len(RAW),
            candidate_concept_ids=[regcap.CCOB, "REGCAP::MREL"],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CANDIDATE_OUTSIDE_MATRIX_DOMAIN")


class GroundingV3Tests(unittest.TestCase):
    def test_stronger_v2_exact_identity_is_preserved(self):
        exact = {
            **open_base(),
            "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
            "mapped_concept_id": regcap.CCOB,
            "fully_semantically_bound": True,
            "opaque_remainder_required": False,
            "semantic_identity_authority": True,
        }
        with patch.object(v3.v2, "ground", return_value=exact), patch.object(
            v3.context,
            "resolve_relative",
        ) as mocked:
            out = v3.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
                projection_verifier=fake_projection,
            )
        self.assertEqual(out["mapped_concept_id"], regcap.CCOB)
        self.assertTrue(out["fully_semantically_bound"])
        self.assertFalse(out["context_signature_attempted"])
        mocked.assert_not_called()

    def test_relative_selection_never_upgrades_identity(self):
        text = "The loss-absorbing cushion is released when system-wide risk crystallises or dissipates."
        start = text.index(RAW)
        with patch.object(v3.v2, "ground", return_value=open_base()):
            out = v3.ground(
                text,
                source_id="doc:A",
                start=start,
                end=start + len(RAW),
                projection_verifier=fake_projection,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCYB)
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["fully_semantically_bound"])
        self.assertTrue(out["opaque_remainder_required"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_context_authority_failure_preserves_v2_result(self):
        text = "The loss-absorbing cushion is released when system-wide risk crystallises or dissipates."
        start = text.index(RAW)
        with patch.object(v3.v2, "ground", return_value=open_base()):
            out = v3.ground(
                text,
                source_id="doc:A",
                start=start,
                end=start + len(RAW),
                projection_verifier=lambda _pack: {"pass": False},
            )
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
        )
        self.assertTrue(out["context_refinement_preserved_base_after_failure"])
        self.assertIsNone(out["relative_selected_concept_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
