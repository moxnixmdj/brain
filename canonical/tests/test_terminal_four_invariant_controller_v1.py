import unittest
from canonical.runtime.terminal_four_invariant_controller_v1 import project

class TestFourInvariantController(unittest.TestCase):
    def test_projection_is_fail_closed_and_zero_credit(self):
        x = project()
        self.assertTrue(x["pass"], x)
        self.assertFalse(x["terminal"])
        self.assertEqual(x["terminal_credit_delta"], 0)
        self.assertEqual(x["current_open_truth_obligations"], 29)

    def test_exact_four_invariants(self):
        x = project()
        self.assertEqual(set(x["invariants"]), {
            "A_TARGET_COVERAGE",
            "B_TARGET_RELATIVE_DISTRIBUTIONAL_DOMINANCE",
            "C_COMPOSITION_AND_TRANSFORM_CLOSURE",
            "D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE",
        })
        self.assertFalse(any(x["invariants"].values()))

    def test_missing_proof_cannot_authorize_new_mechanism(self):
        x = project()
        self.assertFalse(x["new_capability_mechanism_authorized_from_missing_proof"])
        self.assertFalse(x["persistent_opus_specific_residual_authorized_without_pstar_proof"])

    def test_no_unfocused_benchmarking(self):
        self.assertFalse(project()["broad_benchmark_authorized_without_identified_information_gain"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
