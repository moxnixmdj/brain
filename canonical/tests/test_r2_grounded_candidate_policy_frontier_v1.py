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
        policy_id = "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
        condition = out["policy_conditions"][policy_id]
        self.assertEqual(condition["op"], "ATOM")
        predicate_id = out["adequacy_predicate_by_policy"][policy_id]
        self.assertEqual(condition["id"], predicate_id)
        self.assertIn(predicate_id, out["decision_basis_additions"])
        self.assertTrue(
            any(
                row["formula"] == {"op": "ATOM", "id": predicate_id}
                for row in out["discriminators"]
            )
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
        selected = set(out["capability_by_policy"].values())
        self.assertTrue(
            {"auto.npm.dfinity-cbor", "auto.npm.msgpack-msgpack"}.intersection(selected),
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
