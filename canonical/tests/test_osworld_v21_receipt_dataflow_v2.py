from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_receipt_dataflow_v2 import (
    materialize_explicit_references,
    resolve_named_scalar,
)
from canonical.runtime.osworld_v21_workflow_policy_v2 import decide, SCHEMA
from canonical.runtime.osworld_v21_brain_subject_v4 import SUBJECT_ID, build_subject


def _web(app, result):
    return {
        "web_app_result": {
            "type": "WEB_APP_OP", "ok": True, "app": app,
            "operation": "observe", "result": result,
        }
    }


def test_source_qualified_reference_ignores_same_field_from_other_app():
    rows = [
        _web("mailhub", {"sender": "alice@example.com"}),
        _web("teamchat", {"sender": "bob@example.com"}),
    ]
    out = materialize_explicit_references(
        'create "x.txt" containing the sender from Mailhub', rows
    )
    assert out["pass"] is True
    assert out["bindings"][0]["value"] == "alice@example.com"
    assert out["bindings"][0]["source_hint"] == "mailhub"


def test_unqualified_ambiguous_reference_fails_closed():
    rows = [
        _web("mailhub", {"sender": "alice@example.com"}),
        _web("teamchat", {"sender": "bob@example.com"}),
    ]
    out = materialize_explicit_references(
        'create "x.txt" containing the sender found earlier', rows
    )
    assert out["pass"] is False
    assert out["resolution"]["status"] == "OPEN__FIELD_AMBIGUOUS"


def test_sensitive_value_never_flows():
    rows = [_web("vaultbank", {"token": "secret-value"})]
    out = materialize_explicit_references(
        'create "x.txt" containing the token found earlier', rows
    )
    assert out["pass"] is False
    assert out["resolution"]["status"] == "FAIL_CLOSED__SENSITIVE_FIELD"


def test_duplicate_same_value_across_receipts_is_not_false_ambiguity():
    rows = [
        _web("mailhub", {"sender": "same@example.com"}),
        _web("mailhub", {"sender": "same@example.com"}),
    ]
    out = resolve_named_scalar(rows, "sender", source_hint="Mailhub")
    assert out["pass"] is True
    assert out["value"] == "same@example.com"
    assert len(out["provenance"]) == 2


def _state(instruction, history=None):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "screenshot_sha256": "s0",
        "a11y_tree": None,
        "ocr": None,
    }


def _web_receipt(out, app, result):
    action = out["actions"][0]
    return {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_web_app_operation": {
            "app": action["app"], "operation": action["operation"], "args": action["args"],
        },
        "web_app_result": {
            "type": "WEB_APP_OP", "ok": True, "app": app,
            "operation": action["operation"], "result": result,
        },
    }


def test_workflow_v2_uses_source_qualified_prior_fact():
    instruction = (
        'Check Mailhub; then create "sender.txt" containing '
        'the sender from Mailhub'
    )
    first = decide(_state(instruction))
    assert first["actions"][0]["type"] == "WEB_APP_OP"
    h1 = _web_receipt(first, "mailhub", {
        "messages": [{"sender": "alice@example.com"}]
    })
    second = decide(_state(instruction, [h1]))
    assert second["_policy_receipt"]["schema"] == SCHEMA
    assert second["_policy_receipt"]["clause_index"] == 1
    assert second["_policy_receipt"]["dataflow"]["pass"] is True
    assert second["actions"][0]["type"] == "STATE_OPS"
    assert second["actions"][0]["ops"][0]["text"] == "alice@example.com"


def test_v4_subject_is_model_independent_by_source_and_identity():
    subject = build_subject()
    assert subject.policy_id == SUBJECT_ID
    import canonical.runtime.osworld_v21_brain_subject_v4 as mod
    source = inspect.getsource(mod).casefold()
    for forbidden in ("openai", "anthropic", "gemini", "qwen", "reference_trajectory", "task_001"):
        assert forbidden not in source
