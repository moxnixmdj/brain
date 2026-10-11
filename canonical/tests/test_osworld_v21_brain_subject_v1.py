from canonical.runtime.osworld_v21_brain_subject_v1 import (
    SUBJECT_ID,
    build_subject,
    subject_manifest,
)


class FakeBrowser:
    def bind_environment(self, _env):
        pass
    def run(self, _op):
        return {"type": "OBSERVE", "active_url": "https://example.test"}


def test_subject_manifest_is_model_independent_and_no_external_generation():
    m = subject_manifest()
    assert m["subject_id"] == SUBJECT_ID
    assert m["producer_cognition_general_purpose_model_dependency"] is False
    assert m["task_specific_policy_data"] is False
    assert m["reference_trajectory_execution_input"] is False
    assert m["external_generation_provider"] is False
    assert "osworld_v21_local_qwen_policy_v1.py" in m["quarantined_diagnostic_routes"][0]


def test_subject_composition_accepts_injected_synthetic_policy():
    calls = {"n": 0}
    def policy(_state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"response": "click", "actions": [{"type": "CLICK", "x": 10, "y": 10}]}
        return {"response": "done", "actions": [{"type": "DONE"}]}

    class FakeGuest:
        def bind_environment(self, _env):
            pass
        def run(self, _payload):
            return {"type": "STATE_OPS", "ok": True}

    agent = build_subject(
        policy_provider=policy,
        ocr_provider=None,
        browser_controller=FakeBrowser(),
    )
    agent.guest_controller = FakeGuest()
    response, actions = agent.predict("synthetic task", {"screenshot": b"x"})
    assert response == "click"
    assert actions == ["pyautogui.click(x=10, y=10, button='left')"]
    response2, actions2 = agent.predict("synthetic task", {"screenshot": b"y"})
    assert response2 == "done"
    assert actions2 == ["DONE"]
