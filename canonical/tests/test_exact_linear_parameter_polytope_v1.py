import unittest

from canonical.runtime.exact_linear_parameter_polytope_v1 import solve


def obs(features, lo, hi):
    return {"features": features, "output_interval": [lo, hi]}


def query(query_id, features):
    return {"query_id": query_id, "features": features}


def base():
    return {
        "feature_semantics_bound": True,
        "observation_intervals_sound": True,
        "observations": [
            obs(["1", "0"], "1", "1"),
            obs(["1", "1"], "3", "3"),
        ],
        "queries": [query("x2", ["1", "2"])],
    }


class ExactLinearParameterPolytopeTests(unittest.TestCase):
    def test_exact_line_recovers_unique_coefficients_and_prediction(self):
        out = solve(base())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["coefficient_bounds"], [["1", "1"], ["2", "2"]])
        self.assertEqual(out["query_predictions"][0]["prediction_interval"], ["5", "5"])
        self.assertEqual(out["vertex_count"], 1)

    def test_noisy_line_gives_exact_prediction_interval(self):
        p = base()
        p["observations"] = [
            obs(["1", "0"], "9/10", "11/10"),
            obs(["1", "1"], "29/10", "31/10"),
        ]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["query_predictions"][0]["prediction_interval"], ["47/10", "53/10"])

    def test_exact_decimal_strings_are_preserved_as_rationals(self):
        p = base()
        p["observations"] = [
            obs(["1", "0"], "0.1", "0.1"),
            obs(["1", "1"], "0.3", "0.3"),
        ]
        p["queries"] = [query("x2", ["1", "2"])]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["query_predictions"][0]["prediction_interval"], ["1/2", "1/2"])

    def test_binary_float_inputs_are_rejected_from_proof_path(self):
        p = base()
        p["observations"][0]["features"][0] = 1.0
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXACT_INPUT_BINDING_FAILED")

    def test_rank_deficient_feature_matrix_fails_closed(self):
        p = {
            "feature_semantics_bound": True,
            "observation_intervals_sound": True,
            "observations": [
                obs(["1", "0"], "0", "1"),
                obs(["2", "0"], "0", "2"),
            ],
            "queries": [],
        }
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_FULL_COLUMN_RANK", out["reason"])

    def test_infeasible_observations_fail_closed(self):
        p = {
            "feature_semantics_bound": True,
            "observation_intervals_sound": True,
            "observations": [
                obs(["1"], "0", "0"),
                obs(["1"], "1", "1"),
            ],
            "queries": [],
        }
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "NO_FEASIBLE_BOUNDED_PARAMETER_POLYTOPE_VERTEX")

    def test_feature_semantics_must_be_bound(self):
        p = base()
        p["feature_semantics_bound"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FEATURE_SEMANTICS_UNBOUND")

    def test_observation_interval_soundness_must_be_bound(self):
        p = base()
        p["observation_intervals_sound"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "OBSERVATION_INTERVAL_SOUNDNESS_UNPROVED")

    def test_query_dimension_mismatch_fails_closed(self):
        p = base()
        p["queries"] = [query("bad", ["1"])]
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "QUERY_EXACT_INPUT_BINDING_FAILED")

    def test_negative_feature_prediction_extrema_are_exact(self):
        p = base()
        p["observations"] = [
            obs(["1", "0"], "0", "2"),
            obs(["1", "1"], "2", "4"),
        ]
        p["queries"] = [query("negative", ["1", "-1"])]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        # beta0 in [0,2], beta0+beta1 in [2,4].
        # beta0-beta1 = 2*beta0-(beta0+beta1), hence [-4,2].
        self.assertEqual(out["query_predictions"][0]["prediction_interval"], ["-4", "2"])

    def test_success_never_grants_acceptance_or_terminal_authority(self):
        out = solve(base())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
