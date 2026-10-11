from __future__ import annotations

import inspect
import json

from canonical.runtime.osworld_v21_app_policy_overlay_v5 import decide as app_decide
from canonical.runtime.osworld_v21_host_app_ops_v1 import AppOpsError, OSWorldHostAppOps
from canonical.runtime.osworld_v21_workflow_policy_v5 import decide
from canonical.runtime.osworld_v21_brain_subject_v9 import SUBJECT_ID, build_subject

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

def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]

def test_explicit_and_template_formula_routes():
    out=action(app_decide(state("Set formula in C2 to =SUM(A2:B2).")))
    assert out=={
        "type":"APP_OP","app":"libreoffice_calc",
        "operation":"set_cell_formula_verified",
        "args":{"cell":"C2","formula":"=SUM(A2:B2)"},
    }

    out=action(app_decide(state("Set D4 to average B4:C4.")))
    assert out["operation"]=="set_cell_formula_verified"
    assert out["args"]=={"cell":"D4","formula":"=AVERAGE(B4:C4)"}

def test_unsupported_formula_request_fails_closed():
    out=app_decide(state("Set formula in C2 to the clever formula that fits the data."))
    assert out["actions"]==[{"type":"WAIT"}]
    assert out["_policy_receipt"]["route"]=="FORMULA_REQUEST_FAIL_CLOSED"

class FakeController:
    def __init__(self,output=None):
        self.programs=[]
        self.output=output
    def execute_python_command(self,program):
        self.programs.append(program)
        if self.output is not None:
            return {"status":"success","output":self.output}
        return {"status":"success","output":json.dumps({
            "result":{"cell":"C2","formula":"=SUM(A2:B2)","value":7.0}
        })}

class FakeEnv:
    vm_screen_size=(1920,1080)
    def __init__(self,controller):
        self.controller=controller

def test_formula_host_program_is_fixed_and_contains_readback_guard():
    ctl=FakeController()
    app=OSWorldHostAppOps()
    app.bind_environment(FakeEnv(ctl))
    out=app.run({
        "app":"libreoffice_calc","operation":"set_cell_formula_verified",
        "args":{"cell":"C2","formula":"=SUM(A2:B2)"},
    })
    program=ctl.programs[-1]
    assert "_c.Formula=_a['formula']" in program
    assert "_actual=_c.Formula" in program
    assert "_actual==_a['formula']" in program
    assert out["result"]["formula"]=="=SUM(A2:B2)"

def test_formula_input_is_data_not_python_source():
    ctl=FakeController(json.dumps({
        "result":{"cell":"C2","formula":"=IF(A1=\"x\",1,0)","value":1.0}
    }))
    app=OSWorldHostAppOps()
    app.bind_environment(FakeEnv(ctl))
    formula='=IF(A1="x",1,0)'
    app.run({
        "app":"libreoffice_calc","operation":"set_cell_formula_verified",
        "args":{"cell":"C2","formula":formula},
    })
    program=ctl.programs[-1]
    assert "_a=json.loads(" in program
    encoded=json.dumps({"cell":"C2","formula":formula},ensure_ascii=False,separators=(",",":"))
    assert repr(encoded) in program

def test_invalid_formula_and_cell_fail_before_execution():
    ctl=FakeController()
    app=OSWorldHostAppOps()
    app.bind_environment(FakeEnv(ctl))
    for args,reason in (
        ({"cell":"../../x","formula":"=SUM(A1:A2)"},"FORMULA_CELL_INVALID"),
        ({"cell":"C2","formula":"SUM(A1:A2)"},"FORMULA_INVALID"),
    ):
        try:
            app.run({"app":"libreoffice_calc","operation":"set_cell_formula_verified","args":args})
        except AppOpsError as exc:
            assert str(exc)==reason
        else:
            raise AssertionError("expected formula validation failure")
    assert ctl.programs==[]

def app_receipt(out):
    a=out["actions"][0]
    return {
        "screenshot_sha256":"s0","actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operation":{"app":a["app"],"operation":a["operation"],"args":a["args"]},
        "app_result":{
            "type":"APP_OP","ok":True,"app":a["app"],"operation":a["operation"],
            "status":"success",
            "result":{"cell":a["args"]["cell"],"formula":a["args"]["formula"],"value":1.0},
        },
    }

def test_two_formula_steps_compose_without_repeat():
    instruction=(
        "Set formula in C2 to =SUM(A2:B2); "
        "then set formula in C3 to =AVERAGE(A3:B3)"
    )
    first=decide(state(instruction))
    assert action(first)["args"]=={"cell":"C2","formula":"=SUM(A2:B2)"}
    h1=app_receipt(first)

    second=decide(state(instruction,[h1]))
    assert action(second)["args"]=={"cell":"C3","formula":"=AVERAGE(A3:B3)"}
    h2=app_receipt(second)

    third=decide(state(instruction,[h1,h2]))
    assert third["actions"]==[{"type":"DONE"}]

def test_v9_subject_remains_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_app_policy_overlay_v5 as p
    import canonical.runtime.osworld_v21_brain_subject_v9 as s
    source=(inspect.getsource(p)+"\n"+inspect.getsource(s)).casefold()
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
