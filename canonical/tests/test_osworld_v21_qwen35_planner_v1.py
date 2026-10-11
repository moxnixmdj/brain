from canonical.runtime.osworld_v21_qwen35_planner_v1 import _extract_object, _prompt


def test_extracts_first_action_object_from_noisy_model_output():
    out = _extract_object('thinking... {"response":"x","actions":[{"type":"WAIT"}]} trailing')
    assert out["actions"][0]["type"] == "WAIT"


def test_prompt_excludes_screenshot_bytes_and_preserves_live_browser_state():
    state = {
        "instruction": "Open the settings page",
        "screenshot_bytes": b"secret-image",
        "browser_state": {
            "page_count": 1,
            "pages": [{
                "page_index": 0,
                "url": "https://example.test/",
                "title": "Example",
                "elements": [{"i": 0, "tag": "button", "text": "Settings"}],
            }],
        },
        "history": [],
    }
    prompt = _prompt(state)
    assert "secret-image" not in prompt
    assert "https://example.test/" in prompt
    assert "Settings" in prompt
    assert "benchmark source paths" in prompt


def test_prompt_never_includes_task_or_evaluator_source_fields():
    state = {
        "instruction": "Do the task",
        "browser_state": {"page_count": 0, "pages": []},
        "history": [],
        "task_source_path": "/evaluation_examples/task_class/task_001.py",
        "expected_answer": "hidden",
    }
    prompt = _prompt(state)
    assert "/evaluation_examples/task_class/task_001.py" not in prompt
    assert '"expected_answer":"hidden"' not in prompt
