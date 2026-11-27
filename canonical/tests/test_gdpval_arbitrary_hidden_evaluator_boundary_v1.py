import unittest

from canonical.runtime.gdpval_arbitrary_hidden_evaluator_boundary_v1 import (
    arbitrary_hidden_evaluator_universal_noninferiority_possible,
    blind_event_judge_expected_net_opus_advantage,
    laws_equal,
    opus_favoring_event,
    verify_arbitrary_evaluator_boundary,
)


class Tests(unittest.TestCase):
    def test_equal_laws_have_no_separating_event(self):
        b = {"a": 0.4, "b": 0.6}
        self.assertTrue(laws_equal(b, dict(b)))
        out = arbitrary_hidden_evaluator_universal_noninferiority_possible(b, dict(b))
        self.assertFalse(out["separating_blind_judge_exists"])

    def test_unequal_laws_produce_opus_favoring_event(self):
        b = {"a": 0.8, "b": 0.2}
        o = {"a": 0.3, "b": 0.7}
        event, gap = opus_favoring_event(b, o)
        self.assertEqual(event, {"b"})
        self.assertGreater(gap, 0.0)

    def test_event_judge_advantage_equals_probability_gap(self):
        p_b, p_o = 0.2, 0.7
        advantage = blind_event_judge_expected_net_opus_advantage(p_b, p_o)
        self.assertAlmostEqual(advantage, p_o - p_b)

    def test_separating_judge_is_blind_to_model_identity(self):
        b = {"red": 0.9, "blue": 0.1}
        o = {"red": 0.1, "blue": 0.9}
        out = arbitrary_hidden_evaluator_universal_noninferiority_possible(b, o)
        self.assertTrue(out["separating_blind_judge_exists"])
        self.assertIn("blue", out["opus_favoring_event"])

    def test_arbitrary_lane_requires_u_when_laws_differ(self):
        out = arbitrary_hidden_evaluator_universal_noninferiority_possible(
            {"x": 1.0}, {"y": 1.0}
        )
        self.assertEqual(out["route"], "E_OR_M_OR_U_EQUALITY_REQUIRED_FOR_CURRENT_THEOREM")

    def test_verifier(self):
        out = verify_arbitrary_evaluator_boundary()
        self.assertTrue(out["arbitrary_evaluator_lane_collapses_to_U_equality"])

    def test_never_grants_terminal_credit(self):
        self.assertEqual(verify_arbitrary_evaluator_boundary()["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
