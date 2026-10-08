from __future__ import annotations

import unittest

from canonical.runtime import r2_total_control_action_v1 as total


class R2TotalControlActionV1Tests(unittest.TestCase):
    def test_verified_goal_is_the_only_verified_domain_action(self):
        out = total.compile_next_action({
            "pass": True,
            "status": "PASS__GOAL_VERIFIED",
            "actual_goal_satisfaction_verified": True,
            "action": {"kind": "DO_X"},
        })
        self.assertEqual(out["kind"], "VERIFIED_DOMAIN_ACTION")
        self.assertTrue(out["classification_complete"])
        self.assertTrue(out["domain_goal_satisfaction_verified"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_pass_without_acceptance_does_not_become_success(self):
        out = total.compile_next_action({
            "pass": True,
            "status": "PASS__EXECUTION_ONLY",
            "actual_goal_satisfaction_verified": False,
        })
        self.assertEqual(out["kind"], "ACQUIRE_GOAL_SATISFACTION_PROOF")
        self.assertFalse(out["domain_goal_satisfaction_verified"])

    def test_information_request_is_preserved_exactly(self):
        req = {"predicate_id": "p", "source": "s"}
        out = total.compile_next_action({
            "pass": False,
            "status": "OPEN__INFO",
            "next_required_edge": "SOURCE_TRUTH_REQUIRED",
            "next_information_request": req,
        })
        self.assertEqual(out["kind"], "ACQUIRE_DECISION_RELEVANT_INFORMATION")
        self.assertEqual(out["request"], req)

    def test_policy_request_is_not_laundered_into_adequacy(self):
        req = {"required_artifact": "POSITIVE_POLICY_ADEQUACY_CERTIFICATE"}
        out = total.compile_next_action({
            "pass": False,
            "status": "OPEN__POLICY",
            "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
            "next_policy_request": req,
        })
        self.assertEqual(out["kind"], "ACQUIRE_OR_PROVE_POLICY_ADEQUACY")
        self.assertEqual(out["request"], req)
        self.assertFalse(out["policy_adequacy_authority"])

    def test_semantic_execution_acceptance_and_capability_edges_are_typed(self):
        cases = {
            "GOAL_TO_DECISION_SEMANTIC_BINDING": "ACQUIRE_GOAL_SEMANTIC_BINDING",
            "SELECTED_POLICY_TO_EXECUTION_BINDING": "ACQUIRE_POLICY_TO_EXECUTION_BINDING",
            "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION": "ACQUIRE_GOAL_SATISFACTION_PROOF",
            "NEW_VERIFIABLE_CAPABILITY_PRIMITIVE": "ACQUIRE_VERIFIABLE_CAPABILITY",
        }
        for edge, kind in cases.items():
            with self.subTest(edge=edge):
                out = total.compile_next_action({
                    "pass": False,
                    "status": "OPEN",
                    "next_required_edge": edge,
                })
                self.assertEqual(out["kind"], kind)
                self.assertTrue(out["classification_complete"])

    def test_unknown_declared_edge_remains_explicit(self):
        out = total.compile_next_action({
            "pass": False,
            "status": "OPEN",
            "next_required_edge": "SOMETHING_NEW",
        })
        self.assertEqual(out["kind"], "RESOLVE_DECLARED_R2_EDGE")
        self.assertEqual(out["request"]["required_edge"], "SOMETHING_NEW")

    def test_open_without_edge_stops_fail_closed(self):
        out = total.compile_next_action({"pass": False, "status": "OPEN"})
        self.assertEqual(out["kind"], "STOP_FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "OPEN_R2_RESULT_WITHOUT_ACTIONABLE_NEXT_EDGE",
        )

    def test_malformed_result_is_totalized_to_stop(self):
        out = total.compile_next_action(None)
        self.assertEqual(out["kind"], "STOP_FAIL_CLOSED")
        self.assertTrue(out["classification_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
