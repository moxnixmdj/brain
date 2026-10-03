import unittest

from canonical.runtime.metacognitive_learning_policy_v1 import (
    MetaPolicyError,
    VerifiedEpisode,
    compare_strategies,
    compile_environment_policy,
)


class MetaTests(unittest.TestCase):
    def episodes(self):
        return [
            VerifiedEpisode("t1", "old", True, True, wall_clock=10, reality_calls=3, information_actions=5),
            VerifiedEpisode("t2", "old", True, True, wall_clock=10, reality_calls=3, information_actions=5),
            VerifiedEpisode("t1", "new", True, True, wall_clock=6, reality_calls=2, information_actions=4),
            VerifiedEpisode("t2", "new", True, True, wall_clock=7, reality_calls=2, information_actions=4),
        ]

    def test_pareto_improvement_promotes(self):
        out = compare_strategies(episodes=self.episodes(), incumbent="old", candidate="new")
        self.assertTrue(out["promotion_allowed_for_environment_class"])
        self.assertFalse(out["universal_superiority_claimed"])

    def test_success_regression_blocks(self):
        episodes = self.episodes()
        episodes[-1] = VerifiedEpisode(
            "t2", "new", True, False, wall_clock=1, reality_calls=0, information_actions=0
        )
        self.assertFalse(
            compare_strategies(
                episodes=episodes, incumbent="old", candidate="new"
            )["promotion_allowed_for_environment_class"]
        )

    def test_safety_regression_blocks(self):
        episodes = self.episodes()
        episodes[-1] = VerifiedEpisode(
            "t2", "new", True, True, safety_violation=True,
            wall_clock=1, reality_calls=0, information_actions=0,
        )
        self.assertFalse(
            compare_strategies(
                episodes=episodes, incumbent="old", candidate="new"
            )["promotion_allowed_for_environment_class"]
        )

    def test_unmatched_tasks_rejected(self):
        with self.assertRaises(MetaPolicyError):
            compare_strategies(
                episodes=self.episodes()[:-1], incumbent="old", candidate="new"
            )

    def test_unverified_episode_rejected(self):
        episodes = self.episodes()
        episodes[-1] = VerifiedEpisode("t2", "new", False, True, wall_clock=1)
        with self.assertRaises(MetaPolicyError):
            compare_strategies(
                episodes=episodes, incumbent="old", candidate="new"
            )

    def test_compile_requires_pass(self):
        comparison = compare_strategies(
            episodes=self.episodes(), incumbent="old", candidate="new"
        )
        out = compile_environment_policy(
            environment_class="unseen-api",
            comparison=comparison,
            candidate_strategy="new",
            evidence_receipts=["v1"],
        )
        self.assertEqual(out["scope"], "MATCHED_VERIFIED_EPISODE_CLASS_ONLY")
        self.assertEqual(out["fallback"], "UNIVERSAL_LEARNING_V2_DECISION_ROUTER")


if __name__ == "__main__":
    unittest.main(verbosity=2)
