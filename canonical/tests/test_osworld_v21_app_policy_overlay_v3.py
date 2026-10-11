from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_app_policy_overlay_v3 import decide as app_decide
from canonical.runtime.osworld_v21_workflow_policy_v3 import decide
from canonical.runtime.osworld_v21_brain_subject_v6 import SUBJECT_ID, build_subject

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"

def a11y(app):
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="{app}">'
        f'<frame s:active="true" s:visible="true" s:showing="true" '
        f'c:screencoord="(0, 0)" c:size="(800, 600)" /></application></root>'
    )

def state(instruction,app,history=None):
    return {
        "instruction":instruction,"a11y_tree":a11y(app),
        "history":list(history or []),"screenshot_sha256":"s0","ocr":None,
    }

def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]

def test_writer_case_transform_routes():
    out=action(app_decide(state('Change "Alpha Beta" to uppercase.',"LibreOffice Writer")))
    assert out=={
        "type":"APP_OP","app":"libreoffice_writer","operation":"change_text_case",
        "args":{"case_type":"uppercase","pattern":"Alpha\\ Beta"},
    }

def test_calc_freeze_number_format_and_autofit_route():
    out=action(app_decide(state("Freeze 2 rows and 1 columns.","LibreOffice Calc")))
    assert out["operation"]=="freeze_panes"
    assert out["args"]=={"rows":2,"columns":1}

    out=action(app_decide(state("Format A2:A20 as percentage format with 2 decimal places.","LibreOffice Calc")))
    assert out["operation"]=="set_number_format"
    assert out["args"]=={"range_str":"A2:A20","format_type":"percentage","decimal_places":2}

    out=action(app_decide(state("Autofit columns A:C.","LibreOffice Calc")))
    assert out["operation"]=="adjust_column_width"
    assert out["args"]=={"columns":"A:C","autofit":True}

def test_calc_range_format_and_sheet_copy_route():
    out=action(app_decide(state("Make A1:C3 bold center.","LibreOffice Calc")))
    assert out["operation"]=="format_range"
    assert out["args"]=={"range_str":"A1:C3","bold":True,"alignment":"center"}

    out=action(app_decide(state('Copy sheet "Input" to "Input Copy".',"LibreOffice Calc")))
    assert out["operation"]=="copy_sheet"
    assert out["args"]=={"source_sheet":"Input","new_sheet_name":"Input Copy"}

def test_impress_structured_transform_routes():
    out=action(app_decide(state("Set the font on slide 2 to Arial.","LibreOffice Impress")))
    assert out["operation"]=="set_slide_font"
    assert out["args"]=={"slide_index":2,"font_name":"Arial"}

    out=action(app_decide(state("Position box 1 on slide 3 at top-right.","LibreOffice Impress")))
    assert out["operation"]=="position_box"
    assert out["args"]=={"slide_index":3,"box_index":1,"position":"top-right"}

    out=action(app_decide(state("Set the text color of box 2 on slide 4 to blue.","LibreOffice Impress")))
    assert out["operation"]=="set_text_color"
    assert out["args"]=={"slide_index":4,"box_index":2,"color":"blue"}

def test_impress_slide_background_and_export_route():
    out=action(app_decide(state("Set slide 2 background to #112233.","LibreOffice Impress")))
    assert out["operation"]=="set_slide_background"
    assert out["args"]=={"slide_index":2,"color":"#112233"}

    out=action(app_decide(state('Export slide 2 to "/home/oai/share/slide2.png" as png.',"LibreOffice Impress")))
    assert out["operation"]=="export_to_image"
    assert out["args"]=={
        "file_path":"/home/oai/share/slide2.png","format":"png","slide_index":2
    }

def app_receipt(out):
    a=out["actions"][0]
    return {
        "screenshot_sha256":"s0","actions":["WAIT"],
        "policy_receipt":out["_policy_receipt"],
        "submitted_operation":{"app":a["app"],"operation":a["operation"],"args":a["args"]},
        "app_result":{"type":"APP_OP","ok":True,"app":a["app"],"operation":a["operation"],"status":"success","output":"ok"},
    }

def test_semantic_workflow_composes_two_calc_transforms():
    instruction="Freeze 1 rows and autofit columns A:C"
    first=decide(state(instruction,"LibreOffice Calc"))
    assert action(first)["operation"]=="freeze_panes"
    assert first["_policy_receipt"]["semantic_decomposition"]["clause_count"]==2
    h1=app_receipt(first)

    second=decide(state(instruction,"LibreOffice Calc",[h1]))
    assert action(second)["operation"]=="adjust_column_width"
    h2=app_receipt(second)

    third=decide(state(instruction,"LibreOffice Calc",[h1,h2]))
    assert third["actions"]==[{"type":"DONE"}]

def test_v6_subject_remains_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_app_policy_overlay_v3 as a
    import canonical.runtime.osworld_v21_brain_subject_v6 as s
    source=(inspect.getsource(a)+"\n"+inspect.getsource(s)).casefold()
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
