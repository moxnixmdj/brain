from __future__ import annotations

from pathlib import Path
import unittest

from canonical.runtime import regcap_contextual_observation_compiler_v1 as obs


ROOT = Path(__file__).resolve().parents[2]

DUPLICATE_PATHS = (
    "canonical/runtime/regcap_contextual_fact_compiler_v1.py",
    "canonical/runtime/regcap_contextual_discriminator_binding_v1.py",
    "canonical/tests/test_regcap_contextual_fact_compiler_v1.py",
    "canonical/tests/test_regcap_contextual_discriminator_binding_v1.py",
)


def compile_sentence(text: str):
    return obs.compile_span(text, start=0, end=len(text))


class RegcapContextualSingleAuthorityTests(unittest.TestCase):
    def test_parallel_runtime_and_live_tests_are_absent(self):
        for rel in DUPLICATE_PATHS:
            self.assertFalse((ROOT / rel).exists(), rel)

    def test_safe_ccob_surface_remains_owned_by_canonical_compiler(self):
        out = compile_sentence(
            "This cushion is 2.5% CET1 above the regulatory minimum."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "STRUCTURAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        )
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["concept_identity_authority"])

    def test_safe_ccyb_us_spelling_remains_owned_by_canonical_compiler(self):
        out = compile_sentence(
            "This cushion is released when system-wide risk crystallizes or dissipates."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        )

    def test_safe_tlac_us_spelling_remains_owned_by_canonical_compiler(self):
        out = compile_sentence(
            "This capacity provides loss-absorbing and recapitalization capacity "
            "in resolution for a failing G-SIB."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_id"], "FUNCTIONAL_SIGNATURE_CLASS")
        self.assertEqual(
            out["outcome"],
            "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        )

    def test_weaker_release_trigger_stays_unresolved(self):
        out = compile_sentence(
            "The buffer is released when system-wide risk dissipates."
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_CERTIFIED_CONTEXTUAL_OBSERVATION",
        )

    def test_bare_ccob_noun_phrase_stays_unresolved(self):
        out = compile_sentence("2.5% CET1 above the regulatory minimum.")
        self.assertFalse(out["pass"])

    def test_bare_tlac_profile_stays_unresolved(self):
        out = compile_sentence(
            "A G-SIB has loss-absorbing and recapitalisation capacity available "
            "in resolution."
        )
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
