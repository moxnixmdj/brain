from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime import r2_grounded_candidate_policy_frontier_v1 as frontier


ROOT = Path(__file__).resolve().parents[2]


class R2GroundedCandidatePolicyFrontierV1Tests(unittest.TestCase):
    def test_known_owned_capability_becomes_candidate_policy_without_adequacy(self):
        out = frontier.propose(
            "Audit the Python tests with unittest and report passed failed and skipped counts.",
            repo_root=ROOT,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__VERIFIED_GROUNDING_EXPOSED_AS_UNTRUSTED_POLICY_FRONTIER",
        )
        self.assertIn(
            "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest",
            out["policy_conditions"],
        )
        self.assertEqual(
            out["policy_conditions"][
                "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
            ],
            {"op": "TRUE"},
        )
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertTrue(out["candidate_only"])

    def test_unknown_goal_stays_unresolved_instead_of_inventing_policy(self):
        out = frontier.propose(
            "Calibrate the neutrino interferometer phase drift.",
            repo_root=ROOT,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "NOT_APPLICABLE__NO_GROUNDED_BOUND_CAPABILITY",
        )
        self.assertEqual(out["candidate_policy_count"], 0)
        self.assertFalse(out["policy_adequacy_authority"])

    def test_ambiguous_grounding_preserves_all_candidates(self):
        out = frontier.propose(
            "Choose a binary serialization route for these records.",
            repo_root=ROOT,
        )
        self.assertTrue(out["pass"], out)
        self.assertGreaterEqual(out["candidate_policy_count"], 2)
        self.assertTrue(out["ambiguity_preserved"])
        self.assertEqual(
            set(out["capability_by_policy"].values()),
            set(out["grounding"]["candidate_capability_ids"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
