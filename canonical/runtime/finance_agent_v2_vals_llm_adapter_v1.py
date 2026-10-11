#!/usr/bin/env python3
"""Exact Vals model_library adapter for the Brain Finance Agent v2 boundary.

This closes the protocol gap between Vals LLM.query() and Project Brain
Finance boundary V3.

Agent turns with tools are converted to Brain history, Brain selects exactly
one official Vals tool, and a normal QueryResult/ToolCall is returned.
Helper retrieval turns with no tools use deterministic extractive evidence
retrieval over the supplied prompt/document text. They do not invoke a donor
model and do not perform semantic synthesis.

The official Vals tools, execution loop, state, time limit, stopping behavior,
and answer extraction remain untouched.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
import logging
import re
from typing import Any, Mapping, Sequence

from model_library.base import LLM, LLMConfig
from model_library.base.input import (
    FileInput,
    FileWithId,
    InputItem,
    RawResponse,
    SystemInput,
    TextInput,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from model_library.base.output import QueryResult

from canonical.runtime.finance_agent_v2_brain_model_boundary_v1 import Substrate
from canonical.runtime.finance_agent_v2_brain_model_boundary_v3 import (
    choose_next_tool_call,
)

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_VALS_LLM_ADAPTER_V1"
_HELPER_PREFIX = "BRAIN_EXTRACTIVE_EVIDENCE_ONLY\n"
_STOPWORDS = frozenset({
    "about", "after", "again", "against", "also", "and", "are", "been",
    "before", "being", "between", "both", "calculate", "company", "could",
    "does", "each", "from", "have", "into", "more", "most", "only", "other",
    "over", "should", "than", "that", "their", "there", "these", "they",
    "this", "through", "using", "what", "when", "where", "which", "with",
    "would", "your",
})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9&._/-]{2,}")
_NUMERIC = re.compile(r"(?:\$|\b)\(?-?\d[\d,]*(?:\.\d+)?%?\)?")


class FinanceValsLLMAdapterError(RuntimeError):
    pass


def _body_dict(tool: ToolDefinition) -> dict[str, Any]:
    body = tool.body
    if hasattr(body, "model_dump"):
        body = body.model_dump(mode="python")
    if not isinstance(body, Mapping):
        raise FinanceValsLLMAdapterError("UNSUPPORTED_TOOL_BODY:" + str(tool.name))
    return {"name": str(tool.name), "body": dict(body)}


def _raw_response_summary(response: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": (
            json.dumps(response, sort_keys=True, default=str)
            if isinstance(response, Mapping)
            else str(response)
        ),
        "brain_raw_response": True,
    }


def _history_rows(input_items: Sequence[InputItem]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in input_items:
        if isinstance(item, SystemInput):
            rows.append({"role": "system", "content": item.text})
        elif isinstance(item, TextInput):
            rows.append({"role": "user", "content": item.text})
        elif isinstance(item, ToolResult):
            result_text = str(item.result)
            error_like = result_text.lstrip().lower().startswith(("error:", "error "))
            rows.append({
                "role": "tool",
                "tool_name": item.tool_call.name,
                "arguments": item.tool_call.parsed_args,
                "content": result_text,
                "status": "error" if error_like else "success",
                "error": result_text if error_like else None,
            })
        elif isinstance(item, RawResponse):
            rows.append(_raw_response_summary(item.response))
        else:
            rows.append({
                "role": "input",
                "content": json.dumps(
                    item.model_dump(mode="json")
                    if hasattr(item, "model_dump")
                    else str(item),
                    sort_keys=True,
                    default=str,
                ),
            })
    return rows


def _tool_receipts(input_items: Sequence[InputItem]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for item in input_items:
        if not isinstance(item, ToolResult):
            continue
        result_text = str(item.result)
        error_like = result_text.lstrip().lower().startswith(("error:", "error "))
        receipts.append({
            "tool_name": item.tool_call.name,
            "arguments": item.tool_call.parsed_args,
            "result": item.result,
            "status": "error" if error_like else "success",
            "error": result_text if error_like else None,
        })
    return receipts


def _question(input_items: Sequence[InputItem]) -> str:
    candidates: list[str] = []
    for item in input_items:
        if not isinstance(item, TextInput):
            continue
        text = str(item.text or "").strip()
        if not text:
            continue
        if text.lower().startswith("question:"):
            return text.split(":", 1)[1].strip()
        candidates.append(text)
    if not candidates:
        raise FinanceValsLLMAdapterError("QUESTION_NOT_FOUND_IN_AGENT_HISTORY")
    return candidates[0]


def _query_terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN.findall(text[:1600])
        if len(token) >= 4 and token.lower() not in _STOPWORDS
    }


def extractive_helper_response(text: str, *, max_fragments: int = 36) -> str:
    """Return high-overlap source spans without semantic synthesis."""
    raw = str(text or "")
    if not raw.strip():
        raise FinanceValsLLMAdapterError("HELPER_PROMPT_EMPTY")
    if (
        not isinstance(max_fragments, int)
        or isinstance(max_fragments, bool)
        or not 1 <= max_fragments <= 100
    ):
        raise FinanceValsLLMAdapterError("MAX_FRAGMENTS_INVALID")

    terms = _query_terms(raw)
    fragments = [
        " ".join(line.split())
        for line in raw.splitlines()
        if len(" ".join(line.split())) >= 24
    ]
    if not fragments:
        fragments = [
            " ".join(x.split())
            for x in re.split(r"(?<=[.!?])\s+", raw)
            if len(" ".join(x.split())) >= 24
        ]
    if not fragments:
        return _HELPER_PREFIX + raw[:6000]

    scored: list[tuple[int, int, str]] = []
    for idx, fragment in enumerate(fragments):
        low = fragment.lower()
        overlap = sum(1 for term in terms if term in low)
        numeric = len(_NUMERIC.findall(fragment))
        source_bonus = 2 if any(
            key in low
            for key in (
                "revenue", "income", "ebitda", "cash", "debt", "shares",
                "guidance", "margin", "expense", "lease", "acquisition",
                "restructur", "goodwill", "intangible", "capital expenditure",
            )
        ) else 0
        score = overlap * 5 + min(numeric, 8) + source_bonus
        if score > 0:
            scored.append((score, idx, fragment))

    if not scored:
        chosen = fragments[:max_fragments]
    else:
        top = sorted(scored, key=lambda x: (-x[0], x[1]))[:max_fragments]
        chosen = [frag for _, _, frag in sorted(top, key=lambda x: x[1])]

    return _HELPER_PREFIX + "\n".join(
        f"[SOURCE_FRAGMENT_{i + 1}] {fragment}"
        for i, fragment in enumerate(chosen)
    )


def _call_id(
    question: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    sequence: int,
) -> str:
    material = json.dumps(
        {
            "question": question,
            "tool": tool_name,
            "arguments": dict(arguments),
            "sequence": sequence,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "brain_" + sha256(material.encode("utf-8")).hexdigest()[:24]


class FinanceBrainValsLLM(LLM):
    """Direct model_library LLM implementation for Finance Agent v2."""

    def __init__(
        self,
        *,
        substrate: Substrate,
        model_name: str = "brain-finance-agent-v2",
        max_repair_rounds: int = 4,
    ) -> None:
        if not callable(substrate):
            raise FinanceValsLLMAdapterError("SUBSTRATE_NOT_CALLABLE")
        self._brain_substrate = substrate
        self._max_repair_rounds = max_repair_rounds
        super().__init__(
            model_name=model_name,
            provider="project-brain",
            config=LLMConfig(
                native=False,
                supports_tools=True,
                supports_temperature=False,
            ),
        )

    def _get_default_api_key(self) -> str:
        raise FinanceValsLLMAdapterError("NO_PROVIDER_API_KEY_REQUIRED")

    def get_client(
        self, api_key: str | None = None, base_url: str | None = None
    ) -> Any:
        raise FinanceValsLLMAdapterError("NO_PROVIDER_CLIENT_REQUIRED")

    async def _query_impl(
        self,
        input: Sequence[InputItem],
        *,
        tools: list[ToolDefinition],
        query_logger: logging.Logger,
        output_schema: dict[str, Any] | type[Any] | None = None,
        **kwargs: object,
    ) -> QueryResult:
        if output_schema is not None:
            raise FinanceValsLLMAdapterError("OUTPUT_SCHEMA_UNSUPPORTED")

        input_items = list(input)
        if not tools:
            text = "\n".join(
                item.text
                for item in input_items
                if isinstance(item, (SystemInput, TextInput))
            )
            evidence = extractive_helper_response(text)
            raw = RawResponse(response={
                "schema": SCHEMA,
                "mode": "DETERMINISTIC_EXTRACTIVE_HELPER",
                "sha256": sha256(evidence.encode("utf-8")).hexdigest(),
            })
            return QueryResult(
                output_text=evidence,
                history=[*input_items, raw],
            )

        question = _question(input_items)
        selected = await choose_next_tool_call(
            question=question,
            history=_history_rows(input_items),
            tool_definitions=[_body_dict(tool) for tool in tools],
            tool_receipts=_tool_receipts(input_items),
            substrate=self._brain_substrate,
            max_repair_rounds=self._max_repair_rounds,
        )
        tool_name = str(selected.get("tool_name") or "").strip()
        arguments = selected.get("arguments")
        if not tool_name or not isinstance(arguments, Mapping):
            raise FinanceValsLLMAdapterError("BRAIN_TOOL_CALL_INVALID")

        call_id = _call_id(
            question,
            tool_name,
            arguments,
            sum(isinstance(x, RawResponse) for x in input_items),
        )
        tool_call = ToolCall(
            id=call_id,
            call_id=call_id,
            name=tool_name,
            args=dict(arguments),
        )
        raw = RawResponse(response={
            "schema": SCHEMA,
            "mode": "BRAIN_SELECTED_OFFICIAL_VALS_TOOL_CALL",
            "tool_name": tool_name,
            "arguments": dict(arguments),
            "brain_selection_authority": True,
            "substrate_route_authority": False,
            "execution_authority": False,
            "terminal_authority": False,
        })
        return QueryResult(
            tool_calls=[tool_call],
            history=[*input_items, raw],
        )

    async def build_body(
        self,
        input: Sequence[InputItem],
        *,
        tools: list[ToolDefinition],
        output_schema: dict[str, Any] | type[Any] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "input_count": len(input),
            "tool_count": len(tools),
            "output_schema_requested": output_schema is not None,
        }

    async def parse_input(
        self, input: Sequence[InputItem], **kwargs: object
    ) -> Any:
        return list(input)

    async def parse_image(self, image: FileInput) -> Any:
        raise FinanceValsLLMAdapterError("IMAGES_UNSUPPORTED")

    async def parse_file(self, file: FileInput) -> Any:
        raise FinanceValsLLMAdapterError("FILES_UNSUPPORTED")

    async def parse_tools(self, tools: list[ToolDefinition]) -> Any:
        return [_body_dict(tool) for tool in tools]

    async def upload_file(
        self,
        name: str,
        mime: str,
        bytes: io.BytesIO,
        type: str = "file",
    ) -> FileWithId:
        raise FinanceValsLLMAdapterError("FILE_UPLOAD_UNSUPPORTED")


__all__ = [
    "FinanceBrainValsLLM",
    "FinanceValsLLMAdapterError",
    "SCHEMA",
    "extractive_helper_response",
]
