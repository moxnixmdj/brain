"""Brain-owned workflow-control wrapper for Stirrup-compatible cognition clients.

This module is evaluator-neutral. It does not contain AutomationBench task data,
private benchmark semantics, provider credentials, or a model implementation.

The wrapped base_client is a declared general-cognition substrate. Brain owns
the durable workflow-control policy and fail-closed tool-call validation. V1 makes
exactly one base generate call per outer generate invocation and returns
the exact valid AssistantMessage object produced by the base client.

Default integration targets Artificial Analysis Stirrup's public LLMClient
protocol, but the core wrapper is duck-typed and can be unit-tested without
installing Stirrup.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any


class BrainAutomationPolicyError(RuntimeError):
    """Raised when a substrate response violates Brain's workflow contract."""


BRAIN_AUTOMATION_POLICY_V1 = """\
You are the general-cognition substrate inside a Brain-owned workflow controller.

For every tool-using workflow:
1. Derive an explicit ledger of requested objectives and hard constraints before changing state.
2. Treat tool results and visible state as the source of truth. Do not invent identifiers, values, records, or completion evidence.
3. If the correct action route is not established, discover or inspect it before mutation.
4. Read the minimum state needed to bind targets, preserve exact source values, and check guardrails.
5. Make only the minimum necessary side effect. Never modify unrelated state.
6. Emit at most ONE tool call in an assistant turn. Let the resulting observation inform the next action.
7. Validate arguments against the available tool schema and use exact field names and types.
8. After errors or rejected actions, diagnose the cause and change the plan; do not blindly repeat an unchanged action.
9. Keep all explicit user constraints live across the whole workflow, including negative constraints and preservation requirements.
10. Do not treat an attempted mutation as success. Verify remaining objectives from subsequent observations whenever the tools permit it.
11. Do not claim completion while any explicit objective or hard constraint is unresolved.
12. If evidence is insufficient or no authorized safe route exists, fail closed rather than fabricate success.

These rules govern workflow control only. Follow the evaluator/user task itself for the actual requested outcome.
"""


def policy_sha256() -> str:
    return hashlib.sha256(BRAIN_AUTOMATION_POLICY_V1.encode("utf-8")).hexdigest()


def _default_system_message_factory(content: str) -> Any:
    try:
        from stirrup import SystemMessage  # type: ignore
    except ImportError:
        try:
            from stirrup.core.models import SystemMessage  # type: ignore
        except ImportError as exc:
            raise BrainAutomationPolicyError(
                "STIRRUP_NOT_INSTALLED_AND_NO_SYSTEM_MESSAGE_FACTORY_PROVIDED"
            ) from exc
    return SystemMessage(content=content)


def _insert_policy(messages: Sequence[Any], factory: Callable[[str], Any]) -> list[Any]:
    """Insert Brain policy after the leading system-message prefix."""
    copied = list(messages)
    index = 0
    while index < len(copied) and getattr(copied[index], "role", None) == "system":
        index += 1
    copied.insert(index, factory(BRAIN_AUTOMATION_POLICY_V1))
    return copied


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise BrainAutomationPolicyError("TOOL_ARGUMENTS_MUST_BE_JSON_STRING")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrainAutomationPolicyError("TOOL_ARGUMENTS_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise BrainAutomationPolicyError("TOOL_ARGUMENTS_MUST_DECODE_TO_OBJECT")
    return value


def _validate_against_tool_schema(tool: Any, arguments: dict[str, Any]) -> None:
    params = getattr(tool, "parameters", None)
    if params is None:
        raise BrainAutomationPolicyError("TOOL_PARAMETERS_SCHEMA_MISSING")

    validator = getattr(params, "model_validate", None)
    if callable(validator):
        try:
            validator(arguments)
        except Exception as exc:
            raise BrainAutomationPolicyError("TOOL_ARGUMENTS_SCHEMA_INVALID") from exc
        return

    legacy_validator = getattr(params, "parse_obj", None)
    if callable(legacy_validator):
        try:
            legacy_validator(arguments)
        except Exception as exc:
            raise BrainAutomationPolicyError("TOOL_ARGUMENTS_SCHEMA_INVALID") from exc
        return

    raise BrainAutomationPolicyError("TOOL_PARAMETERS_SCHEMA_NOT_VALIDATABLE")


def validate_assistant_message(response: Any, tools: Mapping[str, Any]) -> Any:
    """Fail closed on undeclared, malformed, or parallel tool actions."""
    blocks = getattr(response, "blocks", None)
    if not isinstance(blocks, (list, tuple)):
        raise BrainAutomationPolicyError("ASSISTANT_MESSAGE_BLOCKS_REQUIRED")

    tool_calls = [
        block for block in blocks
        if getattr(block, "kind", None) == "tool_call"
    ]
    if len(tool_calls) > 1:
        raise BrainAutomationPolicyError("MULTIPLE_TOOL_CALLS_FORBIDDEN")

    if not tool_calls:
        return response

    call = tool_calls[0]
    name = getattr(call, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise BrainAutomationPolicyError("TOOL_CALL_NAME_INVALID")
    name = name.strip()
    if name not in tools:
        raise BrainAutomationPolicyError("TOOL_CALL_NOT_DECLARED")

    arguments = _parse_tool_arguments(getattr(call, "arguments", None))
    _validate_against_tool_schema(tools[name], arguments)
    return response


class BrainAutomationClient:
    """Stirrup-compatible Brain workflow controller around an injected LLMClient."""

    def __init__(
        self,
        base_client: Any,
        *,
        system_message_factory: Callable[[str], Any] | None = None,
    ) -> None:
        if base_client is None or not callable(getattr(base_client, "generate", None)):
            raise TypeError("BASE_CLIENT_GENERATE_REQUIRED")
        slug = getattr(base_client, "model_slug", None)
        context = getattr(base_client, "context_window_tokens", None)
        if not isinstance(slug, str) or not slug.strip():
            raise TypeError("BASE_CLIENT_MODEL_SLUG_REQUIRED")
        if not isinstance(context, int) or isinstance(context, bool) or context <= 0:
            raise TypeError("BASE_CLIENT_CONTEXT_WINDOW_POSITIVE_INT_REQUIRED")

        self._base_client = base_client
        self._system_message_factory = system_message_factory or _default_system_message_factory
        self._base_model_slug = slug.strip()
        self._context_window_tokens = context
        self._generate_calls = 0

    @property
    def model_slug(self) -> str:
        return f"brain/automation-control-v1+{self._base_model_slug}"

    @property
    def base_model_slug(self) -> str:
        return self._base_model_slug

    @property
    def context_window_tokens(self) -> int:
        return self._context_window_tokens

    @property
    def brain_policy_sha256(self) -> str:
        return policy_sha256()

    @property
    def base_generate_call_count(self) -> int:
        return self._generate_calls

    async def generate(self, messages: list[Any], tools: dict[str, Any]) -> Any:
        if not isinstance(messages, list):
            raise TypeError("MESSAGES_LIST_REQUIRED")
        if not isinstance(tools, dict):
            raise TypeError("TOOLS_DICT_REQUIRED")

        controlled_messages = _insert_policy(messages, self._system_message_factory)
        self._generate_calls += 1
        response = await self._base_client.generate(controlled_messages, tools)
        return validate_assistant_message(response, tools)


__all__ = [
    "BRAIN_AUTOMATION_POLICY_V1",
    "BrainAutomationClient",
    "BrainAutomationPolicyError",
    "policy_sha256",
    "validate_assistant_message",
]
