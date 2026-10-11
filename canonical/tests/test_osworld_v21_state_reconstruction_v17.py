from __future__ import annotations

from canonical.runtime.osworld_v21_recovery_policy_v2 import route_recovery
from canonical.runtime.osworld_v21_workflow_policy_v12 import decide

STATE_NS="https://accessibility.ubuntu.example.org/ns/state"
COMP_NS="https://accessibility.ubuntu.example.org/ns/component"

def tree(*items):
    rows=[]
    for tag,label,x,y in items:
        rows.append(
            f'<{tag} name="{label}" '
            f'state:visible="true" state:showing="true" '
            f'component:screencoord="({x}, {y})" component:size="(100, 40)">{label}</{tag}>'
        )
    return (
        f'<root xmlns:state="{STATE_NS}" xmlns:component="{COMP_NS}">'
        + "".join(rows) + "</root>"
    )

def state(instruction,a11y=None,history=None,sha="same"):
    return {
        "instruction":instruction,
        "a11y_tree":a11y or tree(),
        "history":list(history or []),
        "screenshot_sha256":sha,
        "screenshot_bytes":b"synthetic",
        "ocr":None,
    }

def action(out):
    assert isinstance(out,dict)
    assert isinstance(out.get("actions"),list) and len(out["actions"])==1
    return out["actions"][0]

def test_browser_failure_without_dialog_reobserves_semantic_state():
    s=state(
        "Continue browsing",
        history=[{
            "operation_error":"BrowserOpsError:stale target",
            "actions":["WAIT"],
            "screenshot_sha256":"same",
        }],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"BROWSER_OP","op":{"type":"OBSERVE"}}
    assert out["_policy_receipt"]["route"]=="BROWSER_REOBSERVE"

def test_repeated_browser_reobserve_failure_is_suppressed():
    s=state(
        "Continue browsing",
        history=[{
            "operation_error":"BrowserOpsError:connection failed",
            "actions":["WAIT"],
            "screenshot_sha256":"same",
            "policy_receipt":{
                "schema":"PROJECT_BRAIN_OSWORLD_V21_RECOVERY_POLICY_V2",
                "route":"BROWSER_REOBSERVE",
            },
        }],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["route"]=="RECOVERY_RECONSTRUCTION_LOOP_SUPPRESSED"

def test_visible_unmodeled_dialog_uses_one_reversible_escape():
    s=state(
        "Continue the task",
        tree(("dialog","Unexpected dialog",200,100)),
        history=[{"actions":["CLICK"],"screenshot_sha256":"same"}],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"PRESS","key":"esc"}
    assert out["_policy_receipt"]["route"]=="MODAL_ESCAPE"

def test_repeated_modal_escape_on_same_state_is_suppressed():
    s=state(
        "Continue the task",
        tree(("dialog","Unexpected dialog",200,100)),
        history=[{
            "actions":["pyautogui.press('esc')"],
            "screenshot_sha256":"same",
            "policy_receipt":{
                "schema":"PROJECT_BRAIN_OSWORLD_V21_RECOVERY_POLICY_V2",
                "route":"MODAL_ESCAPE",
            },
        }],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["route"]=="RECOVERY_RECONSTRUCTION_LOOP_SUPPRESSED"

def test_nonbrowser_error_without_modal_preserves_fail_closed_wait():
    s=state(
        "Continue the task",
        history=[{
            "operation_error":"GuestOpsError:unknown failure",
            "actions":["WAIT"],
            "screenshot_sha256":"same",
        }],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["route"]=="RECOVERY_UNRESOLVED"

def test_explicit_safe_button_still_beats_reconstruction():
    s=state(
        "Continue the task",
        tree(("button","Retry",20,20),("dialog","Failure",200,100)),
        history=[{
            "operation_error":"BrowserOpsError:stale target",
            "actions":["WAIT"],
            "screenshot_sha256":"same",
        }],
    )
    out=route_recovery(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert out["_policy_receipt"]["route"]=="SAFE_RECOVERY_CLICK"
    assert out["_policy_receipt"]["control"]=="Retry"

def test_v12_reconstruction_preempts_normal_action_after_browser_failure():
    s=state(
        'Click "Continue"',
        tree(("button","Continue",200,100)),
        history=[{
            "operation_error":"BrowserOpsError:stale target",
            "actions":["WAIT"],
            "screenshot_sha256":"same",
        }],
    )
    out=decide(s)
    assert action(out)=={"type":"BROWSER_OP","op":{"type":"OBSERVE"}}

def test_v12_falls_through_without_recovery_trigger():
    s=state('Click "Continue"',tree(("button","Continue",200,100)),[])
    out=decide(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert (a["x"],a["y"])==(250,120)
