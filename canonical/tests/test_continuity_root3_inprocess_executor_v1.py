from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from unittest import mock

import pytest

from canonical.runtime import continuity_root3_inprocess_executor_v1 as adapter
from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor

AGENT = "SUPERWORKER-UNIFIED-1"

def _fixture():
    td = tempfile.TemporaryDirectory()
    root = pathlib.Path(td.name)
    mission = root / "canonical/astra_runtime/missions/M.json"
    task_path = root / "canonical/same_identity_worker/tasks/T.json"
    state = root / "canonical/same_identity_worker/state"
    evidence = root / "canonical/same_identity_worker/evidence"
    mission.parent.mkdir(parents=True)
    task_path.parent.mkdir(parents=True)
    state.mkdir(parents=True)
    evidence.mkdir(parents=True)
    mission.write_text('{"mission_id":"M","steps":[]}\n', encoding="utf-8")
    task = {
        "schema": supervisor.TASK_SCHEMA,
        "task_id": "T",
        "agent_id": AGENT,
        "mission_path": "canonical/astra_runtime/missions/M.json",
        "mission_sha256": supervisor._sha_file(mission),
        "priority": 100,
        "prerequisites": [],
        "incremental_spend_usd": 0,
        "checkpoint_before_runtime_once": True,
    }
    task_path.write_text(json.dumps(task, sort_keys=True), encoding="utf-8")
    return td, root, task_path, state, evidence

def test_rejects_any_requested_runtime_other_than_bound_astra():
    with pytest.raises(adapter.ContinuityRoot3Error, match="REQUESTED_RUNTIME_NOT_BOUND_ASTRA"):
        adapter.execute(
            [sys.executable, "canonical/runtime/other.py", "canonical/m.json"],
            pathlib.Path.cwd(),
            {"PROJECT_BRAIN_AGENT_ID":"A","PROJECT_BRAIN_TASK_ID":"T"},
        )

def test_inprocess_adapter_preserves_bound_identity_cwd_and_restores_process_state(tmp_path):
    old_cwd = pathlib.Path.cwd()
    old_env = dict(os.environ)
    seen = {}
    def fake_main(argv):
        seen["argv"] = list(argv)
        seen["cwd"] = pathlib.Path.cwd()
        seen["agent"] = os.environ.get("PROJECT_BRAIN_AGENT_ID")
        seen["task"] = os.environ.get("PROJECT_BRAIN_TASK_ID")
        print("root3-ok")
        return 0
    env = dict(old_env)
    env["PROJECT_BRAIN_AGENT_ID"] = "A"
    env["PROJECT_BRAIN_TASK_ID"] = "T"
    with mock.patch.object(adapter.root3_launcher, "main", side_effect=fake_main):
        result = adapter.execute(
            [sys.executable, adapter.EXPECTED_REQUESTED_RUNTIME, "canonical/m.json"],
            tmp_path,
            env,
        )
    assert result.returncode == 0
    assert "root3-ok" in result.stdout
    assert seen == {
        "argv":["canonical/m.json"],
        "cwd":tmp_path,
        "agent":"A",
        "task":"T",
    }
    assert pathlib.Path.cwd() == old_cwd
    assert dict(os.environ) == old_env

def test_checkpoint_resume_semantics_survive_root3_composition_without_raw_child_spawn():
    td, root, task_path, state, evidence = _fixture()
    try:
        code1, receipt1 = supervisor.run_once(
            root=root,
            tasks_dir=task_path.parent,
            state_dir=state,
            evidence_dir=evidence,
            agent_id=AGENT,
            task_path=task_path,
            executor=lambda *_: (_ for _ in ()).throw(
                AssertionError("runtime must not run before checkpoint")
            ),
        )
        assert code1 == 75
        assert receipt1["status"] == "CHECKPOINTED_RELAUNCH_REQUIRED"

        seen = {}
        def fake_root3_main(argv):
            seen["argv"] = list(argv)
            seen["agent"] = os.environ.get("PROJECT_BRAIN_AGENT_ID")
            seen["task"] = os.environ.get("PROJECT_BRAIN_TASK_ID")
            return 0

        with (
            mock.patch.object(adapter.root3_launcher, "main", side_effect=fake_root3_main) as launch,
            mock.patch.object(
                supervisor.subprocess,
                "run",
                side_effect=AssertionError("raw child subprocess path must not execute"),
            ),
        ):
            code2, receipt2 = adapter.run_once(
                root=root,
                tasks_dir=task_path.parent,
                state_dir=state,
                evidence_dir=evidence,
                agent_id=AGENT,
                task_path=task_path,
            )

        assert code2 == 0
        assert receipt2["terminal_state"] == "COMPLETE"
        assert receipt2["same_identity_bound"] is True
        assert receipt2["checkpoint_count"] == 1
        assert receipt2["runtime_attempt_count"] == 1
        assert seen == {
            "argv":["canonical/astra_runtime/missions/M.json"],
            "agent":AGENT,
            "task":"T",
        }
        launch.assert_called_once()
        persisted = json.loads((state / "T.json").read_text())
        assert persisted["status"] == "COMPLETE"
        assert persisted["agent_id"] == AGENT
        assert persisted["checkpoint_count"] == 1
        assert persisted["runtime_attempt_count"] == 1
    finally:
        td.cleanup()

def test_identity_environment_is_required():
    with pytest.raises(adapter.ContinuityRoot3Error, match="CONTINUITY_IDENTITY_ENV_MISSING"):
        adapter.execute(
            [sys.executable, adapter.EXPECTED_REQUESTED_RUNTIME, "canonical/m.json"],
            pathlib.Path.cwd(),
            {},
        )
