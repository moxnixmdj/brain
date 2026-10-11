from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v6 import BrainOSWorldAgentV6
from canonical.runtime.osworld_v21_brain_subject_v12 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_constraint_guard_v1 import (
    PathInvariantGuard,
    action_conflict,
    extract_constraints,
)
from canonical.runtime.osworld_v21_workflow_policy_v7 import decide


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


def guest_receipt(out, path, text):
    return {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_operations": action(out)["ops"],
        "guest_result": {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": (
                f"WRITE_TEXT:PASS:{path}:chars={len(text)}\n"
                f"ASSERT_TEXT_EQUALS:PASS:{path}"
            ),
        },
    }


def test_extracts_and_removes_explicit_path_invariant():
    raw = (
        'Create "a.txt" containing "x"; then create "b.txt" containing "y"; '
        "while keeping /home/oai/share/protected.txt unchanged"
    )
    spec = extract_constraints(raw)
    assert spec["protected_paths"] == ["/home/oai/share/protected.txt"]
    assert "protected.txt" not in spec["clean_instruction"]
    assert spec["clean_instruction"].endswith('create "b.txt" containing "y"')


def test_action_guard_blocks_mutation_and_unbounded_gui():
    protected = ["/home/oai/share/protected.txt"]
    assert action_conflict({
        "type": "STATE_OPS",
        "ops": [{
            "type": "WRITE_TEXT",
            "path": "/home/oai/share/protected.txt",
            "text": "bad",
        }],
    }, protected) == "PROTECTED_PATH_STATE_MUTATION"
    assert action_conflict({
        "type": "STATE_OPS",
        "ops": [{
            "type": "WRITE_TEXT",
            "path": "/home/oai/share/other.txt",
            "text": "ok",
        }],
    }, protected) is None
    assert action_conflict({
        "type": "CODE_OP",
        "operation": "PYTEST",
        "args": {"cwd": "/home/oai/share"},
    }, protected) == "PROTECTED_PATH_TEST_SIDE_EFFECT_RISK"
    assert action_conflict({"type": "CLICK", "x": 1, "y": 2}, protected) == (
        "UNBOUNDED_GUI_MUTATION_WITH_ACTIVE_PATH_INVARIANT"
    )


class FileController:
    def __init__(self):
        self.files = {"/home/oai/share/protected.txt": b"ORIGINAL"}

    def get_file(self, path):
        return self.files.get(path)


class Env:
    def __init__(self):
        self.controller = FileController()
        self.setup_controller = object()


def test_snapshot_detects_out_of_band_mutation():
    env = Env()
    guard = PathInvariantGuard()
    guard.bind_environment(env)
    first = guard.snapshot(["/home/oai/share/protected.txt"])
    assert first["/home/oai/share/protected.txt"]["exists"] is True
    assert guard.verify()["pass"] is True
    env.controller.files["/home/oai/share/protected.txt"] = b"CHANGED"
    checked = guard.verify()
    assert checked["pass"] is False
    assert checked["changed"][0]["path"] == "/home/oai/share/protected.txt"


def test_twelve_clause_workflow_completes_without_constraint_text_polluting_clauses():
    clauses = [
        f'Create "f{i}.txt" containing "{i}"'
        for i in range(1, 13)
    ]
    raw = "; then ".join(clauses) + (
        "; while keeping /home/oai/share/protected.txt unchanged"
    )
    spec = extract_constraints(raw)
    clean = spec["clean_instruction"]
    history = []
    for i in range(1, 13):
        out = decide(state(clean, history))
        a = action(out)
        assert a["type"] == "STATE_OPS"
        path = f"/home/oai/share/f{i}.txt"
        assert a["ops"][0]["path"] == path
        history.append(guest_receipt(out, path, str(i)))
    done = decide(state(clean, history))
    assert done["actions"] == [{"type": "DONE"}]


class DummyController:
    def __init__(self, result=None):
        self.result = result or {"type": "DUMMY", "ok": True, "status": "ok", "output": ""}
        self.calls = []

    def bind_environment(self, env):
        self.env = env

    def run(self, payload):
        self.calls.append(dict(payload))
        return dict(self.result)


def _agent(policy, env):
    dummy = DummyController({
        "type": "STATE_OPS",
        "ok": True,
        "status": "ok",
        "output": "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/other.txt",
    })
    agent = BrainOSWorldAgentV6(
        policy,
        policy_id="test-v12",
        browser_controller=DummyController(),
        guest_controller=dummy,
        app_controller=DummyController(),
        web_app_controller=DummyController(),
        code_controller=DummyController(),
        media_controller=DummyController(),
        ocr_provider=None,
    )
    agent.bind_environment(env)
    return agent, dummy


def test_adapter_strips_constraint_and_blocks_protected_candidate():
    seen = []

    def policy(s):
        seen.append(s["instruction"])
        return {
            "response": "bad",
            "actions": [{
                "type": "STATE_OPS",
                "ops": [{
                    "type": "WRITE_TEXT",
                    "path": "/home/oai/share/protected.txt",
                    "text": "bad",
                }],
            }],
        }

    env = Env()
    agent, guest = _agent(policy, env)
    raw = (
        "Write another file; while keeping "
        "/home/oai/share/protected.txt unchanged"
    )
    _, actions = agent.predict(
        raw, {"screenshot": b"one", "accessibility_tree": None}
    )
    assert actions == ["WAIT"]
    assert seen == ["Write another file"]
    assert guest.calls == []
    assert agent.history[-1]["constraint_block"] == "PROTECTED_PATH_STATE_MUTATION"


def test_adapter_detects_external_constraint_breach_before_next_action():
    calls = {"n": 0}

    def policy(_s):
        calls["n"] += 1
        return {"response": "wait", "actions": [{"type": "WAIT"}]}

    env = Env()
    agent, _ = _agent(policy, env)
    raw = (
        "Inspect state; while keeping "
        "/home/oai/share/protected.txt unchanged"
    )
    _, actions = agent.predict(
        raw, {"screenshot": b"one", "accessibility_tree": None}
    )
    assert actions == ["WAIT"]
    env.controller.files["/home/oai/share/protected.txt"] = b"CORRUPTED"
    _, actions = agent.predict(
        raw, {"screenshot": b"two", "accessibility_tree": None}
    )
    assert actions == ["FAIL"]
    assert calls["n"] == 1
    assert "constraint_violation" in agent.history[-1]


def test_v12_subject_is_model_independent():
    subject = build_subject()
    assert subject.policy_id == SUBJECT_ID
