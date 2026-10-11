import unittest

from canonical.runtime.gdpval_crowdbt_unseen_entrant_identifiability_v1 import (
    bt_pairwise_probability,
    unseen_entrant_invariance,
    unseen_vs_opus_probability_examples,
    verify_unseen_entrant_cut,
)


class Tests(unittest.TestCase):
    def setUp(self):
        self.strengths = {"OPUS": 2.0, "A": 1.0, "ANCHOR": 0.0}
        self.rows = [
            ("OPUS", "A", 1.0),
            ("OPUS", "ANCHOR", 1.0),
            ("A", "ANCHOR", 0.5),
        ]

    def test_incumbent_likelihood_is_invariant_to_unseen_brain_strength(self):
        out = unseen_entrant_invariance(self.strengths, self.rows)
        self.assertTrue(out["invariant"])
        self.assertFalse(out["unseen_strength_identified"])

    def test_unseen_brain_can_be_below_opus(self):
        p = bt_pairwise_probability(-20.0, 0.0)
        self.assertLess(p, 0.5)

    def test_unseen_brain_can_equal_opus(self):
        self.assertEqual(bt_pairwise_probability(0.0, 0.0), 0.5)

    def test_unseen_brain_can_be_above_opus(self):
        p = bt_pairwise_probability(20.0, 0.0)
        self.assertGreater(p, 0.5)

    def test_same_opus_strength_allows_opposite_brain_conclusions(self):
        out = unseen_vs_opus_probability_examples(3.0)
        self.assertLess(out["very_low_brain"], 0.5)
        self.assertEqual(out["equal_brain"], 0.5)
        self.assertGreater(out["very_high_brain"], 0.5)

    def test_verifier_names_information_gap(self):
        out = verify_unseen_entrant_cut()
        self.assertTrue(out["brain_vs_opus_probability_not_identified_by_incumbent_graph"])

    def test_never_grants_terminal_credit(self):
        self.assertEqual(verify_unseen_entrant_cut()["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
