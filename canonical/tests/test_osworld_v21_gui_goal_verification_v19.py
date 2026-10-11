from __future__ import annotations
import hashlib
from canonical.runtime.osworld_v21_gui_goal_verifier_v1 import verify_gui_goal
from canonical.runtime.osworld_v21_brain_agent_adapter_v8 import BrainOSWorldAgentV8
from canonical.runtime.osworld_v21_workflow_policy_v13 import decide

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"
V="https://accessibility.ubuntu.example.org/ns/value"

def tree(tag,label,extra=""):
    return (
      f'<root xmlns:state="{S}" xmlns:component="{C}" xmlns:value="{V}">'
      f'<{tag} name="{label}" state:visible="true" state:showing="true" '
      f'component:screencoord="(10, 10)" component:size="(100, 30)" {extra}>{label}</{tag}>'
      '</root>'
    )

def st(instruction,a11y):
    data=b"current"
    return {
      "instruction":instruction,"a11y_tree":a11y,
      "screenshot_sha256":hashlib.sha256(data).hexdigest(),
      "screenshot_bytes":data,"history":[],"ocr":None,
    }

def test_boolean_state_predicates():
    assert verify_gui_goal(st("Check Sync",tree("check-box","Sync",'state:checked="true"')))["pass"]
    assert verify_gui_goal(st("Uncheck Sync",tree("check-box","Sync",'state:checked="false"')))["pass"]
    assert verify_gui_goal(st("Select Premium",tree("item","Premium",'state:selected="true"')))["pass"]
    assert verify_gui_goal(st("Disable Auto Save",tree("check-box","Auto Save",'state:enabled="false"')))["pass"]

def test_exact_value_predicate():
    good=st('Set Username to "alice"',tree("entry","Username",'value:value="alice"'))
    bad=st('Set Username to "alice"',tree("entry","Username",'value:value="bob"'))
    assert verify_gui_goal(good)["pass"]
    assert verify_gui_goal(bad) is None

def test_active_window_predicate():
    assert verify_gui_goal(st("Open Settings",tree("frame","Settings",'state:active="true"')))["pass"]

def test_click_only_is_not_state_evidence():
    assert verify_gui_goal(st("Click Continue",tree("button","Continue"))) is None

def test_verified_initial_state_can_finish_without_mutation():
    a11y=tree("check-box","Sync",'state:checked="true"')
    agent=BrainOSWorldAgentV8(decide,policy_id="v19-test")
    _,actions=agent.predict("Check Sync",{"screenshot":b"current","accessibility_tree":a11y})
    assert actions==["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"]=="EXPLICIT_CURRENT_GUI_GOAL_EVIDENCE"
