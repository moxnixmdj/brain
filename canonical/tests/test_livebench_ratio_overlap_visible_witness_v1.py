import unittest

from canonical.runtime.livebench_ratio_overlap_visible_witness_v1 import (
    exact_frozen_overlap_percent,
    synthesize_from_visible_reference,
)


class LiveBenchRatioOverlapVisibleWitnessTests(unittest.TestCase):
    def test_exact_50_percent_whitespace_invariant(self):
        visible = "alpha beta gamma"
        witness = synthesize_from_visible_reference(visible, 50)
        self.assertLessEqual(abs(witness.predicted_percent - 50), 2)
        for exact in ("alpha beta gamma", "alpha\nbeta\tgamma", "alpha   beta gamma"):
            actual = exact_frozen_overlap_percent(witness.response, exact)
            self.assertLessEqual(abs(actual - 50), 2)

    def test_low_overlap_constructive_route(self):
        visible = "For her installation"
        witness = synthesize_from_visible_reference(visible, 6)
        actual = exact_frozen_overlap_percent(witness.response, visible)
        self.assertLessEqual(abs(actual - 6), 2)

    def test_generation_api_has_no_hidden_reference_input(self):
        visible = "Use induction to prove the following claims."
        witness = synthesize_from_visible_reference(visible, 72)
        self.assertTrue(witness.response)
        self.assertLessEqual(abs(witness.predicted_percent - 72), 2)


if __name__ == "__main__":
    unittest.main()
