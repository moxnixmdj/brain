from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_hidden_rubric_indistinguishability_v1 import (
    HiddenRubricCutError,
    prove_two_rubric_cut,
)


def contract():
    return {
        "public_contract_blob": "32b44233529221ac6aa21132782690a1fbf0f748",
        "public_superdomain_blob": "cf612adf37da0cf5d7d1940b4656fd72e483481e",
        "private_rubric_semantics_known": False,
        "arbitrary_finite_hidden_binary_predicates_included": True,
        "all_finite_submission_bytes_included": True,
    }


class Tests(unittest.TestCase):
    def test_deterministic_output_a_fails_world_b(self):
        out = prove_two_rubric_cut(
            public_contract=contract(),
            policy_support=["A"],
            output_a="A",
            output_b="B",
        )
        self.assertTrue(out["policy_top_in_world_a"])
        self.assertFalse(out["policy_top_in_world_b"])
        self.assertFalse(out["policy_top_in_both_worlds"])

    def test_deterministic_output_b_fails_world_a(self):
        out = prove_two_rubric_cut(
            public_contract=contract(),
            policy_support=["B"],
            output_a="A",
            output_b="B",
        )
        self.assertFalse(out["policy_top_in_world_a"])
        self.assertTrue(out["policy_top_in_world_b"])

    def test_randomized_support_a_b_is_not_top_in_either_singleton_world(self):
        out = prove_two_rubric_cut(
            public_contract=contract(),
            policy_support=["A", "B"],
            output_a="A",
            output_b="B",
        )
        self.assertFalse(out["policy_top_in_world_a"])
        self.assertFalse(out["policy_top_in_world_b"])

    def test_third_output_fails_both_worlds(self):
        out = prove_two_rubric_cut(
            public_contract=contract(),
            policy_support=["C"],
            output_a="A",
            output_b="B",
        )
        self.assertFalse(out["policy_top_in_world_a"])
        self.assertFalse(out["policy_top_in_world_b"])

    def test_empty_policy_support_rejected(self):
        with self.assertRaisesRegex(HiddenRubricCutError, "POLICY_SUPPORT_MUST_BE_NONEMPTY"):
            prove_two_rubric_cut(
                public_contract=contract(),
                policy_support=[],
                output_a="A",
                output_b="B",
            )

    def test_same_outputs_rejected(self):
        with self.assertRaisesRegex(HiddenRubricCutError, "DISTINCT_OUTPUTS_REQUIRED"):
            prove_two_rubric_cut(
                public_contract=contract(),
                policy_support=["A"],
                output_a="A",
                output_b="A",
            )

    def test_wrong_public_contract_blob_rejected(self):
        c = contract()
        c["public_contract_blob"] = "0" * 40
        with self.assertRaisesRegex(HiddenRubricCutError, "PUBLIC_CONTRACT_BLOB_MISMATCH"):
            prove_two_rubric_cut(
                public_contract=c,
                policy_support=["A"],
                output_a="A",
                output_b="B",
            )

    def test_cut_does_not_claim_actual_rubrics_adversarial(self):
        out = prove_two_rubric_cut(
            public_contract=contract(),
            policy_support=["A"],
            output_a="A",
            output_b="B",
        )
        self.assertTrue(out["does_not_claim_actual_private_rubrics_are_adversarial"])
        self.assertTrue(out["does_not_disprove_actual_aa_noninferiority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
