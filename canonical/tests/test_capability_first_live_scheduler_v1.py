from __future__ import annotations

import unittest

from canonical.runtime import capability_first_live_scheduler_v1 as live


def row(work_id: str, calibration_id: str = "CAL-V1"):
    evidence = {field: "canonical/test-evidence/" + field for field in live.LIVE_SCORE_FIELDS}
    return {
        "work_id": work_id,
        "work_type": "RELIABILITY_IMPROVEMENT",
        "expected_capability_gain_lcb": 2,
        "expected_efficiency_gain_lcb": 1,
        "expected_reliability_gain_lcb": 3,
        "reuse_breadth_lcb": 4,
        "generalization_lcb": 4,
        "success_probability_lcb": "3/4",
        "wall_clock_cost_ub": 2,
        "compute_cost_ub": 1,
        "memory_cost_ub": 1,
        "complexity_cost_ub": 1,
        "live_score_contract": {
            "scale": live.LIVE_SCORE_CONTRACT_SCALE,
            "dimensionless_normalized": True,
            "calibration_id": calibration_id,
            "frontier_id": "FRONTIER-V1",
            "frontier_complete": True,
            "calibration_evidence_ref": "canonical/governance/LIVE_WORK_SCORE_CALIBRATION_20261010_V1.json",
            "frontier_completeness_evidence_ref": "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json",
            "independent_verification_ref": "canonical/verification/LIVE_WORK_SCORE_CONTRACT_VERIFY_20261010_V1.json",
            "metric_evidence": evidence,
        },
    }


class CapabilityFirstLiveSchedulerV1Tests(unittest.TestCase):
    def test_missing_contract_fails_closed(self):
        bad = row("A")
        del bad["live_score_contract"]
        with self.assertRaisesRegex(
            live.LiveSchedulerContractError,
            "LIVE_SCORE_CONTRACT_REQUIRED:A",
        ):
            live.validate_live_score_contract([bad])

    def test_missing_metric_evidence_fails_closed(self):
        bad = row("A")
        del bad["live_score_contract"]["metric_evidence"]["memory_cost_ub"]
        with self.assertRaisesRegex(
            live.LiveSchedulerContractError,
            "LIVE_SCORE_METRIC_EVIDENCE_MISSING:A:memory_cost_ub",
        ):
            live.validate_live_score_contract([bad])

    def test_mixed_calibrations_fail_closed(self):
        with self.assertRaisesRegex(
            live.LiveSchedulerContractError,
            "LIVE_SCORE_CALIBRATION_MISMATCH",
        ):
            live.validate_live_score_contract([row("A", "CAL-A"), row("B", "CAL-B")])

    def test_raw_heterogeneous_scale_fails_closed(self):
        bad = row("A")
        bad["live_score_contract"]["scale"] = "SECONDS_PLUS_BYTES_PLUS_VIBES"
        with self.assertRaisesRegex(
            live.LiveSchedulerContractError,
            "LIVE_SCORE_CONTRACT_SCALE_INVALID:A",
        ):
            live.validate_live_score_contract([bad])

    def test_complete_common_contract_is_accepted(self):
        out = live.validate_live_score_contract([row("A"), row("B")])
        self.assertEqual(out["calibration_id"], "CAL-V1")
        self.assertEqual(out["frontier_id"], "FRONTIER-V1")
        self.assertEqual(out["scale"], live.LIVE_SCORE_CONTRACT_SCALE)

    def test_live_ranking_delegates_only_after_contract_gate(self):
        out = live.rank_live_work([row("A"), row("B")])
        self.assertTrue(out["live_score_contract_verified"])
        self.assertEqual(
            out["live_ranking_semantics"],
            "ONLY_COMMON_DIMENSIONLESS_EVIDENCE_BOUND_COMPLETE_FRONTIER_SCORES_RANK",
        )
        self.assertEqual(len(out["ranked"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
