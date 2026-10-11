from __future__ import annotations
import json

from canonical.runtime.osworld_v21_host_app_ops_v1 import OSWorldHostAppOps
from canonical.runtime.osworld_v21_workflow_policy_v3 import decide

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"

def a11y():
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="LibreOffice Calc">'
        f'<frame s:active="true" s:visible="true" s:showing="true" '
        f'c:screencoord="(0, 0)" c:size="(800, 600)" /></application></root>'
    )

def state(instruction,history=None):
    return {
        "instruction":instruction,"a11y_tree":a11y(),
        "history":list(history or []),"screenshot_sha256":"s0","ocr":None,
    }

class FakeController:
    def execute_python_command(self,program):
        return {
            "status":"success",
            "output":json.dumps({"result":{"active_sheet":"Sheet1","sheets":["Sheet1","Data"]}}),
        }

class FakeEnv:
    vm_screen_size=(1920,1080)
    controller=FakeController()

def test_native_app_output_is_preserved_as_structured_result():
    app=OSWorldHostAppOps()
    app.bind_environment(FakeEnv())
    out=app.run({"app":"libreoffice_calc","operation":"get_workbook_info","args":{}})
    assert out["ok"] is True
    assert out["result"]=={"active_sheet":"Sheet1","sheets":["Sheet1","Data"]}

def app_receipt(out,result):
    a=out["actions"][0]
    return {
        "screenshot_sha256":"s0",
        "actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operation":{"app":a["app"],"operation":a["operation"],"args":a["args"]},
        "app_result":{
            "type":"APP_OP","ok":True,"app":a["app"],"operation":a["operation"],
            "status":"success","output":json.dumps({"result":result}),"result":result,
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

def test_structured_app_fact_flows_into_later_file_action():
    instruction=(
        'Check workbook info; then create "active.txt" containing '
        'the active_sheet from the previous step'
    )
    first=decide(state(instruction))
    assert first["actions"][0]["operation"]=="get_workbook_info"
    h1=app_receipt(first,{"active_sheet":"Sheet1","sheets":["Sheet1","Data"]})

    second=decide(state(instruction,[h1]))
    assert second["_policy_receipt"]["dataflow"]["pass"] is True
    assert second["_policy_receipt"]["dataflow"]["bindings"][0]["value"]=="Sheet1"
    assert second["actions"][0]["type"]=="STATE_OPS"
    assert second["actions"][0]["ops"][0]["text"]=="Sheet1"

    h2=guest_receipt(second,"/home/oai/share/active.txt","Sheet1")
    third=decide(state(instruction,[h1,h2]))
    assert third["actions"]==[{"type":"DONE"}]
