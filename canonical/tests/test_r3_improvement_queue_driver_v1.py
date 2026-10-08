from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


class R3ImprovementQueueDriverTests(unittest.TestCase):
    def temp_state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def write_state(self, path: Path, queue: dict) -> None:
        state = learning._empty_state()
        state["improvement_queue"] = queue
        learning._refresh_stats(state)
        learning._write_state(state, path)

    def test_blocked_higher_priority_work_does_not_starve_actionable_repair(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "skill": {
                    "work_id": "skill",
                    "kind": "VERIFY_SKILL_CANDIDATE",
                    "priority": 10,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                },
                "repair": {
                    "work_id": "repair",
                    "kind": "REPAIR_FAILURE_CLASS",
                    "priority": 30,
                    "identity": {},
                    "payload": {"failure_fingerprint": "f", "retry_capsule_sha256": "r"},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                },
            },
        )
        repair = mock.Mock(return_value={"pass": True, "status": "REPAIRED"})
        out = driver.advance_once(state_path=path, failure_repair_provider=repair)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(out["work_id"], "repair")
        self.assertEqual(
            out["blockers_skipped"][0]["blocker"],
            "SKILL_VERIFICATION_PROVIDER_REQUIRED",
        )
        repair.assert_called_once()

    def test_delayed_episode_queue_retains_exact_verification_material(self):
        path = self.temp_state()
        episode = {
            "episode_id": "ep",
            "scope_id": "scope",
            "program_sha256": "sha256:p",
            "trace_sha256": "sha256:t",
        }
        problem = {
            "task_id": "task",
            "initial_facts": [],
            "target_effects": ["goal"],
            "capabilities": [],
        }
        out = {
            "pass": True,
            "current_episode": episode,
            "current_episode_verified": False,
            "trace": [{"capability_id": "c"}],
            "state_capsule_head_hash": "fact",
            "value_capsule_head_hash": "value",
        }
        learning.integrate_solver_output(
            out,
            state_path=path,
            verification_problem=problem,
        )
        state = learning.load_state(path)
        work = next(
            row
            for row in state["improvement_queue"].values()
            if row["kind"] == "VERIFY_EPISODE"
        )
        self.assertEqual(work["payload"]["episode"], episode)
        self.assertEqual(work["payload"]["problem"], problem)
        self.assertEqual(work["payload"]["trace"], out["trace"])
        self.assertEqual(work["payload"]["fact_capsule_head_hash"], "fact")
        self.assertEqual(work["payload"]["value_capsule_head_hash"], "value")

    def test_event_waiting_work_does_not_claim_progress(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "collect": {
                    "work_id": "collect",
                    "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
                    "priority": 40,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        out = driver.advance_once(state_path=path)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        self.assertEqual(
            out["blockers"][0]["blocker"],
            "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
        )

    def test_drain_stops_when_no_more_actionable_work_exists(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "collect": {
                    "work_id": "collect",
                    "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
                    "priority": 40,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        out = driver.drain(state_path=path, max_actions=4)
        self.assertEqual(out["progress_count"], 0)
        self.assertEqual(len(out["actions"]), 1)
        self.assertEqual(out["status"], "IMPROVEMENT_QUEUE_STABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
