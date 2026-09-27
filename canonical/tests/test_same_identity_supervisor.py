#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "same_identity_supervisor.py"
spec = importlib.util.spec_from_file_location("same_identity_supervisor_test_target", RUNTIME_PATH)
supervisor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = supervisor
spec.loader.exec_module(supervisor)


class SameIdentitySupervisorTests(unittest.TestCase):
    AGENT = "SUPERWORKER-UNIFIED-1"

    def make_root(self):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        (root/"canonical"/"runtime").mkdir(parents=True)
        (root/"canonical"/"same_identity_worker"/"tasks").mkdir(parents=True)
        (root/"canonical"/"same_identity_worker"/"state").mkdir(parents=True)
        (root/"canonical"/"same_identity_worker"/"evidence").mkdir(parents=True)
        (root/"canonical"/"astra_runtime"/"missions").mkdir(parents=True)
        mission = root/"canonical"/"astra_runtime"/"missions"/"REAL.json"
        mission.write_text('{"mission_id":"REAL","steps":[]}\n', encoding="utf-8")
        return td, root, mission

    def write_task(self, root, mission, task_id="TASK-1", priority=50, **extra):
        task = {
            "schema": supervisor.TASK_SCHEMA,
            "task_id": task_id,
            "agent_id": self.AGENT,
            "mission_path": "canonical/astra_runtime/missions/REAL.json",
            "mission_sha256": supervisor._sha_file(mission),
            "priority": priority,
            "prerequisites": [],
            "incremental_spend_usd": 0,
            **extra,
        }
        path = root/"canonical"/"same_identity_worker"/"tasks"/f"{task_id}.json"
        path.write_text(json.dumps(task, sort_keys=True), encoding="utf-8")
        return path, task

    def dirs(self, root):
        return (
            root/"canonical"/"same_identity_worker"/"tasks",
            root/"canonical"/"same_identity_worker"/"state",
            root/"canonical"/"same_identity_worker"/"evidence",
        )

    def test_chooses_highest_priority_causally_ready_task(self):
        td, root, mission = self.make_root()
        try:
            self.write_task(root, mission, "LOW", priority=1)
            self.write_task(root, mission, "HIGH", priority=100)
            tasks, state, _ = self.dirs(root)
            selected = supervisor.choose_causally_ready_task(root, tasks, state, self.AGENT)
            self.assertEqual(selected.name, "HIGH.json")
        finally:
            td.cleanup()

    def test_unsatisfied_prerequisite_is_not_causally_ready(self):
        td, root, mission = self.make_root()
        try:
            self.write_task(
                root, mission, "BLOCKED", priority=100,
                prerequisites=["canonical/evidence/missing.json"],
            )
            self.write_task(root, mission, "READY", priority=1)
            tasks, state, _ = self.dirs(root)
            selected = supervisor.choose_causally_ready_task(root, tasks, state, self.AGENT)
            self.assertEqual(selected.name, "READY.json")
        finally:
            td.cleanup()

    def test_claim_binds_owner_lease_task_hash_and_no_promotion(self):
        td, root, mission = self.make_root()
        try:
            path, task = self.write_task(root, mission)
            _, state, _ = self.dirs(root)
            observed_task, observed_state = supervisor.claim_task(root, path, state, self.AGENT)
            self.assertEqual(observed_task["task_id"], task["task_id"])
            self.assertEqual(observed_state["lease"]["owner"], self.AGENT)
            self.assertTrue(observed_state["lease"]["lease_id"])
            self.assertEqual(observed_state["task_sha256"], supervisor._task_sha(observed_task))
            self.assertFalse(observed_state["promotion_claim"])
            self.assertEqual(observed_state["p_real_claim"], 0)
        finally:
            td.cleanup()

    def test_manifest_drift_fails_closed(self):
        td, root, mission = self.make_root()
        try:
            path, _ = self.write_task(root, mission)
            _, state, _ = self.dirs(root)
            supervisor.claim_task(root, path, state, self.AGENT)
            mutated = json.loads(path.read_text())
            mutated["priority"] = 999
            path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaisesRegex(supervisor.SupervisorError, "TASK_MANIFEST_DRIFT"):
                supervisor.claim_task(root, path, state, self.AGENT)
        finally:
            td.cleanup()

    def test_nonzero_spend_task_is_rejected(self):
        td, root, mission = self.make_root()
        try:
            path, _ = self.write_task(root, mission, incremental_spend_usd=0.01)
            _, state, _ = self.dirs(root)
            with self.assertRaisesRegex(supervisor.SupervisorError, "NONZERO_INCREMENTAL_SPEND"):
                supervisor.claim_task(root, path, state, self.AGENT)
        finally:
            td.cleanup()

    def test_checkpoint_then_fresh_resume_preserves_same_identity(self):
        td, root, mission = self.make_root()
        try:
            path, _ = self.write_task(root, mission, checkpoint_before_runtime_once=True)
            tasks, state, evidence = self.dirs(root)
            code1, receipt1 = supervisor.run_once(
                root, tasks, state, evidence, self.AGENT, path,
                executor=lambda *_: (_ for _ in ()).throw(AssertionError("runtime should not execute before checkpoint")),
            )
            self.assertEqual(code1, 75)
            self.assertEqual(receipt1["status"], "CHECKPOINTED_RELAUNCH_REQUIRED")

            seen = {}
            def fake_executor(argv, cwd, env):
                seen["argv"] = argv
                seen["cwd"] = cwd
                seen["agent"] = env.get("PROJECT_BRAIN_AGENT_ID")
                seen["task"] = env.get("PROJECT_BRAIN_TASK_ID")
                seen["bridge"] = env.get("PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR")
                return supervisor.RuntimeResult(0, "runtime ok\n", "")

            code2, receipt2 = supervisor.run_once(
                root, tasks, state, evidence, self.AGENT, path, executor=fake_executor,
            )
            self.assertEqual(code2, 0)
            self.assertEqual(receipt2["terminal_state"], "COMPLETE")
            self.assertTrue(receipt2["same_identity_bound"])
            self.assertEqual(receipt2["checkpoint_count"], 1)
            self.assertEqual(seen["agent"], self.AGENT)
            self.assertEqual(seen["task"], "TASK-1")
            self.assertEqual(
                pathlib.Path(seen["bridge"]),
                root/"canonical"/"same_identity_worker"/"external_tool_bridge"/"TASK-1",
            )
            self.assertTrue(pathlib.Path(seen["bridge"]).is_dir())
            persisted = json.loads((state/"TASK-1.json").read_text())
            self.assertEqual(persisted["agent_id"], self.AGENT)
            self.assertEqual(persisted["status"], "COMPLETE")
            self.assertEqual(persisted["runtime_attempt_count"], 1)
        finally:
            td.cleanup()

    def test_wrong_agent_cannot_resume_claim(self):
        td, root, mission = self.make_root()
        try:
            path, _ = self.write_task(root, mission)
            _, state, _ = self.dirs(root)
            supervisor.claim_task(root, path, state, self.AGENT)
            task = json.loads(path.read_text())
            task["agent_id"] = "OTHER"
            path.write_text(json.dumps(task), encoding="utf-8")
            with self.assertRaises(supervisor.SupervisorError):
                supervisor.claim_task(root, path, state, "OTHER")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
