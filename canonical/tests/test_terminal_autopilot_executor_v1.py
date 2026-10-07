from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from canonical.runtime.terminal_autopilot_executor_v1 import (
    execute_wave,
    overlay_worker_progress,
    select_runnable_tasks,
)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def make_root() -> tuple[tempfile.TemporaryDirectory, Path]:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    (root / "canonical/same_identity_worker/tasks").mkdir(parents=True)
    (root / "canonical/same_identity_worker/state").mkdir(parents=True)
    (root / "canonical/same_identity_worker/evidence").mkdir(parents=True)
    return td, root


def task(
    task_id: str,
    agent_id: str,
    action_id: str,
    obligation: str,
    *,
    phase: str = "EXECUTE",
    execution_class: str = "REVERSIBLE_ZERO_REALITY",
    irreversible: bool = False,
    promotion_authority=None,
):
    x = {
        "schema": "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1",
        "task_id": task_id,
        "agent_id": agent_id,
        "incremental_spend_usd": 0,
        "mission_path": "canonical/missions/fake.json",
        "mission_sha256": "0" * 64,
        "terminal_autopilot": {
            "enabled": True,
            "phase": phase,
            "execution_class": execution_class,
            "action_id": action_id,
            "obligation_ids": [obligation],
            "irreversible_benchmark": irreversible,
        },
    }
    if promotion_authority is not None:
        x["terminal_autopilot"]["promotion_authority"] = promotion_authority
    return x


class TerminalAutopilotExecutorTests(unittest.TestCase):
    def test_irreversible_benchmark_is_never_selected(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        p = root / "canonical/same_identity_worker/tasks/t1.json"
        p.write_text(json.dumps(task(
            "t1", "A", "evidence::X", "X", irreversible=True
        )), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [{"action_id": "evidence::X", "obligation_ids": ["X"]}],
            "verify": [],
            "promote": [],
        }
        self.assertEqual(select_runnable_tasks(root, plan), [])

    def test_exact_actions_fan_out_across_distinct_workers(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        tasks = root / "canonical/same_identity_worker/tasks"
        tasks.joinpath("a.json").write_text(json.dumps(task(
            "a", "WORKER-A", "evidence::A", "A"
        )), encoding="utf-8")
        tasks.joinpath("b.json").write_text(json.dumps(task(
            "b", "WORKER-B", "evidence::B", "B"
        )), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [
                {"action_id": "evidence::A", "obligation_ids": ["A"]},
                {"action_id": "evidence::B", "obligation_ids": ["B"]},
            ],
            "verify": [],
            "promote": [],
        }
        gate = threading.Barrier(2)
        intervals = {}
        lock = threading.Lock()

        def fake_runner(**kwargs):
            task_id = Path(kwargs["task_path"]).stem
            start = time.monotonic()
            gate.wait(timeout=2)
            time.sleep(0.03)
            end = time.monotonic()
            with lock:
                intervals[task_id] = (start, end)
            return 0, {"status": "PASS", "task_id": task_id}

        out = execute_wave(root, plan, max_concurrency=2, runner=fake_runner)
        self.assertEqual(out["status"], "WAVE_COMPLETE")
        self.assertEqual(set(out["selected"]), {"a", "b"})
        self.assertEqual(len(out["results"]), 2)
        a, b = intervals["a"], intervals["b"]
        self.assertLess(max(a[0], b[0]), min(a[1], b[1]))

    def test_same_worker_identity_is_not_double_scheduled_in_wave(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        tasks = root / "canonical/same_identity_worker/tasks"
        tasks.joinpath("a.json").write_text(json.dumps(task(
            "a", "WORKER-A", "evidence::A", "A"
        )), encoding="utf-8")
        tasks.joinpath("b.json").write_text(json.dumps(task(
            "b", "WORKER-A", "evidence::B", "B"
        )), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [
                {"action_id": "evidence::A", "obligation_ids": ["A"]},
                {"action_id": "evidence::B", "obligation_ids": ["B"]},
            ],
            "verify": [],
            "promote": [],
        }
        selected = select_runnable_tasks(root, plan)
        self.assertEqual(len(selected), 1)

    def test_completed_execution_projects_only_result_present(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        tasks = root / "canonical/same_identity_worker/tasks"
        states = root / "canonical/same_identity_worker/state"
        tasks.joinpath("a.json").write_text(json.dumps(task(
            "a", "WORKER-A", "evidence::A", "A"
        )), encoding="utf-8")
        states.joinpath("a.json").write_text(
            json.dumps({"status": "COMPLETE"}), encoding="utf-8")
        manifest = {"obligations": [{"id": "A", "status": "OPEN"}]}
        out = overlay_worker_progress(manifest, root)
        self.assertEqual(out["obligations"][0]["status"], "RESULT_PRESENT")

    def test_completed_verification_projects_verified(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        tasks = root / "canonical/same_identity_worker/tasks"
        states = root / "canonical/same_identity_worker/state"
        tasks.joinpath("v.json").write_text(json.dumps(task(
            "v", "VERIFIER-A", "verify::A", "A",
            phase="VERIFY",
            execution_class="INDEPENDENT_ZERO_SPEND_VERIFY",
        )), encoding="utf-8")
        states.joinpath("v.json").write_text(
            json.dumps({"status": "COMPLETE"}), encoding="utf-8")
        manifest = {"obligations": [{"id": "A", "status": "RESULT_PRESENT"}]}
        out = overlay_worker_progress(manifest, root)
        self.assertEqual(out["obligations"][0]["status"], "VERIFIED")

    def test_promotion_requires_exact_content_bound_authority(self):
        td, root = make_root()
        self.addCleanup(td.cleanup)
        auth = root / "canonical/governance/PROMOTE_A.json"
        auth.parent.mkdir(parents=True)
        auth.write_text('{"authorized":true}\n', encoding="utf-8")
        authority = {
            "path": "canonical/governance/PROMOTE_A.json",
            "git_blob_sha": git_blob_sha(auth.read_bytes()),
        }
        tasks = root / "canonical/same_identity_worker/tasks"
        tasks.joinpath("p.json").write_text(json.dumps(task(
            "p", "PROMOTER-A", "promote::A", "A",
            phase="PROMOTE",
            execution_class="CONTENT_BOUND_PROMOTION",
            promotion_authority=authority,
        )), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [],
            "verify": [],
            "promote": [{"action_id": "promote::A", "obligation_ids": ["A"]}],
        }
        self.assertEqual(len(select_runnable_tasks(root, plan)), 1)
        auth.write_text('{"authorized":false}\n', encoding="utf-8")
        self.assertEqual(select_runnable_tasks(root, plan), [])


if __name__ == "__main__":
    unittest.main()
