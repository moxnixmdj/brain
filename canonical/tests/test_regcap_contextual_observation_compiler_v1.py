from __future__ import annotations

import unittest

from canonical.runtime.regcap_contextual_observation_compiler_v1 import compile_span


def run(text: str):
    return compile_span(text, start=0, end=len(text))


class Tests(unittest.TestCase):
    def test_designated_releasable_buffer_compiles(self):
        out = run("The cushion is the only designated releasable buffer in the Basel Framework.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "RELEASABILITY_CLASS")
        self.assertEqual(out["outcome"], "BASEL_DESIGNATED_RELEASABLE_BUFFER")
        self.assertFalse(out["concept_identity_authority"])

    def test_basel_buffer_above_minimum_cet1_compiles(self):
        out = run(
            "The buffer is an additional layer of capital above the regulatory "
            "minimums and must be met with CET1."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FRAMEWORK_CLASS")
        self.assertEqual(
            out["outcome"],
            "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        )

    def test_separate_tlac_requirement_compiles(self):
        out = run(
            "The requirement is a separate minimum TLAC requirement alongside "
            "minimum Basel regulatory capital requirements."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FRAMEWORK_CLASS")
        self.assertEqual(out["outcome"], "SEPARATE_MINIMUM_TLAC_REQUIREMENT")

    def test_ccob_functional_signature_compiles(self):
        out = run("The buffer can be drawn down as losses are incurred.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(out["outcome"], "DRAWDOWN_AS_LOSSES_ARE_INCURRED")

    def test_ccyb_functional_signature_compiles(self):
        out = run(
            "The cushion is released when system-wide risk crystallises or dissipates."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        )

    def test_tlac_functional_signature_compiles(self):
        out = run(
            "The capacity provides loss-absorbing and recapitalisation capacity "
            "available in resolution for a failing G-SIB."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        )

    def test_ccob_structural_signature_compiles(self):
        out = run("The cushion is 2.5% CET1 above the regulatory minimum.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "STRUCTURAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        )

    def test_ccyb_structural_signature_compiles(self):
        out = run(
            "The buffer extends the capital conservation buffer and is met with CET1."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "STRUCTURAL_SIGNATURE_CLASS")
        self.assertEqual(out["outcome"], "EXTENDS_CCOB_AND_MET_WITH_CET1")

    def test_partial_release_fact_is_not_upgraded(self):
        out = run("The cushion is released when risk dissipates.")
        self.assertFalse(out["pass"])

    def test_partial_resolution_fact_is_not_upgraded(self):
        out = run(
            "The capacity is available in resolution to recapitalise a failing G-SIB."
        )
        self.assertFalse(out["pass"])

    def test_partial_numeric_fact_is_not_upgraded(self):
        out = run("The cushion is 2.5% above the regulatory minimum.")
        self.assertFalse(out["pass"])

    def test_naked_phrase_is_unresolved(self):
        out = run("loss-absorbing cushion")
        self.assertFalse(out["pass"])

    def test_wrong_releasability_word_is_unresolved(self):
        out = run("The cushion is a releasable buffer.")
        self.assertFalse(out["pass"])

    def test_source_span_is_exactly_bound(self):
        text = (
            "Prefix. The cushion is the only designated releasable buffer "
            "in the Basel Framework. Suffix."
        )
        start = text.index("The cushion")
        end = text.index(" Suffix")
        out = compile_span(text, start=start, end=end)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["source_span"], [start, end])

    def test_partial_span_does_not_inherit_missing_context(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        start = text.index("designated")
        out = compile_span(text, start=start, end=len(text))
        self.assertFalse(out["pass"])

    def test_no_terminal_or_candidate_completeness_authority(self):
        out = run("The cushion is the only designated releasable buffer in the Basel Framework.")
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


    def test_this_determiner_and_us_crystallizes_compile(self):
        out = run(
            "This cushion is released when system-wide risk crystallizes or dissipates."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        )

    def test_us_recapitalization_spelling_compiles(self):
        out = run(
            "This capacity provides loss-absorbing and recapitalization capacity "
            "available in resolution for a failing G-SIB."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        )

    def test_this_determiner_numeric_signature_compiles(self):
        out = run("This cushion is 2.5% CET1 above the regulatory minimum.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "STRUCTURAL_SIGNATURE_CLASS")

    def test_system_wide_risk_dissipates_only_remains_unresolved(self):
        out = run("The cushion is released when system-wide risk dissipates.")
        self.assertFalse(out["pass"])

    def test_bare_numeric_np_remains_unresolved(self):
        out = run("A 2.5% CET1 buffer above the regulatory minimum.")
        self.assertFalse(out["pass"])

    def test_bare_tlac_np_remains_unresolved(self):
        out = run(
            "Loss-absorbing and recapitalisation capacity available in resolution "
            "for a G-SIB."
        )
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
