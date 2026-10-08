from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as live_runtime
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


class R3DirectOwnedNoDeltaV1Tests(unittest.TestCase):
    def temp_state(self) -> Path:
        return Path(tempfile.mkdtemp()) / "state.json"

    def test_new_direct_owned_success_records_telemetry_without_adapter_work(self):
        path = self.temp_state()
        out = live_runtime.observe_runtime_outcome(
            {
                "schema": "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1",
                "pass": True,
                "status": "BOUND_OK",
                "source_mode": "BOUND_CAPABILITY",
                "capability_id": "bound:example",
            },
            state_path=path,
            surface="UNIFIED_FABRIC_DIRECT_BOUND_CAPABILITY",
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "SUCCESS_OBSERVED__OWNED_DIRECT_EXECUTION__NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE",
        )
        self.assertIsNone(out["improvement_work_id"])
        self.assertFalse(out["new_improvement_work_enqueued"])
        self.assertFalse(out["frontier_expansion_required"])
        self.assertFalse(out["permanent_nonlearnability_claimed"])

        state = learning.load_state(path)
        self.assertEqual(state["improvement_queue"], {})
        self.assertEqual(len(state["observations"]), 1)
        observation = next(iter(state["observations"].values()))
        self.assertEqual(
            observation["learning_disposition"],
            "NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE_FROM_OWNED_DIRECT_SURFACE",
        )
        self.assertTrue(observation["existing_capability_authority_unchanged"])
        self.assertFalse(observation["frontier_expansion_required"])

    def test_repeated_direct_owned_success_deduplicates_without_creating_work(self):
        path = self.temp_state()
        payload = {
            "schema": "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1",
            "pass": True,
            "status": "PASS__EXACT_H100_CAPABILITY_INVOKED",
            "source_mode": "H100_INFERENCE",
        }
        first = live_runtime.observe_runtime_outcome(
            payload,
            state_path=path,
            surface="UNIFIED_FABRIC_DIRECT_H100_INFERENCE",
        )
        second = live_runtime.observe_runtime_outcome(
            payload,
            state_path=path,
            surface="UNIFIED_FABRIC_DIRECT_H100_INFERENCE",
        )
        self.assertEqual(first["observation_id"], second["observation_id"])
        state = learning.load_state(path)
        self.assertEqual(state["improvement_queue"], {})
        observation = state["observations"][first["observation_id"]]
        self.assertEqual(observation["count"], 2)

    def test_legacy_direct_success_resolves_before_same_evidence_backoff(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1",
                "pass": True,
                "status": "BOUND_OK",
                "source_mode": "BOUND_CAPABILITY",
            },
            surface="UNIFIED_FABRIC_DIRECT_BOUND_CAPABILITY",
            state_path=path,
        )
        work_id = observed["improvement_work_id"]
        learning._record_improvement_attempt(
            work_id,
            status="IMPROVEMENT_ACTION_EXCEPTION",
            reason="legacy proofless direct success",
            state_path=path,
        )

        before = learning.load_state(path)
        self.assertEqual(
            before["improvement_queue"][work_id]["last_attempt_observations"],
            before["improvement_queue"][work_id]["observations"],
        )

        advanced = driver.advance_once(state_path=path)
        self.assertTrue(advanced["pass"], advanced)
        self.assertFalse(advanced["progress"], advanced)
        self.assertTrue(advanced["disposition_recorded"], advanced)
        self.assertEqual(
            advanced["status"],
            "IMPROVEMENT_RESOLVED__LEGACY_DIRECT_OWNED_SUCCESS__NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE",
        )

        state = learning.load_state(path)
        self.assertEqual(state["improvement_queue"][work_id]["status"], "RESOLVED")
        self.assertTrue(
            state["improvement_queue"][work_id]["resolved_without_promotion"]
        )
        observation = state["observations"][observed["observation_id"]]
        self.assertTrue(observation["legacy_adapter_debt_retired"])
        self.assertFalse(observation["frontier_expansion_required"])
        frontier_work = [
            row
            for row in state["improvement_queue"].values()
            if row.get("kind") == driver.FRONTIER_EXPANSION_KIND
        ]
        self.assertEqual(frontier_work, [])

    def test_replayable_direct_success_is_not_misclassified_as_legacy_no_delta(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1",
                "pass": True,
                "status": "PASS__DIRECT_WITH_REPLAY",
                "source_mode": "BOUND_CAPABILITY",
            },
            surface="UNIFIED_FABRIC_DIRECT_BOUND_CAPABILITY",
            state_path=path,
            replay_context={"mode": "generic", "problem": {"task_id": "x"}},
        )
        state = learning.load_state(path)
        work = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertIsNone(
            driver._resolve_legacy_direct_owned_success_no_delta(
                work,
                state_path=path,
            )
        )
        state = learning.load_state(path)
        self.assertEqual(
            state["improvement_queue"][observed["improvement_work_id"]]["status"],
            "PENDING",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
