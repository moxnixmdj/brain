import unittest

from canonical.runtime.robust_functional_adequacy_cegar_v1 import solve


A = "a" * 64
B = "b" * 64


def candidate(candidate_id, commitment, bounds, brain_owned=True):
    return {
        "candidate_id": candidate_id,
        "brain_owned": brain_owned,
        "policy_commitment_sha256": commitment,
        "loss_upper_bounds": bounds,
    }


def base():
    return {
        "metric_semantics_bound": True,
        "challenge_cover_complete": True,
        "loss_bounds_sound": True,
        "world_cover_sound": True,
        "adequacy_threshold": "1/10",
        "world_ids": ["w1", "w2"],
        "challenge_ids": ["c1", "c2"],
        "candidates": [
            candidate(
                "h1",
                A,
                {
                    "c1": {"w1": "1/20", "w2": "1/10"},
                    "c2": {"w1": "1/25", "w2": "1/12"},
                },
            )
        ],
    }


class RobustFunctionalAdequacyCegarTests(unittest.TestCase):
    def test_common_law_certifies_at_threshold(self):
        out = solve(base())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["common_law_certified"])
        self.assertTrue(out["conditional_common_law_proved"])
        self.assertFalse(out["upstream_authentication_performed"])
        self.assertEqual(out["selected_candidate_id"], "h1")
        self.assertEqual(out["selected_worst_case_loss_upper_bound"], "1/10")
        self.assertEqual(
            out["status"],
            "CONDITIONAL_PASS__COMMON_LAW_ROBUSTLY_ADEQUATE_IF_DECLARED_PREMISES_ARE_AUTHENTIC",
        )

    def test_minimax_candidate_beats_lower_average_candidate(self):
        p = base()
        p["adequacy_threshold"] = "1"
        p["candidates"] = [
            candidate(
                "spiky",
                A,
                {
                    "c1": {"w1": "0", "w2": "0"},
                    "c2": {"w1": "9/10", "w2": "0"},
                },
            ),
            candidate(
                "robust",
                B,
                {
                    "c1": {"w1": "3/5", "w2": "3/5"},
                    "c2": {"w1": "3/5", "w2": "3/5"},
                },
            ),
        ]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_candidate_id"], "robust")
        self.assertEqual(out["selected_worst_case_loss_upper_bound"], "3/5")

    def test_failure_returns_load_bearing_counterexample(self):
        p = base()
        p["adequacy_threshold"] = "1/100"
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertTrue(out["counterexample_selected"])
        self.assertEqual(out["selected_counterexample"]["challenge_id"], "c1")
        self.assertEqual(out["selected_counterexample"]["world_id"], "w2")
        self.assertEqual(out["selected_counterexample"]["proved_loss_upper_bound"], "1/10")
        self.assertFalse(out["query_optimality_claimed"])

    def test_incomplete_challenge_cover_fails_closed(self):
        p = base()
        p["challenge_cover_complete"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CHALLENGE_COVER_COMPLETENESS_UNPROVED")

    def test_unsound_loss_bounds_fail_closed(self):
        p = base()
        p["loss_bounds_sound"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "LOSS_BOUND_SOUNDNESS_UNPROVED")

    def test_incomplete_world_cover_fails_closed(self):
        p = base()
        p["world_cover_sound"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORLD_COVER_SOUNDNESS_UNPROVED")

    def test_non_brain_owned_candidate_is_rejected(self):
        p = base()
        p["candidates"][0]["brain_owned"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CANDIDATE_NOT_BRAIN_OWNED:h1")

    def test_binary_float_threshold_is_rejected_from_exact_path(self):
        p = base()
        p["adequacy_threshold"] = 0.1
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXACT_BINDING_FAILED")

    def test_candidate_domain_mismatch_fails_closed(self):
        p = base()
        del p["candidates"][0]["loss_upper_bounds"]["c2"]
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CANDIDATE_CHALLENGE_DOMAIN_MISMATCH:h1")

    def test_tie_break_is_deterministic(self):
        p = base()
        p["candidates"] = [
            candidate("z", B, p["candidates"][0]["loss_upper_bounds"]),
            candidate("a", A, p["candidates"][0]["loss_upper_bounds"]),
        ]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_candidate_id"], "a")

    def test_success_never_grants_acceptance_or_terminal_credit(self):
        out = solve(base())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["common_law_certified"])
        self.assertTrue(out["conditional_common_law_proved"])
        self.assertFalse(out["upstream_authentication_performed"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
