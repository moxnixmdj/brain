from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import one_shot_verified_closure_v1 as closure


class OneShotVerifiedClosureV1Tests(unittest.TestCase):
    def test_empty_queue_reaches_truthful_current_fixed_point(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            learning._write_state(learning._empty_state(), state_path)
            with mock.patch.object(
                closure.improvement,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_EMPTY",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                    "blockers": [],
                },
            ):
                out = closure.run(state_path=state_path, repo_root=closure.ROOT)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["internal_actionable_frontier_empty"])
            self.assertFalse(out["open_world_completion_claimed"])

    def test_missing_frontier_provider_is_internal_blocker_not_externalized(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state = learning._empty_state()
            learning._enqueue_improvement(
                state,
                kind=closure.improvement.FRONTIER_EXPANSION_KIND,
                priority=35,
                identity={"x": "y"},
                payload={"required_capability_class": "INDEPENDENT_READONLY_SUCCESS_VERIFIER_OR_ADAPTER"},
            )
            learning._write_state(state, state_path)
            with mock.patch.object(
                closure.improvement,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                    "blockers": [{
                        "work_id": "x",
                        "kind": closure.improvement.FRONTIER_EXPANSION_KIND,
                        "blocker": "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
                    }],
                },
            ):
                out = closure.run(state_path=state_path, repo_root=closure.ROOT)
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["status"],
                "OPEN__INTERNAL_ACQUISITION_OR_VERIFICATION_CAPABILITY_REQUIRED",
            )
            self.assertTrue(out["internal_blockers"])
            self.assertFalse(out["open_world_completion_claimed"])

    def test_drain_repeats_until_zero_progress(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            learning._write_state(learning._empty_state(), state_path)
            with mock.patch.object(
                closure.improvement,
                "drain",
                side_effect=[
                    {"status": "ADVANCED", "pass": True, "progress_count": 2, "actions": [], "blockers": []},
                    {"status": "STABLE", "pass": True, "progress_count": 0, "actions": [], "blockers": []},
                ],
            ) as drain:
                out = closure.run(state_path=state_path, repo_root=closure.ROOT)
            self.assertEqual(drain.call_count, 2)
            self.assertEqual(out["progress_count"], 2)
            self.assertTrue(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
