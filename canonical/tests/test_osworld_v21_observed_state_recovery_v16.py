from __future__ import annotations

from canonical.runtime.osworld_v21_recovery_policy_v1 import route_recovery
from canonical.runtime.osworld_v21_workflow_policy_v11 import decide

STATE_NS="https://accessibility.ubuntu.example.org/ns/state"
COMP_NS="https://accessibility.ubuntu.example.org/ns/component"

def xml(*buttons):
    rows=[]
    for i,(label,x,y) in enumerate(buttons):
        rows.append(
            f'<button name="{label}" '
            f'state:visible="true" state:showing="true" '
            f'component:screencoord="({x}, {y})" component:size="(80, 30)">{label}</button>'
        )
    return (
        f'<root xmlns:state="{STATE_NS}" xmlns:component="{COMP_NS}">'
        + "".join(rows) + "</root>"
    )

def state(instruction,tree,history=None,sha="same"):
    return {
        "instruction":instruction,
        "a11y_tree":tree,
        "history":list(history or []),
        "screenshot_sha256":sha,
        "screenshot_bytes":b"synthetic",
        "ocr":None,
    }

def action(out):
    assert isinstance(out,dict)
    assert isinstance(out.get("actions"),list) and len(out["actions"])==1
    return out["actions"][0]

def test_operation_error_prefers_unique_retry():
    s=state(
        "Continue the task",
        xml(("Retry",10,20),("Cancel",120,20)),
        [{"operation_error":"Timeout","actions":["WAIT"],"screenshot_sha256":"old"}],
    )
    out=route_recovery(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert (a["x"],a["y"])==(50,35)
    assert out["_policy_receipt"]["trigger"]=="OPERATION_ERROR"
    assert out["_policy_receipt"]["control"]=="Retry"

def test_no_progress_uses_reversible_close_not_retry():
    s=state(
        "Continue the task",
        xml(("Retry",10,20),("Close",120,20)),
        [{"actions":["CLICK"],"screenshot_sha256":"same"}],
    )
    out=route_recovery(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert (a["x"],a["y"])==(160,35)
    assert out["_policy_receipt"]["trigger"]=="NO_PROGRESS"
    assert out["_policy_receipt"]["control"]=="Close"

def test_ambiguous_recovery_control_fails_closed():
    s=state(
        "Continue the task",
        xml(("Retry",10,20),("Retry",120,20)),
        [{"operation_error":"Timeout","actions":["WAIT"],"screenshot_sha256":"old"}],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["reason"]=="AMBIGUOUS_SAFE_CONTROL"

def test_recovery_loop_is_suppressed_on_same_state():
    s=state(
        "Continue the task",
        xml(("Cancel",10,20)),
        [{
            "actions":["CLICK"],
            "screenshot_sha256":"same",
            "policy_receipt":{
                "schema":"PROJECT_BRAIN_OSWORLD_V21_RECOVERY_POLICY_V1",
                "route":"SAFE_RECOVERY_CLICK",
                "trigger":"NO_PROGRESS",
                "control":"Cancel",
            },
        }],
    )
    out=route_recovery(s)
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["route"]=="RECOVERY_LOOP_SUPPRESSED"

def test_v11_recovery_preempts_normal_goal_action_after_error():
    s=state(
        'Click "Continue"',
        xml(("Retry",10,20),("Continue",120,20)),
        [{"operation_error":"BrowserOpsError:stale","actions":["WAIT"],"screenshot_sha256":"old"}],
    )
    out=decide(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert (a["x"],a["y"])==(50,35)
    assert out["_policy_receipt"]["route"]=="SAFE_RECOVERY_CLICK"

def test_v11_falls_through_when_no_recovery_trigger():
    s=state('Click "Continue"',xml(("Continue",120,20)),[])
    out=decide(s)
    a=action(out)
    assert a["type"]=="CLICK"
    assert (a["x"],a["y"])==(160,35)
