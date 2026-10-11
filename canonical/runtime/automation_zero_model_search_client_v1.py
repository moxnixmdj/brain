"""Stirrup-compatible zero-model Automation search client V1.

This stage performs deterministic workflow interpretation and endpoint discovery
only. It never emits api_fetch. That is intentional: mutation argument binding is
a separate capability stage and must fail closed until verified.
"""
from __future__ import annotations

import json
from typing import Any

from canonical.runtime.automation_zero_model_task_ir_v1 import compile_task_ir

MODEL_SLUG = "brain/zero-model-automation-search-v1"
CONTEXT_WINDOW_TOKENS = 32768


class ZeroModelAutomationSearchError(RuntimeError):
    pass


def _message_role(message: Any) -> str | None:
    role = getattr(message, "role", None)
    return role if isinstance(role, str) else None


def _message_content_text(message: Any) -> str | None:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    return None


def _latest_user_index(messages: list[Any]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if _message_role(messages[index]) == "user":
            return index
    raise ZeroModelAutomationSearchError("USER_MESSAGE_REQUIRED")


def next_search_action(messages: list[Any], tools: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(messages, list):
        raise ZeroModelAutomationSearchError("MESSAGES_LIST_REQUIRED")
    if not isinstance(tools, dict):
        raise ZeroModelAutomationSearchError("TOOLS_DICT_REQUIRED")
    if "api_search" not in tools:
        raise ZeroModelAutomationSearchError("API_SEARCH_TOOL_REQUIRED")

    user_index = _latest_user_index(messages)
    prompt = _message_content_text(messages[user_index])
    if not isinstance(prompt, str) or not prompt.strip():
        raise ZeroModelAutomationSearchError("STRING_USER_PROMPT_REQUIRED")

    ir = compile_task_ir(prompt)
    if ir.get("pass") is not True:
        raise ZeroModelAutomationSearchError(
            "TASK_IR_UNRESOLVED:" + str(ir.get("reason") or "UNKNOWN")
        )

    completed_searches = 0
    for message in messages[user_index + 1 :]:
        if _message_role(message) != "tool":
            continue
        if getattr(message, "name", None) != "api_search":
            continue
        if getattr(message, "success", False) is not True:
            raise ZeroModelAutomationSearchError("API_SEARCH_RESULT_FAILED")
        completed_searches += 1

    clauses = ir["clauses"]
    if completed_searches < len(clauses):
        clause = clauses[completed_searches]
        return {
            "kind": "tool_call",
            "name": "api_search",
            "arguments": {
                "query": clause["discovery_query"],
                "top_k": 5,
            },
            "clause_ordinal": clause["ordinal"],
            "model_role": "NONE",
            "model_dependency_count": 0,
        }

    return {
        "kind": "text",
        "text": "DISCOVERY_COMPLETE__ENDPOINT_BINDING_NOT_IMPLEMENTED_V1",
        "model_role": "NONE",
        "model_dependency_count": 0,
    }


class ZeroModelAutomationSearchClient:
    @property
    def model_slug(self) -> str:
        return MODEL_SLUG

    @property
    def context_window_tokens(self) -> int:
        return CONTEXT_WINDOW_TOKENS

    async def generate(self, messages: list[Any], tools: dict[str, Any]) -> Any:
        action = next_search_action(messages, tools)
        try:
            from stirrup import AssistantMessage, TextBlock, ToolCall
        except ImportError:
            try:
                from stirrup.core.models import AssistantMessage, TextBlock, ToolCall
            except ImportError as exc:
                raise ZeroModelAutomationSearchError("STIRRUP_IMPORT_REQUIRED") from exc

        if action["kind"] == "tool_call":
            return AssistantMessage(
                blocks=[
                    ToolCall(
                        name=action["name"],
                        arguments=json.dumps(
                            action["arguments"],
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    )
                ]
            )
        return AssistantMessage(blocks=[TextBlock(text=action["text"])])


__all__ = [
    "CONTEXT_WINDOW_TOKENS",
    "MODEL_SLUG",
    "ZeroModelAutomationSearchClient",
    "ZeroModelAutomationSearchError",
    "next_search_action",
]
