from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

fake_learning = types.ModuleType(
    "canonical.runtime.autonomous_verified_self_improvement_v1"
)
fake_learning.DEFAULT_STATE_PATH = Path("state.json")
fake_learning.load_state = lambda path: {"improvement_queue": {}, "stats": {}}
sys.modules[
    "canonical.runtime.autonomous_verified_self_improvement_v1"
] = fake_learning

fake_r3 = types.ModuleType("canonical.runtime.r3_improvement_queue_driver_v1")
fake_r3.drain = lambda **kwargs: {
    "status": "IMPROVEMENT_QUEUE_STABLE",
    "pass": True,
    "progress_count": 0,
    "actions": [],
}
sys.modules["canonical.runtime.r3_improvement_queue_driver_v1"] = fake_r3

from canonical.runtime import one_shot_verified_closure_v1 as closure


class OneShotClosureTests(unittest.TestCase):
    def _snap(self, digest, pending):
        return {
            "schema": closure.SCHEMA,
            "digest": digest,
            "payload": {"files": [], "pending": pending, "stats": {}},
        }

    def test_empty_queue_is_verified_internal_fixed_point(self):
        snaps = [
            self._snap("a", []),
            self._snap("a", []),
            self._snap("a", []),
        ]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertTrue(out["pass"])
        self.assertTrue(out["fixed_point"])
        self.assertEqual(
            out["status"],
            "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
        )

    def test_internal_root1_gap_remains_open(self):
        pending = [{"work_id": "w1", "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w1",
            "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER",
            "blocker": (
                "ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP__"
                "NO_BOUND_ACQUISITION_ROUTE"
            ),
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{
                    "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
                    "blockers": [blocker],
                }],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertTrue(out["fixed_point"])
        self.assertEqual(out["status"], "OPEN__INTERNAL_SOLVABLE_GAP_REMAINS")
        self.assertTrue(out["residual"]["internally_solvable_gap_remaining"])

    def test_external_evidence_only_fixed_point_passes(self):
        pending = [{"work_id": "w2", "kind": "COLLECT_MATCHING_VERIFIED_EPISODE"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w2",
            "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
            "blocker": "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{
                    "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
                    "blockers": [blocker],
                }],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"],
            "VERIFIED_FIXED_POINT__EXTERNAL_OR_NEW_EVIDENCE_REQUIRED",
        )

    def test_rejects_false_progress(self):
        pending = [{"work_id": "w3", "kind": "VERIFY_EPISODE"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_ADVANCED",
                "pass": True,
                "progress_count": 1,
                "actions": [{"pass": True, "progress": True}],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__CLAIMED_PROGRESS_WITHOUT_STATE_OR_FRONTIER_CHANGE",
        )


if __name__ == "__main__":
    unittest.main()
