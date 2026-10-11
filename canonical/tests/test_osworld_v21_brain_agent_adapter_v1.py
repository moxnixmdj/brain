from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import (
    AdapterError,
    BrainOSWorldAgent,
    compile_actions,
)


def test_action_compilation_exact_pyautogui_surface():
    response, actions = compile_actions({
        "response": "click target",
        "actions": [{"type": "CLICK", "x": 100, "y": 200}],
    })
    assert response == "click target"
    assert actions == ["pyautogui.click(x=100, y=200, button='left')"]


def test_special_action_is_singleton():
    try:
        compile_actions({
            "actions": [
                {"type": "WAIT"},
                {"type": "CLICK", "x": 1, "y": 1},
            ]
        })
    except AdapterError as exc:
        assert str(exc) == "SPECIAL_ACTION_MUST_BE_SINGLETON"
    else:
        raise AssertionError("expected fail closed")


def test_agent_binds_screenshot_and_history():
    seen = []
    def policy(state):
        seen.append(state)
        return {"response": "wait", "actions": [{"type": "WAIT"}]}

    agent = BrainOSWorldAgent(policy, policy_id="test-policy")
    agent.reset()
    response, actions = agent.predict("finish the task", {"screenshot": b"image-bytes"})
    assert response == "wait"
    assert actions == ["WAIT"]
    assert len(seen) == 1
    assert seen[0]["instruction"] == "finish the task"
    assert len(seen[0]["screenshot_sha256"]) == 64
    assert len(agent.history) == 1


def test_wrong_resolution_rejected():
    try:
        BrainOSWorldAgent(lambda _: {"actions":[{"type":"WAIT"}]}, policy_id="p", screen_width=1280)
    except AdapterError as exc:
        assert str(exc) == "MATCHED_PROTOCOL_REQUIRES_1920x1080"
    else:
        raise AssertionError("expected fail closed")


class _FakeGuest:
    def __init__(self, fail=False):
        self.bound = None
        self.payloads = []
        self.fail = fail

    def bind_environment(self, env):
        self.bound = env

    def run(self, payload):
        self.payloads.append(dict(payload))
        if self.fail:
            raise RuntimeError("synthetic guest failure")
        return {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": "ASSERT_PATH_EXISTS:PASS:/home/oai/share/a.txt",
        }


class _FakeBrowser:
    def __init__(self):
        self.bound = None
        self.ops = []

    def bind_environment(self, env):
        self.bound = env

    def run(self, op):
        self.ops.append(dict(op))
        kind = str(op.get("type") or "").upper()
        return {
            "type": kind,
            "active_url": "https://example.test/",
            "visible_text": "hello" if kind == "OBSERVE" else "",
        }


def test_browser_tool_loop_binds_environment_and_returns_wait():
    browser = _FakeBrowser()
    calls = []
    def policy(state):
        calls.append(state)
        if len(state["history"]) == 0:
            return {
                "response": "mutate browser",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "CLICK_TEXT", "text": "Save"}}],
            }
        if len(state["history"]) == 1:
            return {
                "response": "observe browser",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    guest = _FakeGuest()
    agent = BrainOSWorldAgent(
        policy,
        policy_id="browser-policy",
        browser_controller=browser,
        guest_controller=guest,
    )
    env = object()
    agent.bind_environment(env)
    assert browser.bound is env
    assert guest.bound is env

    response, actions = agent.predict("inspect page", {"screenshot": b"one"})
    assert response == "mutate browser"
    assert actions == ["WAIT"]
    assert browser.ops == [{"type": "CLICK_TEXT", "text": "Save"}]
    assert agent.history[-1]["browser_result"]["type"] == "CLICK_TEXT"
    assert agent.history[-1]["submitted_operation"] == {"type": "CLICK_TEXT", "text": "Save"}

    response2, actions2 = agent.predict("inspect page", {"screenshot": b"two"})
    assert response2 == "observe browser"
    assert actions2 == ["WAIT"]
    assert agent.history[-1]["browser_result"]["visible_text"] == "hello"

    response3, actions3 = agent.predict("inspect page", {"screenshot": b"three"})
    assert response3 == "done"
    assert actions3 == ["DONE"]
    assert calls[-1]["history"][-1]["browser_result"]["active_url"] == "https://example.test/"


def test_malformed_mixed_browser_action_is_recoverable():
    browser = _FakeBrowser()
    guest = _FakeGuest()
    def bad_policy(_state):
        return {
            "actions": [
                {"type": "BROWSER_OP", "op": {"type": "OBSERVE"}},
                {"type": "DONE"},
            ]
        }
    agent = BrainOSWorldAgent(
        bad_policy,
        policy_id="bad",
        browser_controller=browser,
        guest_controller=guest,
    )
    response, actions = agent.predict("x", {"screenshot": b"x"})
    assert response == ""
    assert actions == ["WAIT"]
    assert "BROWSER_OP_MUST_BE_SINGLETON_HOST_OPERATION" in agent.history[-1]["operation_error"]


def test_browser_failure_becomes_recovery_receipt():
    class BrokenBrowser(_FakeBrowser):
        def run(self, op):
            raise ValueError("stale selector")

    agent = BrainOSWorldAgent(
        lambda _state: {
            "response": "try selector",
            "actions": [{"type": "BROWSER_OP", "op": {"type": "CLICK_TEXT", "text": "Save"}}],
        },
        policy_id="recover-browser",
        browser_controller=BrokenBrowser(),
        guest_controller=_FakeGuest(),
    )
    response, actions = agent.predict("save", {"screenshot": b"x"})
    assert response == "try selector"
    assert actions == ["WAIT"]
    assert "stale selector" in agent.history[-1]["operation_error"]


def test_state_ops_execute_host_side_and_receipt_returns_to_next_cycle():
    guest = _FakeGuest()
    seen = []
    def policy(state):
        seen.append(state)
        if not state["history"]:
            return {
                "response": "write",
                "actions": [{
                    "type": "STATE_OPS",
                    "ops": [{"type": "WRITE_TEXT", "path": "/home/oai/share/a.txt", "text": "alpha"}],
                }],
                "_policy_receipt": {"model": "brain-qwen3.5-9b"},
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgent(
        policy,
        policy_id="state",
        browser_controller=_FakeBrowser(),
        guest_controller=guest,
    )
    env = object()
    agent.bind_environment(env)
    _, actions = agent.predict("write file", {"screenshot": b"one"})
    assert actions == ["WAIT"]
    assert guest.payloads[0]["ops"][0]["type"] == "WRITE_TEXT"
    assert agent.history[-1]["submitted_operations"] == [
        {"type": "WRITE_TEXT", "path": "/home/oai/share/a.txt", "text": "alpha"}
    ]
    assert "ASSERT_PATH_EXISTS:PASS" in agent.history[-1]["guest_result"]["output"]
    assert agent.history[-1]["policy_receipt"]["model"] == "brain-qwen3.5-9b"

    _, actions2 = agent.predict("write file", {"screenshot": b"two"})
    assert actions2 == ["DONE"]
    assert seen[-1]["history"][-1]["guest_result"]["ok"] is True


def test_done_first_cycle_is_rejected_into_recovery():
    agent = BrainOSWorldAgent(
        lambda _state: {"response": "done", "actions": [{"type": "DONE"}]},
        policy_id="finish-guard",
        browser_controller=_FakeBrowser(),
        guest_controller=_FakeGuest(),
    )
    response, actions = agent.predict("do work", {"screenshot": b"same"})
    assert response == "done"
    assert actions == ["WAIT"]
    assert "DONE_WITHOUT_PRIOR_OBSERVED_ACTION" in agent.history[-1]["operation_error"]


def test_done_after_unchanged_gui_state_is_rejected():
    calls = {"n": 0}
    def policy(_state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"response": "click", "actions": [{"type": "CLICK", "x": 10, "y": 10}]}
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgent(
        policy,
        policy_id="finish-guard-gui",
        browser_controller=_FakeBrowser(),
        guest_controller=_FakeGuest(),
    )
    _, first = agent.predict("click then finish", {"screenshot": b"same"})
    assert first == ["pyautogui.click(10, 10)"]
    _, second = agent.predict("click then finish", {"screenshot": b"same"})
    assert second == ["WAIT"]
    assert "DONE_WITHOUT_VERIFIED_COMPLETION_EVIDENCE" in agent.history[-1]["operation_error"]


def test_done_after_receipted_state_verification_is_allowed():
    calls = {"n": 0}
    guest = _FakeGuest()
    def policy(_state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "response": "verify",
                "actions": [{
                    "type": "STATE_OPS",
                    "ops": [{"type": "ASSERT_PATH_EXISTS", "path": "/home/oai/share/a.txt"}],
                }],
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgent(
        policy,
        policy_id="finish-guard-receipt",
        browser_controller=_FakeBrowser(),
        guest_controller=guest,
    )
    _, first = agent.predict("verify then finish", {"screenshot": b"same"})
    assert first == ["WAIT"]
    _, second = agent.predict("verify then finish", {"screenshot": b"same"})
    assert second == ["DONE"]


def test_ocr_failure_is_fail_soft_observation_not_agent_crash():
    seen = []
    def broken_ocr(_image):
        raise RuntimeError("tesseract unavailable")
    def policy(state):
        seen.append(state)
        return {"response": "continue", "actions": [{"type": "WAIT"}]}

    agent = BrainOSWorldAgent(
        policy,
        policy_id="ocr-soft",
        browser_controller=_FakeBrowser(),
        guest_controller=_FakeGuest(),
        ocr_provider=broken_ocr,
    )
    response, actions = agent.predict("continue task", {"screenshot": b"image"})
    assert response == "continue"
    assert actions == ["WAIT"]
    assert seen[0]["ocr"]["status"] == "UNAVAILABLE"
    assert "tesseract unavailable" in seen[0]["ocr"]["reason"]
    assert seen[0]["ocr"]["terminal_semantic_authority"] is False
