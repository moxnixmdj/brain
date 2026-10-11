from __future__ import annotations
import inspect
from canonical.runtime.osworld_v21_app_policy_overlay_v4 import decide
from canonical.runtime.osworld_v21_brain_subject_v7 import SUBJECT_ID, build_subject

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"

def a11y(app):
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="{app}">'
        f'<frame s:active="true" s:visible="true" s:showing="true" '
        f'c:screencoord="(0, 0)" c:size="(800, 600)" /></application></root>'
    )

def state(instruction,app="LibreOffice Calc"):
    return {"instruction":instruction,"a11y_tree":a11y(app),"history":[],"screenshot_sha256":"s0","ocr":None}

def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]

def test_calc_observation_and_advanced_routes():
    assert action(decide(state("Check workbook info.")))["operation"]=="get_workbook_info"
    out=action(decide(state("Read column C.")))
    assert out["operation"]=="get_column_data" and out["args"]=={"column_name":"C"}
    out=action(decide(state('Set validation list for column B to "Open", "Closed".')))
    assert out["operation"]=="set_validation_list"
    assert out["args"]=={"column_name":"B","values":["Open","Closed"]}
    out=action(decide(state("Reorder columns to A, C, B.")))
    assert out["operation"]=="reorder_columns"
    assert out["args"]=={"column_order":["A","C","B"]}

def test_calc_chart_pivot_and_column_values():
    out=action(decide(state('Create a line chart from A1:B10 titled "Revenue".')))
    assert out["operation"]=="create_chart"
    assert out["args"]=={"chart_type":"line","data_range":"A1:B10","title":"Revenue"}
    out=action(decide(state('Set column D values to ["x", "y", 3] starting at row 2.')))
    assert out["operation"]=="set_column_values"
    assert out["args"]=={"column_name":"D","data":["x","y",3],"start_index":2}
    out=action(decide(state('Create pivot table "Summary" from sheet "Data" with value fields C,D at A1 using sum.')))
    assert out["operation"]=="create_pivot_table"
    assert out["args"]["source_sheet"]=="Data"
    assert out["args"]["table_name"]=="Summary"
    assert out["args"]["value_fields"]==["C","D"]
    assert out["args"]["target_cell"]=="A1"
    assert out["args"]["aggregation_function"]=="sum"

def test_impress_slide_count_observation():
    out=action(decide(state("How many slides are in this presentation?","LibreOffice Impress")))
    assert out=={"type":"APP_OP","app":"libreoffice_impress","operation":"get_slide_count","args":{}}

def test_v7_subject_is_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_app_policy_overlay_v4 as a
    import canonical.runtime.osworld_v21_brain_subject_v7 as s
    source=(inspect.getsource(a)+"\n"+inspect.getsource(s)).casefold()
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
