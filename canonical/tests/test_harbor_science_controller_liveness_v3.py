from __future__ import annotations
import asyncio
from canonical.runtime import harbor_science_agent_v1 as s

class Receipt:
    def __init__(self, rc=0, stdout="", stderr=""):
        self.returncode=rc; self.stdout=stdout; self.stderr=stderr

class DeadControllerEnv:
    async def exec(self, command, timeout_sec=None, **kwargs):
        if "PROJECT_BRAIN_CONTROLLER_LIVENESS_V1" in command:
            return Receipt(42, "", "CONTROLLER_EXITED_BEFORE_INPUT")
        return Receipt(0, "ok", "")

def test_interactive_controller_detection_is_task_bound():
    d={"/app/submission/controller.py":"x"}
    mapped={"BRAIN_DELIVERABLE_01":"/app/submission/controller.py"}
    assert s._interactive_controller_paths(
        "Create /app/submission/controller.py. Read one JSON line from stdin.", mapped
    ) == {"/app/submission/controller.py"}
    assert s._interactive_controller_paths(
        "Create /app/submission/controller.py as a static reference.", mapped
    ) == set()

def test_deliverable_liveness_failure_blocks_verification():
    out=asyncio.run(s._validate_brain_deliverable(
        "BRAIN_DELIVERABLE_01",
        "/app/submission/controller.py",
        DeadControllerEnv(),
        require_interactive_liveness=True,
    ))
    assert out["verified"] is False
    assert any(
        row["returncode"] == 42 and "PROJECT_BRAIN_CONTROLLER_LIVENESS_V1" in row["command"]
        for row in out["checks"]
    )

def test_final_output_gate_rechecks_controller_liveness():
    failures=asyncio.run(s._declared_output_gate(
        DeadControllerEnv(),
        ["/app/submission/controller.py"],
        {"/app/submission/controller.py"},
    ))
    assert failures
    assert failures[0]["reason"] == "INTERACTIVE_CONTROLLER_EXITED_BEFORE_INPUT"
