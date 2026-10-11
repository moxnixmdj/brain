#!/usr/bin/env python3
"""Brain-native Finance Agent v2 LLM boundary V1.

Implements the Vals model-library LLM boundary without invoking any external or
general-purpose cognition model.  The class emitted by create_vals_llm() is a
deterministic policy that:

* compiles visible Finance question structure with Brain-owned code;
* chooses only first-party Vals tools by explicit deterministic rules;
* uses the same Brain-native instance for RetrieveInformation helper queries;
* never calls an external model, endpoint, checkpoint, or teacher;
* fail-closes to a sourced evidence submission when stronger synthesis is not
  mechanically supported.

This is capability plumbing, not a benchmark score claim.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from canonical.runtime.finance_quantitative_dependency_v1 import compile_dependencies
from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_BRAIN_NATIVE_LLM_V1"
ALLOWED_TOOLS = frozenset(
    {
        "web_search",
        "retrieve_information",
        "parse_html_page",
        "edgar_search",
        "calculator",
        "price_history",
        "submit_final_result",
    }
)
FORBIDDEN_COGNITION_PROVIDERS = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "gemini",
        "qwen",
        "deepseek",
        "xai",
        "mistral",
        "bedrock",
        "openrouter",
        "custom_endpoint",
    }
)
_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_URL = re.compile(r"https?://[^\s\"'<>]+")
_NUMERIC = re.compile(
    r"(?<![A-Za-z0-9])(?:\$\s*)?[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?(?:\s*%|\s*[xX])?(?![A-Za-z0-9])"
)
_DATE_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_DATE_US = re.compile(
    r"\b(\d{1,2})/(\d{1,2})/(20\d{2}|\d{2})\b"
)
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "how", "in", "is", "it", "of", "on", "or", "that", "the", "to",
    "was", "were", "what", "which", "who", "with", "using", "calculate",
    "compare", "determine", "find", "please", "question", "answer",
}


class BrainNativeFinanceError(ValueError):
    pass


@dataclass(frozen=True)
class PlannedCall:
    name: str
    args: dict[str, Any]
    reason: str


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _text(item: Any) -> str:
    if isinstance(item, Mapping):
        value = item.get("text")
        return value if isinstance(value, str) else ""
    value = getattr(item, "text", "")
    return value if isinstance(value, str) else ""


def _kind(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("kind") or "")
    return str(getattr(item, "kind", "") or "")


def _tool_result(item: Any) -> tuple[str, str] | None:
    if _kind(item) != "tool_result":
        return None
    if isinstance(item, Mapping):
        call = item.get("tool_call") or {}
        name = call.get("name") if isinstance(call, Mapping) else None
        result = item.get("result")
    else:
        call = getattr(item, "tool_call", None)
        name = getattr(call, "name", None)
        result = getattr(item, "result", None)
    if not isinstance(name, str):
        return None
    return name, str(result if result is not None else "")


def extract_question(history: Sequence[Any]) -> str:
    candidates: list[str] = []
    for item in history:
        if _kind(item) != "text":
            continue
        text = _text(item).strip()
        if text:
            candidates.append(text)
    for text in reversed(candidates):
        m = re.match(r"(?is)^Question:\s*(.+)$", text)
        if m:
            return m.group(1).strip()
    if candidates:
        return candidates[-1]
    raise BrainNativeFinanceError("QUESTION_NOT_FOUND_IN_HISTORY")


def tool_results(history: Sequence[Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in history:
        row = _tool_result(item)
        if row is not None:
            out.append(row)
    return out


def _tool_names(tool_definitions: Sequence[Any]) -> set[str]:
    names: set[str] = set()
    for raw in tool_definitions:
        if isinstance(raw, Mapping):
            name = raw.get("name")
        else:
            name = getattr(raw, "name", None)
        if isinstance(name, str) and name:
            names.add(name)
    unknown = names - ALLOWED_TOOLS
    if unknown:
        raise BrainNativeFinanceError(
            "UNRECOGNIZED_TOOL_DEFINITION:" + ",".join(sorted(unknown))
        )
    return names


def _content_tokens(value: str, limit: int = 28) -> list[str]:
    out: list[str] = []
    for raw in _WORD.findall(value):
        tok = raw.casefold().strip("-/")
        if len(tok) < 2 or tok in _STOP:
            continue
        if tok not in out:
            out.append(tok)
        if len(out) >= limit:
            break
    return out


def _bounded_search_query(question: str, *, sec_preferred: bool) -> str:
    contract = compile_question(question)
    tickers = [
        str(x).split(":", 1)[-1]
        for x in contract.get("tickers", [])
        if isinstance(x, str)
    ]
    metrics = [
        str(row.get("metric_id") or "").replace("_", " ")
        for row in contract.get("metric_requests", [])
        if isinstance(row, Mapping) and row.get("metric_id")
    ]
    ops = [str(x).replace("_", " ") for x in contract.get("operations", [])]
    pieces: list[str] = []
    if sec_preferred:
        pieces.append("site:sec.gov")
    for piece in [*tickers, *metrics, *ops, *_content_tokens(question)]:
        clean = " ".join(str(piece).split()).strip()
        if clean and clean.casefold() not in {x.casefold() for x in pieces}:
            pieces.append(clean)
        if len(" ".join(pieces)) >= 420:
            break
    query = " ".join(pieces)[:480].strip()
    if not query:
        raise BrainNativeFinanceError("SEARCH_QUERY_EMPTY")
    return query


def _extract_urls(payload: str) -> list[str]:
    urls: list[str] = []
    try:
        decoded = json.loads(payload)
    except Exception:
        decoded = None

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).casefold() in {"url", "link", "filing_url", "html_url"}:
                    if isinstance(child, str) and child.startswith(("http://", "https://")):
                        urls.append(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(decoded)
    urls.extend(_URL.findall(payload))
    dedup: list[str] = []
    for url in urls:
        url = url.rstrip(".,);]")
        if url not in dedup:
            dedup.append(url)
    return dedup


def _preferred_url(urls: Sequence[str]) -> str | None:
    if not urls:
        return None
    for url in urls:
        low = url.casefold()
        if "sec.gov/archives/" in low:
            return url
    for url in urls:
        if "sec.gov" in url.casefold():
            return url
    return urls[0]


def _saved_key(results: Sequence[tuple[str, str]]) -> str | None:
    for name, output in reversed(results):
        if name != "parse_html_page":
            continue
        m = re.search(
            r"saved to the data storage under the key:\s*([^\s.]+)",
            output,
            flags=re.I,
        )
        if m:
            return m.group(1).strip()
    return None


def _objective(question: str) -> str:
    contract = compile_question(question)
    deps = compile_dependencies(contract)
    fields = [
        "operations=" + ",".join(str(x) for x in contract.get("operations", [])),
        "metrics=" + ",".join(
            str(x.get("metric_id"))
            for x in contract.get("metric_requests", [])
            if isinstance(x, Mapping) and x.get("metric_id")
        ),
        "dependencies=" + ",".join(
            str(x.get("dependency"))
            for x in deps.get("dependencies", [])
            if isinstance(x, Mapping)
        ),
        "question=" + " ".join(question.split())[:1200],
    ]
    return "\n".join(fields)


def deterministic_document_extract(prompt: str, *, max_rows: int = 48) -> str:
    """Extract objective-linked document rows with no model cognition."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise BrainNativeFinanceError("HELPER_PROMPT_REQUIRED")
    om = re.search(r"(?is)\[OBJECTIVE\](.*?)\[/OBJECTIVE\]", prompt)
    dm = re.search(r"(?is)\[DOCUMENT\](.*?)\[/DOCUMENT\]", prompt)
    if not om or not dm:
        # Fail closed: never pretend arbitrary helper prompts were understood.
        return "BRAIN_NATIVE_HELPER_UNRESOLVED"
    objective = " ".join(om.group(1).split())
    document = dm.group(1)
    terms = _content_tokens(objective, limit=42)
    if not terms:
        return "BRAIN_NATIVE_HELPER_NO_OBJECTIVE_TERMS"

    rows = [
        " ".join(x.split())
        for x in re.split(r"\n+|(?<=[.;!?])\s+", document)
        if x.strip()
    ]
    ranked: list[tuple[int, int, str]] = []
    for index, row in enumerate(rows):
        low = row.casefold()
        overlap = sum(1 for term in terms if term in low)
        numbers = len(_NUMERIC.findall(row))
        if overlap == 0:
            continue
        score = overlap * 100 + min(numbers, 9) * 7
        ranked.append((score, -index, row[:2400]))
    ranked.sort(reverse=True)

    selected: list[str] = []
    for _, _, row in ranked:
        if row not in selected:
            selected.append(row)
        if len(selected) >= max_rows:
            break
    if not selected:
        return "BRAIN_NATIVE_HELPER_NO_RELEVANT_ROWS"
    return "\n".join(
        [
            "BRAIN_NATIVE_EXTRACTIVE_EVIDENCE_V1",
            f"objective_sha256={_sha(objective)}",
            *selected,
        ]
    )


def _format_evidence_submission(question: str, results: Sequence[tuple[str, str]]) -> str:
    evidence: list[str] = []
    sources: list[str] = []
    for name, output in results:
        if name in {"retrieve_information", "price_history", "calculator"}:
            text = output.strip()
            if text and text not in evidence:
                evidence.append(text[:10000])
        for url in _extract_urls(output):
            if url not in sources:
                sources.append(url)
    contract = compile_question(question)
    deps = compile_dependencies(contract)
    status = (
        "MECHANICALLY_CLOSED_CANDIDATE"
        if deps.get("mechanically_closed_candidate") is True
        else "SEMANTIC_OR_SOURCE_RESIDUAL_REMAINS"
    )
    body = [
        "Brain-native Finance evidence package.",
        f"Status: {status}.",
        "Requested operations: " + ", ".join(contract.get("operations", [])),
    ]
    if evidence:
        body.append("Evidence:")
        body.extend(evidence[:4])
    else:
        body.append("No admissible evidence was extracted; no unsupported facts are asserted.")
    body.append(
        json.dumps(
            {
                "sources": [
                    {"url": url, "name": "Retrieved source"}
                    for url in sources[:12]
                ]
            },
            sort_keys=True,
        )
    )
    return "\n".join(body)


def plan_next(
    history: Sequence[Any],
    tool_definitions: Sequence[Any],
) -> PlannedCall:
    """Choose exactly one next official Vals tool call."""
    names = _tool_names(tool_definitions)
    question = extract_question(history)
    contract = compile_question(question)
    deps = compile_dependencies(contract)
    results = tool_results(history)
    used = [name for name, _ in results]

    def require(name: str) -> None:
        if name not in names:
            raise BrainNativeFinanceError("REQUIRED_TOOL_UNAVAILABLE:" + name)

    # Market-only work gets the authoritative official price tool first when the
    # visible question exposes one ticker and two ISO/US dates.
    if not results and deps.get("market_price_dependency_count", 0):
        tickers = [
            str(x).split(":", 1)[-1]
            for x in contract.get("tickers", [])
            if isinstance(x, str)
        ]
        dates: list[str] = []
        for y, m, d in _DATE_ISO.findall(question):
            dates.append(f"{y}-{m}-{d}")
        for m, d, y in _DATE_US.findall(question):
            if len(y) == 2:
                y = "20" + y
            dates.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
        dates = list(dict.fromkeys(dates))
        if len(tickers) == 1 and len(dates) >= 2:
            require("price_history")
            return PlannedCall(
                "price_history",
                {
                    "ticker": tickers[0],
                    "start_date": dates[0],
                    "end_date": dates[-1],
                    "asset_class": "equity",
                },
                "VISIBLE_MARKET_PRICE_DEPENDENCY",
            )

    if not results:
        require("web_search")
        sec_preferred = bool(
            deps.get("sec_standard_dependency_count", 0)
            or any(
                str(x).startswith("SEC_") or str(x) == "ANNUAL_FILING"
                for x in contract.get("source_hints", [])
            )
        )
        return PlannedCall(
            "web_search",
            {
                "search_query": _bounded_search_query(
                    question, sec_preferred=sec_preferred
                ),
                "number_of_results": 10,
                "end_date": "2026-03-01",
            },
            "BOUND_SOURCE_DISCOVERY",
        )

    if "parse_html_page" not in used:
        search_outputs = [
            output for name, output in results if name in {"web_search", "edgar_search"}
        ]
        urls: list[str] = []
        for output in search_outputs:
            urls.extend(_extract_urls(output))
        url = _preferred_url(urls)
        if url is None:
            if used.count("web_search") < 2:
                require("web_search")
                return PlannedCall(
                    "web_search",
                    {
                        "search_query": _bounded_search_query(
                            question, sec_preferred=False
                        ),
                        "number_of_results": 10,
                        "end_date": "2026-03-01",
                    },
                    "SOURCE_DISCOVERY_FALLBACK",
                )
            require("submit_final_result")
            return PlannedCall(
                "submit_final_result",
                {"final_result": _format_evidence_submission(question, results)},
                "FAIL_CLOSED_NO_SOURCE_URL",
            )
        require("parse_html_page")
        return PlannedCall(
            "parse_html_page",
            {"url": url, "key": "brain_finance_source_1"},
            "PARSE_SELECTED_PRIMARY_SOURCE",
        )

    key = _saved_key(results)
    if key and "retrieve_information" not in used:
        require("retrieve_information")
        return PlannedCall(
            "retrieve_information",
            {
                "prompt": (
                    "[OBJECTIVE]\n"
                    + _objective(question)
                    + "\n[/OBJECTIVE]\n[DOCUMENT]{{"
                    + key
                    + "}}[/DOCUMENT]"
                )
            },
            "BRAIN_NATIVE_DOCUMENT_EXTRACTION",
        )

    # V1 intentionally does not invent semantic bindings.  It returns a sourced
    # evidence package rather than laundering an unsupported interpretation into
    # a benchmark answer.  Later native synthesis layers can replace this branch
    # only after independent qualification.
    require("submit_final_result")
    return PlannedCall(
        "submit_final_result",
        {"final_result": _format_evidence_submission(question, results)},
        "FAIL_CLOSED_EVIDENCE_PACKAGE_SUBMISSION",
    )


def create_vals_llm():
    """Return an instance implementing Vals model_library.base.LLM locally.

    Imports are delayed so the Brain core remains importable without Vals'
    model-library installed.
    """
    import logging

    from model_library.base import LLM, LLMConfig
    from model_library.base.input import (
        FileInput,
        FileWithId,
        InputItem,
        RawResponse,
        ToolCall,
        ToolDefinition,
    )
    from model_library.base.output import FinishReason, FinishReasonInfo, QueryResult

    class BrainNativeFinanceLLM(LLM):
        external_model_calls = 0
        external_reasoning_model_calls = 0
        model_dependency_count = 0

        def __init__(self):
            super().__init__(
                "brain-native-finance-v1",
                "project-brain",
                config=LLMConfig(native=False, supports_tools=True),
            )

        def get_client(
            self, api_key: str | None = None, base_url: str | None = None
        ) -> Any:
            return None

        def _get_default_api_key(self) -> str:
            return ""

        async def _query_impl(
            self,
            input: Sequence[InputItem],
            *,
            tools: list[ToolDefinition],
            query_logger: logging.Logger,
            output_schema: dict[str, Any] | type[Any] | None = None,
            **kwargs: object,
        ) -> QueryResult:
            # RetrieveInformation recursively invokes the same LLM with no tools.
            # That path is deterministic extraction, not a model call.
            if not tools:
                prompt = "\n".join(
                    _text(item) for item in input if _kind(item) == "text"
                )
                output = deterministic_document_extract(prompt)
                marker = RawResponse(
                    response={
                        "schema": SCHEMA,
                        "mode": "DETERMINISTIC_HELPER_EXTRACTION",
                        "output_sha256": _sha(output),
                        "external_model_calls": 0,
                    }
                )
                return QueryResult(
                    output_text=output,
                    history=[*input, marker],
                    finish_reason=FinishReasonInfo(
                        reason=FinishReason.STOP, raw="brain_native_helper"
                    ),
                )

            call = plan_next(input, tools)
            tc = ToolCall(
                id="brain-" + _sha(
                    call.name
                    + "\n"
                    + json.dumps(call.args, sort_keys=True, default=str)
                    + "\n"
                    + str(len(tool_results(input)))
                )[:20],
                name=call.name,
                args=call.args,
                sequence=0,
            )
            marker = RawResponse(
                response={
                    "schema": SCHEMA,
                    "mode": "BRAIN_NATIVE_TOOL_POLICY",
                    "tool_name": call.name,
                    "reason": call.reason,
                    "args_sha256": _sha(
                        json.dumps(call.args, sort_keys=True, default=str)
                    ),
                    "external_model_calls": 0,
                    "external_reasoning_model_calls": 0,
                    "model_dependency_count": 0,
                }
            )
            return QueryResult(
                tool_calls=[tc],
                history=[*input, marker],
                finish_reason=FinishReasonInfo(
                    reason=FinishReason.TOOL_CALLS, raw="brain_native_tool_call"
                ),
            )

        async def build_body(
            self,
            input: Sequence[InputItem],
            *,
            tools: list[ToolDefinition],
            output_schema: dict[str, Any] | type[Any] | None = None,
            **kwargs: object,
        ) -> dict[str, Any]:
            return {}

        async def parse_input(self, input: Sequence[InputItem], **kwargs: object) -> Any:
            return input

        async def parse_image(self, image: FileInput) -> Any:
            return image

        async def parse_file(self, file: FileInput) -> Any:
            return file

        async def parse_tools(self, tools: list[ToolDefinition]) -> Any:
            return tools

        async def upload_file(
            self,
            name: str,
            mime: str,
            bytes: io.BytesIO,
            type: Literal["image", "file"] = "file",
        ) -> FileWithId:
            raise NotImplementedError("BRAIN_NATIVE_FINANCE_V1_HAS_NO_FILE_UPLOAD")

    return BrainNativeFinanceLLM()


def ownership_receipt() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "BRAIN_NATIVE_ZERO_MODEL_LLM_BOUNDARY",
        "external_model_calls": 0,
        "external_reasoning_model_calls": 0,
        "model_dependency_count": 0,
        "custom_endpoint_used": False,
        "teacher_runtime_calls": 0,
        "retrieve_information_helper": "SAME_BRAIN_NATIVE_DETERMINISTIC_LLM",
        "target_score_claimed": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = [
    "ALLOWED_TOOLS",
    "BrainNativeFinanceError",
    "PlannedCall",
    "SCHEMA",
    "create_vals_llm",
    "deterministic_document_extract",
    "extract_question",
    "ownership_receipt",
    "plan_next",
    "tool_results",
]
