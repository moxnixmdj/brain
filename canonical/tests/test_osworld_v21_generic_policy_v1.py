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
