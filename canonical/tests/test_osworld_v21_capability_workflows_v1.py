from __future__ import annotations

from canonical.runtime.osworld_v21_workflow_policy_v1 import decide


def state(instruction, *, history=None, a11y=None, screenshot="s0"):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "a11y_tree": a11y,
        "ocr": None,
        "screenshot_sha256": screenshot,
    }


def guest_receipt(out, output, screenshot="s0"):
    action=out["actions"][0]
    return {
        "screenshot_sha256": screenshot,
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operations":action["ops"],
        "guest_result":{"type":"STATE_OPS","ok":True,"status":"ok","output":output},
    }


def browser_receipt(out, result, screenshot="s0"):
    action=out["actions"][0]
    return {
        "screenshot_sha256": screenshot,
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operation":action["op"],
        "browser_result":dict(result),
    }


def app_a11y(name):
    S="https://accessibility.ubuntu.example.org/ns/state"
    C="https://accessibility.ubuntu.example.org/ns/component"
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="{name}">'
        f'<frame s:active="true" s:visible="true" s:showing="true" '
        f'c:screencoord="(0, 0)" c:size="(800, 600)" /></application></root>'
    )


def app_receipt(out, screenshot="s0"):
    action=out["actions"][0]
    return {
        "screenshot_sha256": screenshot,
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operation":{
            "app":action["app"],"operation":action["operation"],"args":action["args"],
        },
        "app_result":{
            "type":"APP_OP","ok":True,"app":action["app"],
            "operation":action["operation"],"status":"success","output":"ok",
        },
    }


def test_browser_then_file_cross_tool_workflow_advances_only_after_browser_verify():
    instruction='Open https://example.com; then create "done.txt" containing "ready"'

    first=decide(state(instruction))
    assert first["actions"] == [{
        "type":"BROWSER_OP","op":{"type":"NAVIGATE","url":"https://example.com"}
    }]
    h1=browser_receipt(first,{"type":"NAVIGATE","ok":True,"url":"https://example.com"})

    second=decide(state(instruction,history=[h1]))
    assert second["actions"] == [{"type":"BROWSER_OP","op":{"type":"OBSERVE"}}]
    h2=browser_receipt(second,{
        "type":"OBSERVE","ok":True,"active_url":"https://example.com",
        "pages":[{"url":"https://example.com"}],"controls":[]
    })

    third=decide(state(instruction,history=[h1,h2]))
    assert third["actions"][0]["type"]=="STATE_OPS"
    assert third["actions"][0]["ops"][0] == {
        "type":"WRITE_TEXT","path":"/home/oai/share/done.txt","text":"ready"
    }
    h3=guest_receipt(
        third,
        "WRITE_TEXT:PASS:/home/oai/share/done.txt:chars=5\n"
        "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/done.txt",
    )
    fourth=decide(state(instruction,history=[h1,h2,h3]))
    assert fourth["actions"] == [{"type":"DONE"}]


def test_unverified_browser_clause_never_leaks_into_file_clause():
    instruction='Open https://example.com; then create "done.txt" containing "ready"'
    first=decide(state(instruction))
    h1=browser_receipt(first,{"type":"NAVIGATE","ok":True,"url":"https://example.com"})
    second=decide(state(instruction,history=[h1]))
    assert second["_policy_receipt"]["clause_index"]==0
    assert second["actions"] == [{"type":"BROWSER_OP","op":{"type":"OBSERVE"}}]


def test_app_then_file_workflow_uses_receipted_app_completion():
    instruction='Pause the video; then create "paused.txt" containing "yes"'
    tree=app_a11y("VLC media player")

    first=decide(state(instruction,a11y=tree))
    assert first["actions"][0] == {
        "type":"APP_OP","app":"vlc","operation":"pause","args":{}
    }
    h1=app_receipt(first)

    second=decide(state(instruction,history=[h1],a11y=tree))
    assert second["_policy_receipt"]["clause_index"]==1
    assert second["actions"][0]["type"]=="STATE_OPS"
    assert second["actions"][0]["ops"][0] == {
        "type":"WRITE_TEXT","path":"/home/oai/share/paused.txt","text":"yes"
    }


def test_three_clause_file_workflow_preserves_order():
    instruction=(
        'Create "a.txt" containing "a"; then create "b.txt" containing "b"; '
        'then create "c.txt" containing "c"'
    )
    history=[]
    expected=[("a.txt","a"),("b.txt","b"),("c.txt","c")]
    for index,(name,value) in enumerate(expected):
        out=decide(state(instruction,history=history))
        assert out["_policy_receipt"]["clause_index"]==index
        assert out["actions"][0]["ops"][0]["path"]==f"/home/oai/share/{name}"
        history.append(guest_receipt(
            out,
            f"WRITE_TEXT:PASS:/home/oai/share/{name}:chars=1\n"
            f"ASSERT_TEXT_EQUALS:PASS:/home/oai/share/{name}",
        ))
    done=decide(state(instruction,history=history))
    assert done["actions"]==[{"type":"DONE"}]


def test_prior_clause_receipt_cannot_satisfy_later_clause():
    instruction='Create "a.txt" containing "x"; then create "b.txt" containing "x"'
    first=decide(state(instruction))
    h1=guest_receipt(
        first,
        "WRITE_TEXT:PASS:/home/oai/share/a.txt:chars=1\n"
        "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/a.txt",
    )
    second=decide(state(instruction,history=[h1]))
    assert second["_policy_receipt"]["clause_index"]==1
    assert second["actions"][0]["ops"][0]["path"]=="/home/oai/share/b.txt"
