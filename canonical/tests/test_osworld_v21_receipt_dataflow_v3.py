from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_receipt_dataflow_v3 import (
    materialize_explicit_references,
    resolve_count,
    resolve_filtered_scalar,
    resolve_projection,
)
from canonical.runtime.osworld_v21_workflow_policy_v5 import decide
from canonical.runtime.osworld_v21_brain_subject_v8 import SUBJECT_ID, build_subject


def web(app, result):
    return {
        "web_app_result": {
            "type": "WEB_APP_OP",
            "ok": True,
            "app": app,
            "operation": "observe",
            "result": result,
        }
    }


def test_count_projection_and_filter_over_receipted_records():
    rows=[web("mailhub",{"messages":[
        {"subject":"Urgent","sender":"alice@example.com"},
        {"subject":"FYI","sender":"bob@example.com"},
    ]})]

    count=resolve_count(rows,"messages","Mailhub")
    assert count["pass"] is True and count["value"]==2

    first=resolve_projection(rows,"first","sender","Mailhub")
    last=resolve_projection(rows,"last","sender","Mailhub")
    allv=resolve_projection(rows,"all","sender","Mailhub")
    assert first["value"]=="alice@example.com"
    assert last["value"]=="bob@example.com"
    assert allv["value"]==["alice@example.com","bob@example.com"]

    selected=resolve_filtered_scalar(rows,"sender","Mailhub","subject","Urgent")
    assert selected["pass"] is True
    assert selected["value"]=="alice@example.com"


def test_filtered_relation_ambiguous_fails_closed():
    rows=[web("mailhub",{"messages":[
        {"subject":"Same","sender":"a@example.com"},
        {"subject":"Same","sender":"b@example.com"},
    ]})]
    out=resolve_filtered_scalar(rows,"sender","Mailhub","subject","Same")
    assert out["pass"] is False
    assert out["status"]=="OPEN__RELATION_AMBIGUOUS"


def test_sensitive_relational_fields_fail_closed():
    rows=[web("vaultbank",{"sessions":[{"token":"secret","name":"x"}]})]
    out=resolve_projection(rows,"first","token","VaultBank")
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED__SENSITIVE_FIELD"


def test_relational_reference_materialization():
    rows=[web("mailhub",{"messages":[
        {"subject":"Urgent","sender":"alice@example.com"},
        {"subject":"FYI","sender":"bob@example.com"},
    ]})]
    out=materialize_explicit_references(
        'create "count.txt" containing the count of messages from Mailhub', rows
    )
    assert out["pass"] is True
    assert '"2"' in out["text"]

    out=materialize_explicit_references(
        'create "sender.txt" containing the sender from Mailhub where subject is "Urgent"', rows
    )
    assert out["pass"] is True
    assert '"alice@example.com"' in out["text"]


def state(instruction,history=None):
    return {
        "instruction":instruction,
        "history":list(history or []),
        "screenshot_sha256":"s0",
        "a11y_tree":None,
        "ocr":None,
    }


def web_receipt(out,result):
    a=out["actions"][0]
    return {
        "screenshot_sha256":"s0",
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_web_app_operation":{
            "app":a["app"],"operation":a["operation"],"args":a["args"],
        },
        "web_app_result":{
            "type":"WEB_APP_OP","ok":True,
            "app":a["app"],"operation":a["operation"],"result":result,
        },
    }


def guest_receipt(out,path,text):
    return {
        "screenshot_sha256":"s0",
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operations":out["actions"][0]["ops"],
        "guest_result":{
            "type":"STATE_OPS","ok":True,"status":"ok",
            "output":f"WRITE_TEXT:PASS:{path}:chars={len(text)}\nASSERT_TEXT_EQUALS:PASS:{path}",
        },
    }


def test_workflow_counts_prior_records_then_executes_later_action():
    instruction=(
        'Check Mailhub; then create "count.txt" containing '
        'the count of messages from Mailhub'
    )
    first=decide(state(instruction))
    assert first["actions"][0]["type"]=="WEB_APP_OP"
    h1=web_receipt(first,{"messages":[
        {"sender":"a@example.com"},{"sender":"b@example.com"},{"sender":"c@example.com"}
    ]})

    second=decide(state(instruction,[h1]))
    assert second["_policy_receipt"]["dataflow"]["pass"] is True
    assert second["actions"][0]["type"]=="STATE_OPS"
    assert second["actions"][0]["ops"][0]["text"]=="3"

    h2=guest_receipt(second,"/home/oai/share/count.txt","3")
    third=decide(state(instruction,[h1,h2]))
    assert third["actions"]==[{"type":"DONE"}]


def test_workflow_selects_unique_record_by_explicit_predicate():
    instruction=(
        'Check Mailhub; then create "urgent_sender.txt" containing '
        'the sender from Mailhub where subject is "Urgent"'
    )
    first=decide(state(instruction))
    h1=web_receipt(first,{"messages":[
        {"subject":"FYI","sender":"b@example.com"},
        {"subject":"Urgent","sender":"a@example.com"},
    ]})
    second=decide(state(instruction,[h1]))
    assert second["actions"][0]["ops"][0]["text"]=="a@example.com"


def test_v8_subject_remains_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_receipt_dataflow_v3 as d
    import canonical.runtime.osworld_v21_workflow_policy_v5 as w
    import canonical.runtime.osworld_v21_brain_subject_v8 as s
    source=(inspect.getsource(d)+"\n"+inspect.getsource(w)+"\n"+inspect.getsource(s)).casefold()
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
