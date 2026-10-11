from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_workflow_policy_v3 import (
    decide,
    split_capability_supported_subgoals,
)
from canonical.runtime.osworld_v21_brain_subject_v5 import SUBJECT_ID, build_subject


def _a11y(app_name: str):
    S="https://accessibility.ubuntu.example.org/ns/state"
    C="https://accessibility.ubuntu.example.org/ns/component"
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="{app_name}">'
        f'<frame s:active="true" s:visible="true" s:showing="true" '
        f'c:screencoord="(0, 0)" c:size="(800, 600)" /></application></root>'
    )


def _state(instruction: str, *, history=None, a11y=None):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "screenshot_sha256": "s0",
        "a11y_tree": a11y,
        "ocr": None,
    }


def test_writer_two_supported_constraints_semantically_split():
    state=_state(
        "Set line spacing to 1.5 and export to PDF",
        a11y=_a11y("LibreOffice Writer"),
    )
    parts=split_capability_supported_subgoals(state,state["instruction"])
    assert parts == ["Set line spacing to 1.5", "export to PDF"]


def test_find_and_replace_is_not_broken_on_ordinary_and():
    instruction='Find and replace "alpha" with "beta"'
    state=_state(instruction,a11y=_a11y("LibreOffice Writer"))
    assert split_capability_supported_subgoals(state,instruction) == [instruction]


def test_unsupported_second_clause_prevents_split():
    instruction="Set line spacing to 1.5 and contemplate the meaning of fonts"
    state=_state(instruction,a11y=_a11y("LibreOffice Writer"))
    assert split_capability_supported_subgoals(state,instruction) == [instruction]


def test_quoted_and_is_not_a_boundary():
    instruction='Create "sales and marketing.txt" containing "ready"'
    state=_state(instruction)
    assert split_capability_supported_subgoals(state,instruction) == [instruction]


def _guest_success(out,path,text):
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


def test_unordered_supported_file_constraints_execute_as_verified_workflow():
    instruction='Create "a.txt" containing "alpha" and create "b.txt" containing "beta"'
    first=decide(_state(instruction))
    assert first["actions"][0]["type"]=="STATE_OPS"
    assert first["actions"][0]["ops"][0]["path"]=="/home/oai/share/a.txt"
    assert first["_policy_receipt"]["semantic_decomposition"]["clause_count"]==2

    h1=_guest_success(first,"/home/oai/share/a.txt","alpha")
    second=decide(_state(instruction,history=[h1]))
    assert second["actions"][0]["ops"][0]["path"]=="/home/oai/share/b.txt"

    h2=_guest_success(second,"/home/oai/share/b.txt","beta")
    third=decide(_state(instruction,history=[h1,h2]))
    assert third["actions"]==[{"type":"DONE"}]


def test_v5_subject_stays_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_workflow_policy_v3 as p
    import canonical.runtime.osworld_v21_brain_subject_v5 as s
    source=(inspect.getsource(p)+"\n"+inspect.getsource(s)).casefold()
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
