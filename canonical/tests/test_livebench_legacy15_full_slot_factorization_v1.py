#!/usr/bin/env python3
import unittest

from canonical.runtime import livebench_legacy15_full_slot_factorization_v1 as f


class FullSlotFactorizationV1Test(unittest.TestCase):
    def test_verification_summary(self):
        out = f.verify()
        self.assertTrue(out["status"].startswith("PASS__FULL_SLOT_FACTORIZATION_CANDIDATE"))
        self.assertEqual(out["structural_identity_sets"], 928)
        self.assertEqual(out["lexical_signature_count"], 192)
        self.assertEqual(out["reduced_structural_numeric_categorical_basis_count"], 60495)
        self.assertFalse(out["acceptance_credit"])

    def test_basis_enumerator_is_total_for_reduced_domains(self):
        self.assertEqual(sum(1 for _ in f.iter_reduced_basis()), 60495)

    def test_all_public_word_less_than_thresholds_share_one_safe_boundary_class(self):
        out = f.word_less_than_global_upper_bound()
        self.assertEqual(out["conservative_global_unpadded_word_upper_bound"], 48)
        self.assertEqual(out["public_minimum_less_than_threshold"], 100)
        self.assertGreater(out["margin"], 0)

    def test_repeat_prompt_arbitrary_text_is_not_a_cross_product_dimension(self):
        out = f.repeat_prompt_equivalence()
        self.assertGreater(out["constructor_prefix_checks"], 0)
        self.assertEqual(
            out["consequence"],
            "NONEMPTY_PROMPT_TO_REPEAT_TEXT_COLLAPSES_TO_ONE_SUCCESS_EQUIVALENCE_CLASS",
        )

    def test_sentence_threshold_classes_are_fail_closed(self):
        out = f.sentence_threshold_factorization()
        self.assertEqual(out["less_than_classes"]["1"], "INTRINSICALLY_UNSAT")
        self.assertIn("BOUNDARY_REPRESENTATIVE_2", out["less_than_classes"]["2_to_20"])
        self.assertIn("independent_runner_obligation", out)


if __name__ == "__main__":
    unittest.main()
