from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.osworld_v21_app_policy_overlay_v2 import decide
from canonical.runtime.osworld_v21_brain_agent_adapter_v2 import BrainOSWorldAgentV2
from canonical.runtime.osworld_v21_host_app_ops_v1 import AppOpsError, OSWorldHostAppOps

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"


def a11y(app: str) -> str:
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}">'
        f'<application name="{app}"><frame s:active="true" '
        f's:visible="true" s:showing="true" c:screencoord="(0, 0)" c:size="(800, 600)" />'
        f'</application></root>'
    )


def state(instruction: str, app: str):
    return {
        "instruction": instruction,
        "a11y_tree": a11y(app),
        "history": [],
        "screenshot_sha256": "a"*64,
    }


def action(out):
    assert len(out["actions"]) == 1
    return out["actions"][0]


def test_overlay_writer_routes_high_confidence_commands():
    assert action(decide(state("Export this document to PDF.", "LibreOffice Writer"))) == {
        "type":"APP_OP","app":"libreoffice_writer","operation":"export_to_pdf","args":{}
    }
    assert action(decide(state("Set line spacing to 2.0.", "LibreOffice Writer")))["args"] == {
        "spacing_value": 2.0
    }
    out=action(decide(state('Replace "alpha" with "beta".', "LibreOffice Writer")))
    assert out["operation"]=="find_and_replace"
    assert out["args"]=={"pattern":"alpha","replacement":"beta"}


def test_overlay_calc_routes_high_confidence_commands():
    out=action(decide(state("Merge cells A1:B4.", "LibreOffice Calc")))
    assert out=={"type":"APP_OP","app":"libreoffice_calc","operation":"merge_cells","args":{"range_str":"A1:B4"}}

    out=action(decide(state('Rename sheet "Old" to "New".', "LibreOffice Calc")))
    assert out["operation"]=="rename_sheet"
    assert out["args"]=={"old_name":"Old","new_name":"New"}

    out=action(decide(state("Transpose A1:B3 to D1.", "LibreOffice Calc")))
    assert out["operation"]=="transpose_range"
    assert out["args"]=={"source_range":"A1:B3","target_cell":"D1"}


def test_overlay_impress_code_vlc_routes():
    out=action(decide(state("Duplicate slide 3.", "LibreOffice Impress")))
    assert out["operation"]=="duplicate_slide" and out["args"]["slide_index"]==3

    out=action(decide(state("Install extension ms-python.python.", "Visual Studio Code")))
    assert out["operation"]=="install_extension"
    assert out["args"]["extension_id"]=="ms-python.python"

    out=action(decide(state("Pause the video.", "VLC media player")))
    assert out["operation"]=="pause"


def test_overlay_does_not_route_app_op_for_wrong_active_app():
    out=decide(state("Export this document to PDF.", "GIMP"))
    assert all(x.get("type")!="APP_OP" for x in out.get("actions",[]) if isinstance(x,dict))


class FakeController:
    def __init__(self, result=None):
        self.result=result or {"status":"success","output":"ok"}
        self.programs=[]
    def execute_python_command(self, program):
        self.programs.append(program)
        return dict(self.result)


class FakeEnv:
    vm_screen_size=(1920,1080)
    def __init__(self):
        self.controller=FakeController()


def test_app_executor_rejects_unknown_and_protected_paths():
    app=OSWorldHostAppOps()
    app.bind_environment(FakeEnv())
    try:
        app.run({"app":"libreoffice_writer","operation":"definitely_not_allowed","args":{}})
    except AppOpsError as exc:
        assert str(exc).startswith("APP_OPERATION_NOT_ALLOWED")
    else:
        raise AssertionError("expected unknown operation rejection")

    try:
        app.run({
            "app":"libreoffice_impress","operation":"insert_image",
            "args":{"slide_index":1,"image_path":"/evaluation_examples/secret.png"},
        })
    except AppOpsError as exc:
        assert str(exc)=="APP_OP_PROTECTED_PATH"
    else:
        raise AssertionError("expected protected path rejection")


def test_app_executor_arguments_remain_json_data():
    env=FakeEnv()
    app=OSWorldHostAppOps()
    app.bind_environment(env)
    payload="x'); __import__('os').system('false'); ('"
    receipt=app.run({
        "app":"libreoffice_calc","operation":"set_cell_value",
        "args":{"cell":"A1","value":payload},
    })
    assert receipt["ok"] is True
    program=env.controller.programs[-1]
    assert "_a=json.loads(" in program
    encoded=json.dumps({"cell":"A1","value":payload},ensure_ascii=False,separators=(",",":"))
    assert repr(encoded) in program


class FakeAppController:
    def __init__(self):
        self.bound=False
        self.calls=[]
    def bind_environment(self, environment):
        self.bound=True
    def run(self, payload):
        self.calls.append(dict(payload))
        return {"type":"APP_OP","ok":True,"app":payload["app"],"operation":payload["operation"],"status":"success","output":"ok"}


class FakeBrowser:
    def bind_environment(self, environment):
        pass


class FakeGuest:
    def bind_environment(self, environment):
        pass


def test_adapter_v2_executes_app_op_once_and_returns_wait():
    fake=FakeAppController()
    def policy(_state):
        return {
            "response":"do it",
            "actions":[{"type":"APP_OP","app":"vlc","operation":"pause","args":{}}],
        }
    agent=BrainOSWorldAgentV2(
        policy, policy_id="test",
        browser_controller=FakeBrowser(), guest_controller=FakeGuest(),
        app_controller=fake, ocr_provider=None,
    )
    env=FakeEnv()
    agent.bind_environment(env)
    response,actions=agent.predict("Pause the video.",{"screenshot":b"png"})
    assert response=="do it"
    assert actions==["WAIT"]
    assert fake.calls==[{"app":"vlc","operation":"pause","args":{}}]


def test_calc_unquoted_value_drops_sentence_punctuation():
    out=action(decide(state("Set A1 to 42.", "LibreOffice Calc")))
    assert out["operation"]=="set_cell_value"
    assert out["args"]=={"cell":"A1","value":"42"}


def test_successful_identical_app_operation_becomes_completion_evidence():
    s = state("Pause the video.", "VLC media player")
    first = decide(s)
    op = action(first)
    s2 = state("Pause the video.", "VLC media player")
    s2["history"] = [{
        "submitted_operation": {
            "app": op["app"],
            "operation": op["operation"],
            "args": op["args"],
        },
        "app_result": {
            "type": "APP_OP",
            "ok": True,
            "app": op["app"],
            "operation": op["operation"],
            "status": "success",
            "output": "ok",
        },
    }]
    second = decide(s2)
    assert second["actions"] == [{"type": "DONE"}]
    assert second["_policy_receipt"]["route"] == "GENERIC_APP_OPERATION_VERIFIED_V2"


def test_different_app_operation_receipt_does_not_false_complete():
    s = state("Pause the video.", "VLC media player")
    s["history"] = [{
        "submitted_operation": {"app": "vlc", "operation": "play", "args": {}},
        "app_result": {"type": "APP_OP", "ok": True, "app": "vlc", "operation": "play"},
    }]
    out = decide(s)
    assert action(out)["operation"] == "pause"
