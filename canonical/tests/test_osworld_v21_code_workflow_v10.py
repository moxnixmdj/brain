from __future__ import annotations

import inspect
import json

from canonical.runtime.osworld_v21_brain_agent_adapter_v4 import BrainOSWorldAgentV4
from canonical.runtime.osworld_v21_brain_subject_v10 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_code_policy_overlay_v1 import route_code
from canonical.runtime.osworld_v21_host_code_ops_v1 import CodeOpsError, OSWorldHostCodeOps
from canonical.runtime.osworld_v21_workflow_policy_v6 import decide


def state(instruction, history=None):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "a11y_tree": None,
        "ocr": None,
        "screenshot_sha256": "s0",
    }


def action(out):
    assert len(out["actions"]) == 1
    return out["actions"][0]


def code_receipt(out, result, *, screenshot="s0"):
    a = action(out)
    return {
        "screenshot_sha256": screenshot,
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_code_operation": {
            "operation": a["operation"],
            "args": a.get("args", {}),
        },
        "code_result": {
            "type": "CODE_OP",
            "ok": result.get("ok") is True,
            "operation": a["operation"],
            "result": dict(result),
            "status": "success",
            "output": json.dumps(result),
        },
    }


class FakeController:
    def __init__(self, output):
        self.output = output
        self.programs = []

    def execute_python_command(self, program):
        self.programs.append(program)
        return {"status": "success", "output": json.dumps(self.output)}


class FakeEnv:
    vm_screen_size = (1920, 1080)

    def __init__(self, output):
        self.controller = FakeController(output)


def test_code_policy_routes_exact_replace_and_compile():
    out = route_code(state(
        'Replace "alpha" with "beta" in /home/oai/share/project/app.py'
    ))
    assert action(out) == {
        "type": "CODE_OP",
        "operation": "REPLACE_TEXT_VERIFIED",
        "args": {
            "path": "/home/oai/share/project/app.py",
            "old": "alpha",
            "new": "beta",
            "replace_all": True,
        },
    }

    out = route_code(state(
        "Compile /home/oai/share/project/app.py"
    ))
    assert action(out) == {
        "type": "CODE_OP",
        "operation": "PYTHON_COMPILE",
        "args": {"path": "/home/oai/share/project/app.py"},
    }


def test_pytest_route_is_fixed_and_receipted():
    ctl = FakeController({
        "ok": True,
        "operation": "PYTEST",
        "cwd": "/home/oai/share/project",
        "target": None,
        "returncode": 0,
        "stdout": "4 passed",
        "stderr": "",
    })
    ops = OSWorldHostCodeOps()
    ops.bind_environment(FakeEnv(ctl.output))
    ops.environment.controller = ctl
    out = ops.run({
        "operation": "PYTEST",
        "args": {"cwd": "/home/oai/share/project"},
    })
    assert out["ok"] is True
    program = ctl.programs[-1]
    assert "_scan(cwd)" in program
    assert "[sys.executable,'-m','pytest','-q']" in program
    assert "shell=True" not in program


def test_code_paths_fail_closed_outside_safe_root_and_on_traversal():
    ops = OSWorldHostCodeOps()
    for payload, expected in (
        ({"operation": "READ_TEXT", "args": {"path": "/tmp/x.py"}}, "CODE_PATH_OUTSIDE_SAFE_ROOT"),
        ({"operation": "READ_TEXT", "args": {"path": "/home/oai/share/../x.py"}}, "CODE_PATH_TRAVERSAL_FORBIDDEN"),
        ({"operation": "READ_TEXT", "args": {"path": "/home/oai/evaluation_examples/x.py"}}, "CODE_PATH_PROTECTED"),
    ):
        try:
            ops.run(payload)
        except CodeOpsError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError("expected fail closed")


def test_replacement_payload_remains_data():
    injected = "x'; __import__('os').system('id'); #"
    ctl = FakeController({
        "ok": True,
        "operation": "REPLACE_TEXT_VERIFIED",
        "path": "/home/oai/share/project/app.py",
        "sha256": "abc",
    })
    ops = OSWorldHostCodeOps()
    ops.bind_environment(FakeEnv(ctl.output))
    ops.environment.controller = ctl
    ops.run({
        "operation": "REPLACE_TEXT_VERIFIED",
        "args": {
            "path": "/home/oai/share/project/app.py",
            "old": "alpha",
            "new": injected,
        },
    })
    program = ctl.programs[-1]
    assert repr(injected) in program
    assert "subprocess.run" not in program.split("elif", 1)[0] if "elif" in program else True


def test_edit_then_test_workflow_advances_only_after_receipts():
    instruction = (
        'Replace "alpha" with "beta" in /home/oai/share/project/app.py; '
        "then run tests in /home/oai/share/project"
    )
    first = decide(state(instruction))
    assert action(first)["operation"] == "REPLACE_TEXT_VERIFIED"
    h1 = code_receipt(first, {
        "ok": True,
        "operation": "REPLACE_TEXT_VERIFIED",
        "path": "/home/oai/share/project/app.py",
        "sha256": "a",
    })

    second = decide(state(instruction, [h1]))
    assert action(second) == {
        "type": "CODE_OP",
        "operation": "PYTEST",
        "args": {"cwd": "/home/oai/share/project"},
    }
    h2 = code_receipt(second, {
        "ok": True,
        "operation": "PYTEST",
        "cwd": "/home/oai/share/project",
        "target": None,
        "returncode": 0,
        "stdout": "4 passed",
        "stderr": "",
    })

    third = decide(state(instruction, [h1, h2]))
    assert third["actions"] == [{"type": "DONE"}]


def test_failed_tests_never_complete_clause():
    instruction = "Run tests in /home/oai/share/project"
    first = decide(state(instruction))
    failed = code_receipt(first, {
        "ok": False,
        "operation": "PYTEST",
        "cwd": "/home/oai/share/project",
        "target": None,
        "returncode": 1,
        "stdout": "1 failed",
        "stderr": "",
    })
    second = decide(state(instruction, [failed]))
    assert action(second)["type"] == "CODE_OP"
    assert action(second)["operation"] == "PYTEST"


class FakeCode:
    def __init__(self):
        self.calls = []

    def run(self, payload):
        self.calls.append(dict(payload))
        return {
            "type": "CODE_OP",
            "ok": True,
            "operation": payload["operation"],
            "result": {"ok": True, "operation": payload["operation"]},
            "status": "success",
            "output": "ok",
        }


def test_adapter_records_code_receipt_and_allows_receipted_done():
    fake = FakeCode()
    calls = {"n": 0}

    def policy(_state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "response": "compile",
                "actions": [{
                    "type": "CODE_OP",
                    "operation": "PYTHON_COMPILE",
                    "args": {"path": "/home/oai/share/project/app.py"},
                }],
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgentV4(policy, policy_id="test-v10", code_controller=fake)
    obs = {"screenshot": b"one", "accessibility_tree": None}
    response, actions = agent.predict("Compile /home/oai/share/project/app.py", obs)
    assert actions == ["WAIT"]
    assert agent.history[-1]["code_result"]["ok"] is True

    response, actions = agent.predict(
        "Compile /home/oai/share/project/app.py",
        {"screenshot": b"two", "accessibility_tree": None},
    )
    assert actions == ["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"] == "CODE_OP_VERIFIED_RECEIPT"


def test_v10_subject_is_model_independent_and_v9_not_mutated_by_import():
    subject = build_subject()
    assert subject.policy_id == SUBJECT_ID
    import canonical.runtime.osworld_v21_host_code_ops_v1 as h
    import canonical.runtime.osworld_v21_code_policy_overlay_v1 as p
    import canonical.runtime.osworld_v21_workflow_policy_v6 as w
    import canonical.runtime.osworld_v21_brain_subject_v10 as s
    source = "\n".join(inspect.getsource(x).casefold() for x in (h, p, w, s))
    for forbidden in ("openai", "anthropic", "gemini", "qwen", "reference_trajectory", "task_001"):
        assert forbidden not in source
