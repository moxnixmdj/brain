from __future__ import annotations

import unittest

from canonical.runtime import regcap_contextual_fact_compiler_v1 as ctx


class Tests(unittest.TestCase):
    def test_ccob_structural_profile_proves_only_three_facts(self):
        text = (
            "The buffer is 2.5% and is comprised of CET1 above the "
            "regulatory minimum capital requirement."
        )
        out = ctx.compile_context(text, source_id="doc:A")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["matched_profiles"], ["CCOB_STRUCTURAL_PROFILE"])
        self.assertEqual(
            set(out["proved_facts"]),
            {ctx.FACT_CCOB_25, ctx.FACT_CET1, ctx.FACT_ABOVE_MIN},
        )
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["exact_profile_identity_claimed"])

    def test_ccyb_release_profile(self):
        text = "The buffer is released when system-wide risk crystallises or dissipates."
        out = ctx.compile_context(text, source_id="doc:B")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["matched_profiles"], ["CCYB_RELEASE_PROFILE"])
        self.assertEqual(out["proved_facts"], [ctx.FACT_RELEASE])
        self.assertFalse(out["concept_identity_authority"])

    def test_ccyb_us_spelling_profile(self):
        text = "The buffer is released when system-wide risk crystallizes or dissipates."
        out = ctx.compile_context(text, source_id="doc:B")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["proved_facts"], [ctx.FACT_RELEASE])

    def test_tlac_resolution_profile(self):
        text = (
            "A G-SIB has loss-absorbing and recapitalisation capacity "
            "available in resolution."
        )
        out = ctx.compile_context(text, source_id="doc:C")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["matched_profiles"], ["TLAC_RESOLUTION_PROFILE"])
        self.assertEqual(
            set(out["proved_facts"]),
            {ctx.FACT_GSIB, ctx.FACT_LOSS, ctx.FACT_RECAP, ctx.FACT_RESOLUTION},
        )
        self.assertFalse(out["concept_identity_authority"])

    def test_tlac_recapitalization_us_spelling(self):
        text = (
            "A global systemically important bank has loss-absorbing "
            "recapitalization capacity in resolution."
        )
        out = ctx.compile_context(text, source_id="doc:C")
        self.assertTrue(out["pass"], out)
        self.assertIn(ctx.FACT_RESOLUTION, out["proved_facts"])

    def test_loss_absorbing_alone_does_not_trigger_tlac_profile(self):
        out = ctx.compile_context("This is a loss-absorbing cushion.", source_id="doc:D")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "UNRESOLVED__NO_BOUND_CONTEXT_PROFILE")
        self.assertEqual(out["proved_facts"], [])

    def test_resolution_without_gsib_and_recapitalisation_is_unresolved(self):
        out = ctx.compile_context(
            "The resource is available in resolution.",
            source_id="doc:E",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["proved_facts"], [])

    def test_ccob_missing_above_minimum_is_unresolved(self):
        out = ctx.compile_context(
            "The buffer is 2.5% and comprised of CET1.",
            source_id="doc:F",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["proved_facts"], [])

    def test_ccyb_missing_release_trigger_is_unresolved(self):
        out = ctx.compile_context(
            "System-wide risk may crystallise or dissipate.",
            source_id="doc:G",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["proved_facts"], [])

    def test_multiple_profiles_can_coexist_without_identity(self):
        text = (
            "The buffer is 2.5% CET1 above the regulatory minimum. "
            "It is released when system-wide risk crystallises or dissipates."
        )
        out = ctx.compile_context(text, source_id="doc:H")
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["matched_profiles"]),
            {"CCOB_STRUCTURAL_PROFILE", "CCYB_RELEASE_PROFILE"},
        )
        self.assertFalse(out["concept_identity_authority"])

    def test_source_hash_changes_with_bytes(self):
        a = ctx.compile_context(
            "The buffer is released when system-wide risk crystallises or dissipates.",
            source_id="doc:I",
        )
        b = ctx.compile_context(
            "The buffer is released when system-wide risk crystallises or dissipates. ",
            source_id="doc:I",
        )
        self.assertTrue(a["pass"])
        self.assertTrue(b["pass"])
        self.assertNotEqual(a["source_text_sha256"], b["source_text_sha256"])

    def test_no_terminal_or_promotion_authority(self):
        out = ctx.compile_context(
            "A G-SIB has loss-absorbing and recapitalisation capacity available in resolution.",
            source_id="doc:J",
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
