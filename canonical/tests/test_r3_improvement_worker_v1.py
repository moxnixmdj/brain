from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3
from canonical.runtime import r3_improvement_worker_v1 as worker


class R3ImprovementWorkerV1Tests(unittest.TestCase):
    def temp_state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def test_deferred_episode_is_captured_then_verified_without_task_replay(self):
        path = self.temp_state()
        episode = {
            "episode_id": "ep-deferred",
            "scope_id": "scope-a",
            "program_sha256": "a" * 64,
            "trace_sha256": "b" * 64,
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
        }
        solver_output = {
            "pass": True,
            "status": "SOLVED__EPISODE_AWAITS_VERIFICATION",
            "current_episode": episode,
            "current_episode_verified": False,
            "trace": [{"index": 0, "status": "PASS"}],
            "state_capsule_head_hash": "c" * 64,
            "value_capsule_head_hash": "d" * 64,
        }
        learning = r3.integrate_solver_output(
            solver_output,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "p"}},
        )
        self.assertEqual(learning["status"], "EPISODE_AWAITS_INDEPENDENT_VERIFICATION")

        captured = worker.capture_pending_episode_evidence(
            solver_output,
            problem={
                "task_id": "p",
                "initial_facts": [],
                "target_effects": ["goal"],
                "capabilities": [],
            },
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "p"}},
        )
        self.assertTrue(captured["pass"], captured)
        self.assertEqual(captured["status"], "DEFERRED_EPISODE_EVIDENCE_PERSISTED")

        authenticated = {
            **episode,
            "verification_receipt": {
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
            },
            "verification_binding": {
                "receipt": {"path": "receipt.json", "git_blob_sha": "1" * 40},
                "verification": {"path": "verification.json", "git_blob_sha": "2" * 40},
            },
        }
        provider = mock.Mock(return_value={"binding": "content-addressed"})
        with mock.patch.object(
            worker.r3,
            "authenticate_episode_verification",
            return_value={"pass": True, "authenticated_episode": authenticated},
        ):
            advanced = worker.advance_improvement_queue(
                state_path=path,
                episode_verification_provider=provider,
            )

        self.assertEqual(advanced["completed_count"], 1, advanced)
        state = r3.load_state(path)
        self.assertEqual(state["stats"]["verified_episode_count"], 1)
        verify_rows = [
            row for row in state["improvement_queue"].values()
            if row.get("kind") == "VERIFY_EPISODE"
        ]
        self.assertTrue(verify_rows)
        self.assertTrue(all(row.get("status") == "RESOLVED" for row in verify_rows))
        self.assertFalse(state.get("improvement_evidence"))

    def test_deferred_skill_candidate_is_verified_and_pareto_admitted(self):
        path = self.temp_state()
        candidate = {
            "candidate_sha256": "sha256:" + "e" * 64,
            "source_episode_ids": ["ep-1", "ep-2"],
            "source_scopes": ["scope-a"],
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "scope_relation": "EXACT",
        }
        state = r3.load_state(path)
        wid = r3._enqueue_improvement(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            priority=10,
            identity={"candidate_sha256": candidate["candidate_sha256"]},
            payload={
                "candidate_sha256": candidate["candidate_sha256"],
                "source_episode_ids": candidate["source_episode_ids"],
                "source_scopes": candidate["source_scopes"],
                "postconditions": candidate["postconditions"],
                "candidate": candidate,
            },
        )
        r3._refresh_stats(state)
        r3._write_state(state, path)

        verified_skill = {
            **candidate,
            "verified_skill": True,
            "reuse_authorized": True,
        }
        provider = mock.Mock(return_value={"binding": "content-addressed"})
        with mock.patch.object(
            worker.r3,
            "authenticate_skill_verification",
            return_value={"pass": True, "verified_skill": verified_skill},
        ):
            advanced = worker.advance_improvement_queue(
                state_path=path,
                skill_verification_provider=provider,
            )

        self.assertEqual(advanced["completed_count"], 1, advanced)
        state = r3.load_state(path)
        self.assertEqual(state["stats"]["verified_skill_count"], 1)
        self.assertEqual(state["stats"]["active_skill_count"], 1)
        self.assertEqual(state["improvement_queue"][wid]["status"], "RESOLVED")
        self.assertTrue(advanced["results"][0]["permanent_reuse_authorized"])

    def test_no_provider_never_self_certifies_pending_work(self):
        path = self.temp_state()
        state = r3.load_state(path)
        r3._enqueue_improvement(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            priority=10,
            identity={"candidate_sha256": "sha256:" + "f" * 64},
            payload={
                "candidate_sha256": "sha256:" + "f" * 64,
                "candidate": {
                    "candidate_sha256": "sha256:" + "f" * 64,
                    "source_episode_ids": ["ep"],
                    "source_scopes": ["scope"],
                    "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
                    "postconditions": ["goal"],
                    "scope_relation": "EXACT",
                },
            },
        )
        r3._refresh_stats(state)
        r3._write_state(state, path)

        advanced = worker.advance_improvement_queue(state_path=path)
        self.assertEqual(advanced["completed_count"], 0)
        self.assertIn(
            "VERIFY_SKILL_CANDIDATE",
            advanced["pending_nonactionable_or_unprovided_kinds"],
        )
        state = r3.load_state(path)
        self.assertEqual(state["stats"]["verified_skill_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
