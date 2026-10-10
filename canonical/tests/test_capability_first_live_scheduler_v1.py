from __future__ import annotations

import json
from pathlib import Path
import tempfile
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

    def _frontier_fixture(self, root: Path, *, authorized=True, include_b=True):
        source = root / "source.json"
        source.write_text('{"ok": true}\n', encoding="utf-8")
        ids = ["A", "B"] if include_b else ["A"]
        frontier = {
            "frontier_id": "FRONTIER-V1",
            "scope": {
                "source_set": [
                    {
                        "path": "source.json",
                        "git_blob_sha": live._git_blob_sha(source),
                    }
                ]
            },
            "candidates": [
                {"work_id": work_id, "score_state": "UNBOUND"} for work_id in ids
            ],
            "live_selection": {"authorized": authorized},
        }
        frontier_path = root / "frontier.json"
        frontier_path.write_text(json.dumps(frontier), encoding="utf-8")
        return source, frontier_path

    def test_current_frontier_accepts_exact_current_candidate_set(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, frontier_path = self._frontier_fixture(root)
            previous_root = live.ROOT
            try:
                live.ROOT = root
                contract = live.validate_live_score_contract([row("A"), row("B")])
                out = live.validate_current_frontier(
                    [row("A"), row("B")],
                    contract,
                    frontier_path=frontier_path,
                )
            finally:
                live.ROOT = previous_root
            self.assertTrue(out["currentness_verified"])
            self.assertEqual(out["eligible_candidate_count"], 2)

    def test_current_frontier_rejects_stale_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, frontier_path = self._frontier_fixture(root)
            source.write_text('{"changed": true}\n', encoding="utf-8")
            previous_root = live.ROOT
            try:
                live.ROOT = root
                contract = live.validate_live_score_contract([row("A"), row("B")])
                with self.assertRaisesRegex(
                    live.LiveSchedulerContractError,
                    "LIVE_WORK_FRONTIER_STALE:source.json",
                ):
                    live.validate_current_frontier(
                        [row("A"), row("B")],
                        contract,
                        frontier_path=frontier_path,
                    )
            finally:
                live.ROOT = previous_root

    def test_current_frontier_rejects_incomplete_candidate_set(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, frontier_path = self._frontier_fixture(root)
            previous_root = live.ROOT
            try:
                live.ROOT = root
                contract = live.validate_live_score_contract([row("A")])
                with self.assertRaisesRegex(
                    live.LiveSchedulerContractError,
                    "LIVE_WORK_FRONTIER_CANDIDATE_SET_MISMATCH",
                ):
                    live.validate_current_frontier(
                        [row("A")],
                        contract,
                        frontier_path=frontier_path,
                    )
            finally:
                live.ROOT = previous_root

    def test_current_frontier_rejects_unauthorized_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, frontier_path = self._frontier_fixture(root, authorized=False)
            previous_root = live.ROOT
            try:
                live.ROOT = root
                contract = live.validate_live_score_contract([row("A"), row("B")])
                with self.assertRaisesRegex(
                    live.LiveSchedulerContractError,
                    "LIVE_WORK_FRONTIER_SELECTION_NOT_AUTHORIZED",
                ):
                    live.validate_current_frontier(
                        [row("A"), row("B")],
                        contract,
                        frontier_path=frontier_path,
                    )
            finally:
                live.ROOT = previous_root


if __name__ == "__main__":
    unittest.main(verbosity=2)
