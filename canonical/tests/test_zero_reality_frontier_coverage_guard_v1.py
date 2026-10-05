from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.zero_reality_frontier_coverage_guard_v1 import (
    FrontierCoverageError,
    verify_files,
    verify_frontier,
)


ROOT = Path(__file__).resolve().parents[2]


class FrontierCoverageGuardTests(unittest.TestCase):
    def test_current_v18_covers_exact_open_set(self) -> None:
        out = verify_files(
            ROOT / "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
            ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V18.json",
        )
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["open_count"], 24)
        self.assertEqual(out["covered_unique_count"], 24)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["extra"], [])

    def test_missing_open_predicate_fails_closed(self) -> None:
        root_state = {
            "current_residual_root_partition": {
                "unresolved_total": 2,
                "root1_only": [],
                "root2_only": ["A", "B"],
                "root3_only": [],
                "root2_and_root3": [],
            }
        }
        cut = {
            "current_information_positive_action_groups": [
                {"id": "g", "predicates": ["A"]}
            ],
            "dormant_wake_only": [],
        }
        out = verify_frontier(root_state, cut)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["missing"], ["B"])

    def test_extra_predicate_fails_closed(self) -> None:
        root_state = {
            "current_residual_root_partition": {
                "unresolved_total": 1,
                "root1_only": [],
                "root2_only": ["A"],
                "root3_only": [],
                "root2_and_root3": [],
            }
        }
        cut = {
            "current_information_positive_action_groups": [
                {"id": "g", "predicates": ["A", "STALE"]}
            ],
            "dormant_wake_only": [],
        }
        out = verify_frontier(root_state, cut)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["extra"], ["STALE"])

    def test_declared_root_count_mismatch_raises(self) -> None:
        root_state = {
            "current_residual_root_partition": {
                "unresolved_total": 2,
                "root1_only": [],
                "root2_only": ["A"],
                "root3_only": [],
                "root2_and_root3": [],
            }
        }
        cut = {
            "current_information_positive_action_groups": [],
            "dormant_wake_only": [],
        }
        with self.assertRaises(FrontierCoverageError):
            verify_frontier(root_state, cut)


if __name__ == "__main__":
    unittest.main()
