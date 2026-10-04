#!/usr/bin/env python3
import unittest

from canonical.runtime.root1_causal_subtype_guard_v1 import (
    Root1CausalSubtypeError,
    classify_root1_causal_subtype,
    livebench_v6_current_projection,
)


class Root1CausalSubtypeGuardTests(unittest.TestCase):
    def test_livebench_current_projection_is_route_gap_not_underlying_capability(self):
        out = livebench_v6_current_projection()
        self.assertEqual(out["status"], "ROOT1_OPERATIVE_ROUTE_GAP_ONLY")
        self.assertEqual(out["causal_subtype"], "OPERATIVE_ROUTE_OR_COMPOSITION_GAP")
        self.assertIs(out["integration_repair_authorized"], True)
        self.assertIs(out["underlying_capability_acquisition_authorized"], False)
        self.assertEqual(out["counts"], {
            "observed_case_count": 72,
            "valid_candidate_response_count": 0,
            "policy_block_count": 43,
            "runtime_or_composition_failure_count": 29,
            "independently_adjudicated_semantic_failure_count": 0,
        })

    def test_valid_independently_adjudicated_semantic_failure_can_authorize_acquisition(self):
        out = classify_root1_causal_subtype({
            "positive_operational_gap": True,
            "operative_failure_demonstrated": True,
            "observed_case_count": 10,
            "valid_candidate_response_count": 10,
            "policy_block_count": 0,
            "runtime_or_composition_failure_count": 0,
            "independently_adjudicated_semantic_failure_count": 3,
            "underlying_behavior_exercised": True,
            "independent_semantic_acceptance": True,
            "execution_surface_verified_ready": True,
            "failure_attributed_to_underlying_behavior": True,
        })
        self.assertEqual(out["status"], "ROOT1_UNDERLYING_CAPABILITY_GAP_ESTABLISHED")
        self.assertIs(out["underlying_capability_acquisition_authorized"], True)
        self.assertIs(out["integration_repair_authorized"], False)

    def test_semantic_failure_without_causal_gates_fails_closed(self):
        out = classify_root1_causal_subtype({
            "positive_operational_gap": True,
            "operative_failure_demonstrated": True,
            "observed_case_count": 5,
            "valid_candidate_response_count": 5,
            "policy_block_count": 0,
            "runtime_or_composition_failure_count": 0,
            "independently_adjudicated_semantic_failure_count": 1,
        })
        self.assertEqual(out["status"], "ROOT1_SUBTYPE_UNPROVED_FAIL_CLOSED")
        self.assertIs(out["underlying_capability_acquisition_authorized"], False)
        self.assertIs(out["integration_repair_authorized"], False)

    def test_no_positive_operational_gap_means_no_action(self):
        out = classify_root1_causal_subtype({
            "positive_operational_gap": False,
            "operative_failure_demonstrated": True,
        })
        self.assertIs(out["root1_operational_gap"], False)
        self.assertIs(out["underlying_capability_acquisition_authorized"], False)

    def test_counts_must_be_consistent(self):
        with self.assertRaisesRegex(
            Root1CausalSubtypeError,
            "COUNTS_EXCEED_OBSERVED_CASE_COUNT",
        ):
            classify_root1_causal_subtype({
                "positive_operational_gap": True,
                "operative_failure_demonstrated": True,
                "observed_case_count": 3,
                "valid_candidate_response_count": 1,
                "policy_block_count": 2,
                "runtime_or_composition_failure_count": 1,
            })

    def test_semantic_failures_cannot_exceed_valid_responses(self):
        with self.assertRaisesRegex(
            Root1CausalSubtypeError,
            "SEMANTIC_FAILURES_EXCEED_VALID_RESPONSES",
        ):
            classify_root1_causal_subtype({
                "positive_operational_gap": True,
                "operative_failure_demonstrated": True,
                "observed_case_count": 4,
                "valid_candidate_response_count": 1,
                "policy_block_count": 3,
                "runtime_or_composition_failure_count": 0,
                "independently_adjudicated_semantic_failure_count": 2,
            })


if __name__ == "__main__":
    unittest.main()
