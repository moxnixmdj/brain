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
    assert actions == ["pyautogui.click(100, 200)"]


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
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgent(policy, policy_id="test-policy")
    agent.reset()
    response, actions = agent.predict("finish the task", {"screenshot": b"image-bytes"})
    assert response == "done"
    assert actions == ["DONE"]
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


class _FakeBrowser:
    def __init__(self):
        self.bound = None
        self.ops = []

    def bind_environment(self, env):
        self.bound = env

    def run(self, op):
        self.ops.append(dict(op))
        return {"type": "OBSERVE", "active_url": "https://example.test/", "visible_text": "hello"}


def test_browser_tool_loop_binds_environment_and_returns_wait():
    browser = _FakeBrowser()
    calls = []
    def policy(state):
        calls.append(state)
        if not state["history"]:
            return {
                "response": "observe browser",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgent(policy, policy_id="browser-policy", browser_controller=browser)
    env = object()
    agent.bind_environment(env)
    assert browser.bound is env

    response, actions = agent.predict("inspect page", {"screenshot": b"one"})
    assert response == "observe browser"
    assert actions == ["WAIT"]
    assert browser.ops == [{"type": "OBSERVE"}]
    assert agent.history[-1]["browser_result"]["visible_text"] == "hello"

    response2, actions2 = agent.predict("inspect page", {"screenshot": b"two"})
    assert response2 == "done"
    assert actions2 == ["DONE"]
    assert calls[-1]["history"][-1]["browser_result"]["active_url"] == "https://example.test/"


def test_browser_op_must_be_singleton_and_structured():
    browser = _FakeBrowser()
    def bad_policy(_state):
        return {
            "actions": [
                {"type": "BROWSER_OP", "op": {"type": "OBSERVE"}},
                {"type": "DONE"},
            ]
        }
    agent = BrainOSWorldAgent(bad_policy, policy_id="bad", browser_controller=browser)
    try:
        agent.predict("x", {"screenshot": b"x"})
    except AdapterError as exc:
        assert str(exc) == "ACTION_TYPE_UNSUPPORTED:BROWSER_OP"
    else:
        raise AssertionError("expected mixed browser action rejection")
