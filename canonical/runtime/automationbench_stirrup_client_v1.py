"""Stirrup adapter for Project Brain's owned AutomationBench policy.

This module adds no cognition. It only:
- converts Stirrup chat/tool history into the deterministic policy state format;
- invokes automationbench_policy_state_machine_v1;
- converts returned calls into Stirrup AssistantMessage ToolCall blocks.

The Stirrup import is lazy so Brain's core repository does not require Stirrup
unless this adapter is actually used by an evaluator.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from canonical.runtime.automationbench_policy_state_machine_v1 import next_policy_action

MODEL_SLUG = "project-brain/automationbench-owned-policy-v1"
CONTEXT_WINDOW_TOKENS = 200_000
_METADATA_KEY = "project_brain/automationbench_semantic"


def _content_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(str(getattr(item, "text")))
            elif hasattr(item, "content"):
                parts.append(str(getattr(item, "content")))
        return "\n".join(x for x in parts if x)
    return str(value)


def extract_task_prompt(messages: Sequence[Any]) -> str:
    """Use the first substantive user message as the benchmark task prompt."""
    for msg in messages:
        role = str(getattr(msg, "role", ""))
        kind = str(getattr(msg, "kind", ""))
        if role == "user" and kind not in {"summary", "turn_warning"}:
            text = _content_text(getattr(msg, "content", ""))
            if text.strip():
                return text.strip()
    return ""


def normalize_history(messages: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert only load-bearing Stirrup history into Brain policy events."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = str(getattr(msg, "role", ""))
        if role == "tool":
            out.append(
                {
                    "kind": "tool_result",
                    "name": str(getattr(msg, "name", "")),
                    "content": _content_text(getattr(msg, "content", "")),
                    "tool_call_id": str(getattr(msg, "tool_call_id", "")),
                }
            )
            continue

        if role == "assistant":
            metadata = getattr(msg, "metadata", None)
            if isinstance(metadata, Mapping) and metadata.get(_METADATA_KEY):
                out.append(
                    {
                        "kind": "assistant_state",
                        "metadata": {_METADATA_KEY: str(metadata[_METADATA_KEY])},
                    }
                )
            for block in getattr(msg, "blocks", []) or []:
                if str(getattr(block, "kind", "")) != "tool_call":
                    continue
                name = str(getattr(block, "name", ""))
                arguments = getattr(block, "arguments", "{}")
                out.append(
                    {
                        "kind": "tool_call",
                        "name": name,
                        "arguments": str(arguments),
                    }
                )
    return out


class ProjectBrainAutomationBenchClient:
    """Custom Stirrup LLMClient implementing the owned deterministic Brain policy."""

    @property
    def model_slug(self) -> str:
        return MODEL_SLUG

    @property
    def context_window_tokens(self) -> int:
        return CONTEXT_WINDOW_TOKENS

    async def generate(self, messages: list[Any], tools: dict[str, Any]) -> Any:
        # Lazy import keeps the canonical Brain runtime independent of Stirrup.
        from stirrup import AssistantMessage, TextBlock, TokenUsage, ToolCall

        prompt = extract_task_prompt(messages)
        if not prompt:
            return AssistantMessage(
                blocks=[TextBlock(text="No executable task prompt was available.")],
                token_usage=TokenUsage(),
                metadata={"project_brain/status": "FAIL_CLOSED_NO_TASK_PROMPT"},
            )

        decision = next_policy_action(
            prompt=prompt,
            history=normalize_history(messages),
        )

        if decision.get("status") != "CALL_TOOLS":
            return AssistantMessage(
                blocks=[
                    TextBlock(
                        text=(
                            "Brain has no grounded owned policy extension for the "
                            "remaining workflow operation; stopping fail-closed."
                        )
                    )
                ],
                token_usage=TokenUsage(),
                metadata={
                    "project_brain/status": str(decision.get("status") or "NEEDS_POLICY_EXTENSION"),
                    "project_brain/phase": str(decision.get("phase") or ""),
                },
            )

        blocks: list[Any] = []
        missing: list[str] = []
        for call in decision.get("calls") or []:
            name = str(call.get("tool") or "")
            args = call.get("arguments") or {}
            if not name or name not in tools:
                missing.append(name or "<empty>")
                continue
            blocks.append(
                ToolCall(
                    name=name,
                    arguments=json.dumps(args, sort_keys=True),
                )
            )

        if missing:
            return AssistantMessage(
                blocks=[
                    TextBlock(
                        text=(
                            "Required benchmark tools are unavailable: "
                            + ", ".join(sorted(set(missing)))
                        )
                    )
                ],
                token_usage=TokenUsage(),
                metadata={
                    "project_brain/status": "FAIL_CLOSED_REQUIRED_TOOL_MISSING",
                    "project_brain/phase": str(decision.get("phase") or ""),
                },
            )

        if not blocks:
            return AssistantMessage(
                blocks=[TextBlock(text="No grounded tool call was produced.")],
                token_usage=TokenUsage(),
                metadata={"project_brain/status": "FAIL_CLOSED_NO_CALL"},
            )

        metadata: dict[str, Any] = {
            "project_brain/status": "CALL_TOOLS",
            "project_brain/phase": str(decision.get("phase") or ""),
        }
        semantic = decision.get("semantic")
        if semantic:
            metadata[_METADATA_KEY] = str(semantic)

        return AssistantMessage(
            blocks=blocks,
            token_usage=TokenUsage(),
            metadata=metadata,
        )
