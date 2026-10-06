import unittest

from canonical.runtime.distributional_target_upper_envelope_v1 import (
    support,
    weakly_dominates,
    target_upper_envelope_covered,
)


SUCCESS = {"failure": 0.0, "success": 1.0}
SAFE = {"unsafe": 0.0, "safe": 1.0}
QUALITY_A = {"a": 1.0, "b": 0.0}
QUALITY_B = {"a": 0.0, "b": 1.0}


class DistributionalTargetUpperEnvelopeTests(unittest.TestCase):
    def test_equal_support_does_not_hide_reliability_gap(self):
        opus = {"failure": 0.01, "success": 0.99}
        brain = {"failure": 0.49, "success": 0.51}
        self.assertEqual(support(opus), support(brain))
        self.assertFalse(weakly_dominates(brain, opus, evaluators=[SUCCESS]))

    def test_perfect_brain_distribution_dominates_target(self):
        opus = {"failure": 0.01, "success": 0.99}
        brain = {"success": 1.0}
        self.assertTrue(weakly_dominates(brain, opus, evaluators=[SUCCESS]))

    def test_incomparable_tradeoff_is_not_collapsed(self):
        target_b = {"b": 1.0}
        brain_a = {"a": 1.0}
        self.assertFalse(
            weakly_dominates(
                brain_a,
                target_b,
                evaluators=[QUALITY_A, QUALITY_B],
            )
        )

    def test_hard_constraint_nonregression_is_load_bearing(self):
        target = {"safe": 1.0}
        brain = {"safe": 0.8, "unsafe": 0.2}
        self.assertFalse(
            weakly_dominates(
                brain,
                target,
                evaluators=[SAFE],
                hard_constraints=[{"evaluator": SAFE, "threshold": 0.95}],
            )
        )

    def test_unowned_candidate_cannot_cover_target(self):
        target = {"success": 1.0}
        candidates = [{"brain_owned": False, "law": {"success": 1.0}}]
        self.assertFalse(
            target_upper_envelope_covered(
                candidates,
                [target],
                evaluators=[SUCCESS],
            )
        )

    def test_every_target_law_requires_owned_cover(self):
        targets = [
            {"failure": 0.01, "success": 0.99},
            {"success": 1.0},
        ]
        candidates = [
            {"brain_owned": True, "law": {"success": 1.0}},
        ]
        self.assertTrue(
            target_upper_envelope_covered(
                candidates,
                targets,
                evaluators=[SUCCESS],
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
