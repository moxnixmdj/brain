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
