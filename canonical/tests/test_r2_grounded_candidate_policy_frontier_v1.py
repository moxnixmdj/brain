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
        policy_id = frontier.goal_scoped_policy_id(
            "python.tests.audit.unittest",
            "Audit the Python tests with unittest and report passed failed and skipped counts.",
        )
        self.assertIn(policy_id, out["policy_conditions"])
        self.assertEqual(out["policy_conditions"][policy_id], {"op": "TRUE"})
        self.assertEqual(out["policy_identity_scope"], "EXACT_RAW_GOAL_SHA256")
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertTrue(out["candidate_only"])

    def test_same_capability_is_distinct_policy_for_distinct_raw_goals(self):
        a = frontier.goal_scoped_policy_id("python.tests.audit.unittest", "goal a")
        b = frontier.goal_scoped_policy_id("python.tests.audit.unittest", "goal b")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith(frontier.POLICY_PREFIX + "python.tests.audit.unittest"))
        self.assertTrue(b.startswith(frontier.POLICY_PREFIX + "python.tests.audit.unittest"))

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
        selected = set(out["capability_by_policy"].values())
        self.assertTrue(
            {
                "auto.npm.dfinity-cbor",
                "auto.npm.msgpack-msgpack",
                "auto.pypi.msgpack",
                "auto.pypi.bson-modern",
            }.intersection(selected),
            selected,
        )
        self.assertNotIn("terminal.kstar.root.assess.stdlib", selected)
        self.assertNotIn("yaml.to_json.yq", selected)
        self.assertNotIn("json.query.jq", selected)
        self.assertTrue(out["policy_adequacy_authority"] is False)


    def test_execution_bindability_does_not_block_semantic_policy_discovery(self):
        out = frontier.propose(
            "Audit the Python tests with unittest and report passed failed and skipped counts.",
            repo_root=ROOT,
        )
        self.assertTrue(out["pass"], out)
        selected = set(out["capability_by_policy"].values())
        self.assertIn("python.tests.audit.unittest", selected)
        self.assertFalse(out["execution_authority"])

    def test_multi_clause_goal_is_not_collapsed_into_one_capability_policy(self):
        out = frontier.propose(
            "Choose the decision route using the available evidence and constraints, and independently verify the decision.",
            repo_root=ROOT,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "NOT_APPLICABLE__MULTI_CLAUSE_OR_EMPTY")
        self.assertEqual(out["candidate_policy_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
