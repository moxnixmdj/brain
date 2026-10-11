from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import (
    BrainOSWorldAgentV7,
    GOAL_EVIDENCE_SCHEMA,
)


def test_plain_gui_screen_change_does_not_authorize_done():
    calls={"n":0}
    def policy(state):
        calls["n"]+=1
        if calls["n"]==1:
            return {"response":"click","actions":[{"type":"CLICK","x":100,"y":100}]}
        return {"response":"done","actions":[{"type":"DONE"}]}
    agent=BrainOSWorldAgentV7(policy,policy_id="v18-test")
    _,first=agent.predict("Click Continue",{"screenshot":b"before"})
    assert first != ["WAIT"]
    _,second=agent.predict("Click Continue",{"screenshot":b"after"})
    assert second==["WAIT"]
    assert agent.history[-1]["terminal_block"]["reason"]=="GUI_DONE_REQUIRES_EXPLICIT_CURRENT_GOAL_EVIDENCE"
    assert agent.history[-1]["terminal_block"]["screen_changed_is_terminal_evidence"] is False


def test_explicit_current_gui_goal_evidence_authorizes_done():
    calls={"n":0}
    def policy(state):
        calls["n"]+=1
        if calls["n"]==1:
            return {"response":"click","actions":[{"type":"CLICK","x":100,"y":100}]}
        return {
            "response":"verified",
            "actions":[{"type":"DONE"}],
            "_goal_evidence":{
                "schema":GOAL_EVIDENCE_SCHEMA,
                "pass":True,
                "basis":"EXPLICIT_CURRENT_A11Y_PREDICATE",
                "current_screenshot_sha256":state["screenshot_sha256"],
                "task_specific_policy_data":False,
                "external_model_dependency":False,
            },
        }
    agent=BrainOSWorldAgentV7(policy,policy_id="v18-test")
    agent.predict("Enable option",{"screenshot":b"before"})
    _,second=agent.predict("Enable option",{"screenshot":b"after"})
    assert second==["DONE"]


def test_app_completion_receipt_remains_allowed():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.append({
        "screenshot_sha256":"a"*64,
        "actions":["WAIT"],
        "app_result":{"ok":True,"app":"vlc","operation":"pause"},
    })
    _,actions=agent.predict("Pause the video",{"screenshot":b"same"})
    assert actions==["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"]=="APP_OP_SUCCESS_RECEIPT"


def test_web_app_completion_gets_explicit_receipt():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.append({
        "screenshot_sha256":"a"*64,
        "actions":["WAIT"],
        "web_app_result":{"ok":True,"app":"mailhub","operation":"send"},
    })
    _,actions=agent.predict("Send the message",{"screenshot":b"same"})
    assert actions==["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"]=="WEB_APP_OP_SUCCESS_RECEIPT"


def test_code_completion_receipt_remains_allowed():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.append({
        "screenshot_sha256":"a"*64,
        "actions":["WAIT"],
        "code_result":{"ok":True,"operation":"PYTEST"},
    })
    _,actions=agent.predict("Run tests",{"screenshot":b"same"})
    assert actions==["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"]=="CODE_OP_VERIFIED_RECEIPT"


def test_media_completion_receipt_remains_allowed():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.append({
        "screenshot_sha256":"a"*64,
        "actions":["WAIT"],
        "media_result":{"ok":True,"operation":"TRIM"},
    })
    _,actions=agent.predict("Trim the clip",{"screenshot":b"same"})
    assert actions==["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"]=="MEDIA_OP_VERIFIED_RECEIPT"


def test_guest_assertion_completion_remains_allowed():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.append({
        "screenshot_sha256":"a"*64,
        "actions":["WAIT"],
        "guest_result":{"ok":True,"output":"ASSERT_PATH_EXISTS:PASS:/home/oai/share/x"},
    })
    _,actions=agent.predict("Verify file",{"screenshot":b"same"})
    assert actions==["DONE"]


def test_browser_observation_completion_remains_allowed():
    agent=BrainOSWorldAgentV7(
        lambda _s:{"response":"done","actions":[{"type":"DONE"}]},
        policy_id="v18-test",
    )
    agent.history.extend([
        {
            "screenshot_sha256":"a"*64,
            "actions":["WAIT"],
            "browser_result":{"type":"CLICK_TEXT","ok":True},
        },
        {
            "screenshot_sha256":"b"*64,
            "actions":["WAIT"],
            "browser_result":{"type":"OBSERVE","ok":True},
        },
    ])
    _,actions=agent.predict("Submit form",{"screenshot":b"current"})
    assert actions==["DONE"]
