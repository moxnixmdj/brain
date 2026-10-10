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

    def test_release_when_risk_dissipates_is_not_silently_upgraded(self):
        out = run("The cushion is released when system-wide risk dissipates.")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_CERTIFIED_CONTEXTUAL_OBSERVATION",
        )

    def test_resolution_recapitalisation_is_not_silently_upgraded(self):
        out = run(
            "The capacity is available in resolution to recapitalise a failing G-SIB."
        )
        self.assertFalse(out["pass"])

    def test_numeric_cet1_context_is_not_silently_upgraded(self):
        out = run("The cushion is 2.5% CET1 above the regulatory minimum.")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
