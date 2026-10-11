from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_workflow_policy_v1 import (
    SCHEMA,
    decide,
    split_explicit_subgoals,
)


def _state(instruction: str, history=None):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "screenshot_sha256": "s0",
        "a11y_tree": None,
        "ocr": None,
    }


def _guest_success(out, path: str, text: str):
    action = out["actions"][0]
    assert action["type"] == "STATE_OPS"
    return {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_operations": action["ops"],
        "guest_result": {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": (
                f"WRITE_TEXT:PASS:{path}:chars={len(text)}\n"
                f"ASSERT_TEXT_EQUALS:PASS:{path}"
            ),
        },
    }


def test_split_explicit_ordered_subgoals_without_splitting_quoted_semicolons():
    instruction = (
        'Create "a;b.txt" containing "alpha; beta"; '
        'then create "c.txt" containing "gamma"'
    )
    parts = split_explicit_subgoals(instruction)
    assert parts == [
        'Create "a;b.txt" containing "alpha; beta"',
        'create "c.txt" containing "gamma"',
    ]


def test_ordinary_conjunction_is_not_invented_as_workflow_boundary():
    instruction = 'Find and replace "alpha" with "beta" in notes.txt'
    assert split_explicit_subgoals(instruction) == [instruction]


def test_numbered_lines_are_explicit_subgoals():
    instruction = '1. Create "a.txt" containing "alpha"\n2. Create "b.txt" containing "beta"'
    assert split_explicit_subgoals(instruction) == [
        'Create "a.txt" containing "alpha"',
        'Create "b.txt" containing "beta"',
    ]


def test_two_file_subgoals_advance_only_after_verified_postcondition():
    instruction = (
        'Create "a.txt" containing "alpha"; '
        'then create "b.txt" containing "beta"'
    )

    first = decide(_state(instruction))
    assert first["actions"][0]["type"] == "STATE_OPS"
    assert first["actions"][0]["ops"][0] == {
        "type": "WRITE_TEXT",
        "path": "/home/oai/share/a.txt",
        "text": "alpha",
    }
    assert first["_policy_receipt"]["schema"] == SCHEMA
    assert first["_policy_receipt"]["clause_index"] == 0
    assert first["_policy_receipt"]["clause_count"] == 2

    h1 = _guest_success(first, "/home/oai/share/a.txt", "alpha")
    second = decide(_state(instruction, [h1]))
    assert second["actions"][0]["type"] == "STATE_OPS"
    assert second["actions"][0]["ops"][0] == {
        "type": "WRITE_TEXT",
        "path": "/home/oai/share/b.txt",
        "text": "beta",
    }
    assert second["_policy_receipt"]["clause_index"] == 1

    h2 = _guest_success(second, "/home/oai/share/b.txt", "beta")
    third = decide(_state(instruction, [h1, h2]))
    assert third["actions"] == [{"type": "DONE"}]
    assert third["_policy_receipt"]["clause_index"] == 1


def test_failed_or_unverified_first_clause_does_not_advance():
    instruction = (
        'Create "a.txt" containing "alpha"; '
        'then create "b.txt" containing "beta"'
    )
    first = decide(_state(instruction))
    pending = {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": first["_policy_receipt"],
        "submitted_operations": first["actions"][0]["ops"],
        "guest_result": {
            "type": "STATE_OPS",
            "ok": True,
            "status": "ok",
            "output": "WRITE_TEXT:PASS:/home/oai/share/a.txt:chars=5",
        },
    }
    again = decide(_state(instruction, [pending]))
    assert again["_policy_receipt"]["clause_index"] == 0
    assert again["actions"][0]["type"] == "STATE_OPS"


def test_excessive_clause_count_fails_closed_to_whole_goal():
    instruction = "; ".join(f"Step {i}" for i in range(20))
    assert split_explicit_subgoals(instruction) == [instruction]


def test_workflow_policy_source_has_no_benchmark_or_model_runtime_dependency():
    import canonical.runtime.osworld_v21_workflow_policy_v1 as mod

    source = inspect.getsource(mod).casefold()
    for forbidden in (
        "task_001",
        "reference_trajectory",
        "expected_answer",
        "openai",
        "anthropic",
        "qwen",
        "gemini",
    ):
        assert forbidden not in source


def _web_app_receipt(out, result):
    action = out["actions"][0]
    assert action["type"] == "WEB_APP_OP"
    return {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_web_app_operation": {
            "app": action["app"],
            "operation": action["operation"],
            "args": action["args"],
        },
        "web_app_result": {
            "type": "WEB_APP_OP",
            "ok": True,
            "app": action["app"],
            "operation": action["operation"],
            "result": result,
        },
    }


def test_observe_then_use_unique_receipted_scalar_in_later_file_clause():
    instruction = (
        'Check Mailhub; then create "sender.txt" containing '
        'the sender from the previous step'
    )

    first = decide(_state(instruction))
    assert first["actions"] == [{
        "type": "WEB_APP_OP",
        "app": "mailhub",
        "operation": "observe_mail",
        "args": {},
    }]
    h1 = _web_app_receipt(first, {
        "messages": [{"subject": "Hello", "sender": "alice@example.com"}]
    })

    second = decide(_state(instruction, [h1]))
    assert second["_policy_receipt"]["clause_index"] == 1
    assert second["_policy_receipt"]["dataflow"]["pass"] is True
    assert second["_policy_receipt"]["dataflow"]["bindings"][0]["field"] == "sender"
    assert second["actions"][0]["type"] == "STATE_OPS"
    assert second["actions"][0]["ops"][0] == {
        "type": "WRITE_TEXT",
        "path": "/home/oai/share/sender.txt",
        "text": "alice@example.com",
    }

    h2 = _guest_success(second, "/home/oai/share/sender.txt", "alice@example.com")
    third = decide(_state(instruction, [h1, h2]))
    assert third["actions"] == [{"type": "DONE"}]


def test_ambiguous_prior_scalar_blocks_later_clause_instead_of_guessing():
    instruction = (
        'Check Mailhub; then create "sender.txt" containing '
        'the sender from the previous step'
    )
    first = decide(_state(instruction))
    h1 = _web_app_receipt(first, {
        "messages": [
            {"sender": "alice@example.com"},
            {"sender": "bob@example.com"},
        ]
    })
    second = decide(_state(instruction, [h1]))
    assert second["actions"] == [{"type": "WAIT"}]
    flow = second["_policy_receipt"]["dataflow"]
    assert flow["pass"] is False
    assert flow["resolution"]["status"] == "OPEN__FIELD_AMBIGUOUS"


def test_observation_clause_with_mutation_verb_does_not_auto_advance():
    instruction = (
        'Check Mailhub and send a reply; then create "done.txt" containing "yes"'
    )
    first = decide(_state(instruction))
    assert first["_policy_receipt"]["clause_index"] == 0
    h1 = _web_app_receipt(first, {"messages": [{"sender": "alice@example.com"}]})
    second = decide(_state(instruction, [h1]))
    assert second["_policy_receipt"]["clause_index"] == 0
