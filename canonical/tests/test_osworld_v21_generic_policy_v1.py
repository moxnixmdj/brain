from pathlib import Path

from canonical.runtime.osworld_v21_generic_policy_v1 import decide


STATE_NS = "https://accessibility.ubuntu.example.org/ns/state"
COMP_NS = "https://accessibility.ubuntu.example.org/ns/component"


def _state(instruction, *, a11y=None, ocr=None, history=None, screenshot="a"):
    return {
        "instruction": instruction,
        "a11y_tree": a11y,
        "ocr": ocr,
        "history": history or [],
        "screenshot_sha256": screenshot,
    }


def _a11y_button(label, x=100, y=100, w=80, h=30):
    return (
        f'<root xmlns:st="{STATE_NS}" xmlns:cp="{COMP_NS}">'
        f'<button name="{label}" st:visible="true" st:showing="true" '
        f'cp:screencoord="({x}, {y})" cp:size="({w}, {h})" />'
        f'</root>'
    )


def _ocr(items, w=800, h=600):
    return {
        "page_width": w,
        "page_height": h,
        "text_items": items,
    }


def _item(text, x0, y0, x1, y1, sid):
    return {
        "text": text,
        "source_id": sid,
        "box": {
            "x0": x0,
            "y0": y0,
            "x1_exclusive": x1,
            "y1_exclusive": y1,
        },
    }


def test_explicit_url_uses_host_browser_navigation():
    out = decide(_state("Open https://example.com/docs"))
    assert out["actions"] == [{
        "type": "BROWSER_OP",
        "op": {"type": "NAVIGATE", "url": "https://example.com/docs"},
    }]


def test_unique_a11y_button_clicks_center():
    out = decide(_state("Click the Save button", a11y=_a11y_button("Save", 100, 200, 80, 40)))
    assert out["actions"] == [{"type": "CLICK", "x": 140, "y": 220}]


def test_unique_ocr_exact_target_is_fallback():
    out = decide(_state(
        'Click "Save"',
        a11y=None,
        ocr=_ocr([_item("Save", 20, 40, 80, 60, "save")]),
    ))
    assert out["actions"] == [{"type": "CLICK", "x": 49, "y": 49}]


def test_duplicate_ocr_target_never_guesses():
    out = decide(_state(
        'Click "OK"',
        a11y=None,
        ocr=_ocr([
            _item("OK", 10, 10, 40, 30, "a"),
            _item("OK", 200, 200, 240, 220, "b"),
        ]),
    ))
    assert out["actions"] == [{"type": "WAIT"}]


def test_unquoted_button_suffix_is_stripped_for_ocr_grounding():
    out = decide(_state(
        "Press the Apply button.",
        a11y=None,
        ocr=_ocr([_item("Apply", 100, 100, 180, 140, "apply")]),
    ))
    assert out["actions"] == [{"type": "CLICK", "x": 139, "y": 119}]


def test_unchanged_state_does_not_repeat_action():
    history = [{"screenshot_sha256": "same", "actions": ["something"]}]
    out = decide(_state(
        "Click Save",
        a11y=_a11y_button("Save"),
        history=history,
        screenshot="same",
    ))
    assert out["actions"] == [{"type": "WAIT"}]


def test_no_task_specific_or_model_producer_markers_in_policy_source():
    src = Path(__file__).parents[1] / "runtime" / "osworld_v21_generic_policy_v1.py"
    text = src.read_text(encoding="utf-8").lower()
    forbidden = (
        "task_001",
        "task_108",
        "reference trajectory",
        "reference_trajectory",
        "anthropic",
        "openai",
        "qwen",
        "llama.cpp",
        "ollama",
    )
    for token in forbidden:
        assert token not in text


def _browser_receipt(submitted, result, screenshot="old"):
    return {
        "screenshot_sha256": screenshot,
        "actions": ["WAIT"],
        "submitted_operation": submitted,
        "browser_result": result,
    }


def test_simple_url_workflow_navigate_observe_done():
    instruction = "Open https://example.com/docs"

    first = decide(_state(instruction, screenshot="s0"))
    assert first["actions"][0]["op"]["type"] == "NAVIGATE"

    nav = _browser_receipt(
        {"type": "NAVIGATE", "url": "https://example.com/docs"},
        {"type": "NAVIGATE", "url": "https://example.com/docs"},
        screenshot="s0",
    )
    second = decide(_state(instruction, history=[nav], screenshot="s1"))
    assert second["actions"] == [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}]

    obs = _browser_receipt(
        {"type": "OBSERVE"},
        {
            "type": "OBSERVE",
            "active_url": "https://example.com/docs",
            "visible_text": "Documentation",
            "controls": [],
        },
        screenshot="s1",
    )
    third = decide(_state(instruction, history=[nav, obs], screenshot="s1"))
    assert third["actions"] == [{"type": "DONE"}]


def test_generic_search_workflow_observe_fill_press_observe_done():
    instruction = "On the website, search for cats"

    first = decide(_state(instruction, screenshot="s0"))
    assert first["actions"] == [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}]

    observed = _browser_receipt(
        {"type": "OBSERVE"},
        {
            "type": "OBSERVE",
            "active_url": "https://example.test/",
            "visible_text": "Search",
            "controls": [
                {
                    "tag": "input",
                    "role": "searchbox",
                    "type": "search",
                    "placeholder": "Search",
                    "text": "",
                }
            ],
        },
        screenshot="s0",
    )
    second = decide(_state(instruction, history=[observed], screenshot="s0"))
    assert second["actions"] == [{
        "type": "BROWSER_OP",
        "op": {
            "type": "FILL_PLACEHOLDER",
            "placeholder": "Search",
            "value": "cats",
            "exact": True,
        },
    }]

    filled = _browser_receipt(
        {
            "type": "FILL_PLACEHOLDER",
            "placeholder": "Search",
            "value": "cats",
            "exact": True,
        },
        {"type": "FILL_PLACEHOLDER", "placeholder": "Search", "url": "https://example.test/"},
        screenshot="s0",
    )
    third = decide(_state(instruction, history=[observed, filled], screenshot="s1"))
    assert third["actions"] == [{"type": "BROWSER_OP", "op": {"type": "PRESS", "key": "Enter"}}]

    pressed = _browser_receipt(
        {"type": "PRESS", "key": "Enter"},
        {"type": "PRESS", "key": "Enter", "url": "https://example.test/?q=cats"},
        screenshot="s1",
    )
    fourth = decide(_state(instruction, history=[observed, filled, pressed], screenshot="s2"))
    assert fourth["actions"] == [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}]

    post = _browser_receipt(
        {"type": "OBSERVE"},
        {
            "type": "OBSERVE",
            "active_url": "https://example.test/?q=cats",
            "visible_text": "Results for cats",
            "controls": [],
        },
        screenshot="s2",
    )
    fifth = decide(_state(instruction, history=[observed, filled, pressed, post], screenshot="s2"))
    assert fifth["actions"] == [{"type": "DONE"}]


def _guest_receipt(ops, output, screenshot="old"):
    return {
        "screenshot_sha256": screenshot,
        "actions": ["WAIT"],
        "submitted_operations": ops,
        "guest_result": {"type": "STATE_OPS", "ok": True, "status": "ok", "output": output},
    }


def test_create_explicit_text_file_write_verify_done():
    instruction = 'Create "notes.txt" containing "hello world"'
    first = decide(_state(instruction, screenshot="s0"))
    assert first["actions"] == [{
        "type": "STATE_OPS",
        "ops": [
            {"type": "WRITE_TEXT", "path": "/home/oai/share/notes.txt", "text": "hello world"},
            {"type": "ASSERT_TEXT_EQUALS", "path": "/home/oai/share/notes.txt", "text": "hello world"},
        ],
    }]

    verified = _guest_receipt(
        first["actions"][0]["ops"],
        "WRITE_TEXT:PASS:/home/oai/share/notes.txt:chars=11\n"
        "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/notes.txt",
        screenshot="s0",
    )
    second = decide(_state(instruction, history=[verified], screenshot="s0"))
    assert second["actions"] == [{"type": "DONE"}]


def test_replace_existing_text_file_discover_replace_verify_done():
    instruction = 'Replace "alpha" with "omega" in notes.txt'

    first = decide(_state(instruction, screenshot="s0"))
    assert first["actions"] == [{
        "type": "STATE_OPS",
        "ops": [{"type": "LIST_DIR", "path": "/home/oai/share", "max_entries": 200}],
    }]

    listing_output = (
        'LIST_DIR:PASS:/home/oai/share:'
        '[{"name":"notes.txt","path":"/home/oai/share/notes.txt",'
        '"is_file":true,"is_dir":false,"size":20}]'
    )
    listed = _guest_receipt(first["actions"][0]["ops"], listing_output, screenshot="s0")
    second = decide(_state(instruction, history=[listed], screenshot="s0"))
    assert second["actions"] == [{
        "type": "STATE_OPS",
        "ops": [
            {
                "type": "TEXT_REPLACE",
                "path": "/home/oai/share/notes.txt",
                "old": "alpha",
                "new": "omega",
                "replace_all": True,
            },
            {
                "type": "ASSERT_TEXT_CONTAINS",
                "path": "/home/oai/share/notes.txt",
                "text": "omega",
            },
        ],
    }]

    verified = _guest_receipt(
        second["actions"][0]["ops"],
        "TEXT_REPLACE:PASS:/home/oai/share/notes.txt:chars=20\n"
        "ASSERT_TEXT_CONTAINS:PASS:/home/oai/share/notes.txt",
        screenshot="s0",
    )
    third = decide(_state(instruction, history=[listed, verified], screenshot="s0"))
    assert third["actions"] == [{"type": "DONE"}]


def test_create_file_without_explicit_content_does_not_invent_data():
    out = decide(_state("Create notes.txt with the appropriate content", screenshot="s0"))
    assert out["actions"] == [{"type": "WAIT"}]
