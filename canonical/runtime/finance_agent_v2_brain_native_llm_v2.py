#!/usr/bin/env python3
"""Brain-native Finance Agent v2 LLM boundary V2.

V2 extends V1 with a deterministic multi-entity state machine and mechanically
verified market-price synthesis.  It still uses zero external/general-purpose
model cognition.  Unsupported semantic or source bindings remain fail-closed.

Key delta over V1:
- sequentially executes official price_history for every visible ticker;
- computes raw-close returns, sentiment, and return ranking in Brain-owned code;
- sequentially gathers/parses/extracts one primary source per visible ticker;
- preserves every unresolved semantic/source obligation in the final package.

No hidden benchmark examples, gold answers, or external model inference are used.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from canonical.runtime import finance_agent_v2_brain_native_llm_v1 as v1
from canonical.runtime.finance_market_price_series_v1 import period_return
from canonical.runtime.finance_native_evidence_synthesis_v1 import (
    format_revenue_growth,
    synthesize_revenue_growth,
)
from canonical.runtime.finance_quantitative_dependency_v1 import compile_dependencies
from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_BRAIN_NATIVE_LLM_V2"
Q2 = Decimal("0.01")
_DATE_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_DATE_US = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2}|\d{2})\b")


@dataclass(frozen=True)
class TraceRow:
    name: str
    args: dict[str, Any]
    output: str


def _kind(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("kind") or "")
    return str(getattr(item, "kind", "") or "")


def _tool_trace(history: Sequence[Any]) -> list[TraceRow]:
    out: list[TraceRow] = []
    for item in history:
        if _kind(item) != "tool_result":
            continue
        if isinstance(item, Mapping):
            call = item.get("tool_call")
            output = item.get("result")
        else:
            call = getattr(item, "tool_call", None)
            output = getattr(item, "result", None)
        if call is None:
            continue
        if isinstance(call, Mapping):
            name = call.get("name")
            args = call.get("args", {})
            parsed = call.get("parsed_args")
        else:
            name = getattr(call, "name", None)
            args = getattr(call, "args", {})
            parsed = getattr(call, "parsed_args", None)
        if not isinstance(name, str):
            continue
        if isinstance(parsed, Mapping):
            normalized_args = dict(parsed)
        elif isinstance(args, Mapping):
            normalized_args = dict(args)
        elif isinstance(args, str):
            try:
                loaded = json.loads(args)
            except Exception:
                loaded = {}
            normalized_args = dict(loaded) if isinstance(loaded, Mapping) else {}
        else:
            normalized_args = {}
        out.append(TraceRow(name, normalized_args, str(output or "")))
    return out


def _tickers(contract: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for raw in contract.get("tickers", []):
        if not isinstance(raw, str):
            continue
        ticker = raw.split(":", 1)[-1].strip().upper()
        if ticker and ticker not in out:
            out.append(ticker)
    return out


def _explicit_dates(question: str) -> list[str]:
    out: list[str] = []
    for y, m, d in _DATE_ISO.findall(question):
        value = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        if value not in out:
            out.append(value)
    for m, d, y in _DATE_US.findall(question):
        if len(y) == 2:
            y = "20" + y
        value = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        if value not in out:
            out.append(value)
    return out


def _price_result_for(trace: Sequence[TraceRow], ticker: str) -> TraceRow | None:
    for row in reversed(trace):
        if row.name != "price_history":
            continue
        if str(row.args.get("ticker") or "").upper() == ticker.upper():
            return row
    return None


def _search_result_for(trace: Sequence[TraceRow], ticker: str) -> TraceRow | None:
    needle = ticker.casefold()
    for row in reversed(trace):
        if row.name not in {"web_search", "edgar_search"}:
            continue
        q = " ".join(str(x) for x in row.args.values()).casefold()
        if needle in q:
            return row
    return None


def _source_key(ticker: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", ticker.casefold()).strip("_")
    return f"brain_finance_{safe}_source_1"


def _parse_result_for(trace: Sequence[TraceRow], key: str) -> TraceRow | None:
    for row in reversed(trace):
        if row.name == "parse_html_page" and row.args.get("key") == key:
            return row
    return None


def _retrieve_result_for(trace: Sequence[TraceRow], key: str) -> TraceRow | None:
    marker = "{{" + key + "}}"
    for row in reversed(trace):
        if row.name == "retrieve_information":
            prompt = str(row.args.get("prompt") or "")
            if marker in prompt:
                return row
    return None


def _csv_rows(payload: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(payload.strip()))
    if not reader.fieldnames or "date" not in reader.fieldnames or "close" not in reader.fieldnames:
        raise v1.BrainNativeFinanceError("PRICE_HISTORY_CSV_SCHEMA_INVALID")
    rows: list[dict[str, str]] = []
    for raw in reader:
        date_value = str(raw.get("date") or "").strip()
        close = str(raw.get("close") or "").strip()
        if date_value and close and close != "N/A":
            rows.append({"date": date_value, "close": close})
    if not rows:
        raise v1.BrainNativeFinanceError("PRICE_HISTORY_CSV_EMPTY")
    return rows


def _fmt_percent(value: Decimal) -> str:
    q = value.quantize(Q2, rounding=ROUND_HALF_UP)
    if q < 0:
        return f"({abs(q)}%)"
    return f"{q}%"


def synthesize_market(question: str, trace: Sequence[TraceRow]) -> dict[str, Any] | None:
    contract = compile_question(question)
    operations = set(str(x) for x in contract.get("operations", []))
    if "SHARE_PRICE_RETURN" not in operations:
        return None
    tickers = _tickers(contract)
    dates = _explicit_dates(question)
    if not tickers or len(dates) < 2:
        return None

    use_next = bool(
        re.search(
            r"(?i)non[- ]trading|next (?:trading )?day|next day that the market is open",
            question,
        )
    )
    start_date = dates[0]
    end_date = dates[-1]
    values: dict[str, Decimal] = {}
    details: list[dict[str, Any]] = []
    for ticker in tickers:
        row = _price_result_for(trace, ticker)
        if row is None:
            return None
        try:
            out = period_return(
                _csv_rows(row.output),
                start_date,
                end_date,
                next_trading_day_if_missing=use_next,
            )
        except Exception:
            return None
        ret = Decimal(str(out["return_percent"]))
        values[ticker] = ret
        details.append(
            {
                "ticker": ticker,
                "requested_start": start_date,
                "requested_end": end_date,
                "used_start": out["start"]["used_date"],
                "used_end": out["end"]["used_date"],
                "start_close": str(out["start"]["close"]),
                "end_close": str(out["end"]["close"]),
                "return_percent": str(ret),
                "display_return": _fmt_percent(ret),
                "sentiment": (
                    "positive" if ret > 0 else "negative" if ret < 0 else "neutral"
                ),
            }
        )

    ranking = sorted(values, key=lambda name: (-values[name], name))
    return {
        "status": "PASS__MECHANICALLY_BOUND_MARKET_RETURN",
        "details": details,
        "ranking_high_to_low": ranking,
        "all_tickers_bound": True,
        "raw_close_only": True,
        "external_model_calls": 0,
    }


def _market_answer(market: Mapping[str, Any]) -> str:
    lines = ["Market-price calculations from the official price_history tool:"]
    for row in market.get("details", []):
        lines.append(
            f"- {row['ticker']}: {row['display_return']} "
            f"({row['used_start']} close {row['start_close']} to "
            f"{row['used_end']} close {row['end_close']}); "
            f"{row['sentiment']} market sentiment."
        )
    ranking = market.get("ranking_high_to_low", [])
    if ranking:
        lines.append("Return ranking, highest to lowest: " + " > ".join(ranking) + ".")
    return "\n".join(lines)


def _combined_submission(
    question: str,
    trace: Sequence[TraceRow],
    market: Mapping[str, Any] | None,
) -> str:
    contract = compile_question(question)
    deps = compile_dependencies(contract)
    lines: list[str] = []
    if market is not None:
        lines.append(_market_answer(market))

    evidence_rows: list[str] = []
    urls: list[str] = []
    for row in trace:
        if row.name == "retrieve_information":
            value = row.output.strip()
            if value and value not in evidence_rows:
                evidence_rows.append(value[:12000])
        for url in v1._extract_urls(row.output):
            if url not in urls:
                urls.append(url)

    evidence_by_ticker: dict[str, str] = {}
    for ticker in _tickers(contract):
        retrieved = _retrieve_result_for(trace, _source_key(ticker))
        if retrieved is not None and retrieved.output.strip():
            evidence_by_ticker[ticker] = retrieved.output

    revenue = synthesize_revenue_growth(question, evidence_by_ticker)
    revenue_text = format_revenue_growth(revenue)
    if revenue_text:
        lines.append(revenue_text)
        if (
            market is not None
            and revenue.get("all_entities_bound") is True
            and len(market.get("ranking_high_to_low", [])) > 1
            and len(revenue.get("ranking_high_to_low", [])) > 1
            and re.search(r"(?i)rank|correlation|same", question)
        ):
            same = list(market["ranking_high_to_low"]) == list(
                revenue["ranking_high_to_low"]
            )
            lines.append(
                "The market-return and revenue-growth rankings are "
                + ("the same." if same else "not the same.")
            )

    if evidence_rows:
        lines.append("Source-bound extracted evidence:")
        lines.extend(evidence_rows)
    unresolved = list(deps.get("semantic_source_dependencies", []))
    if unresolved:
        lines.append(
            "Unresolved semantic/source dependencies preserved fail-closed: "
            + ", ".join(
                str(x.get("dependency"))
                for x in unresolved
                if isinstance(x, Mapping)
            )
            + "."
        )
    if not lines:
        lines.append("No mechanically admissible answer could be produced.")

    lines.append(
        json.dumps(
            {
                "sources": [
                    {"url": url, "name": "Retrieved source"} for url in urls[:20]
                ]
            },
            sort_keys=True,
        )
    )
    return "\n".join(lines)


def plan_next_v2(history: Sequence[Any], tool_definitions: Sequence[Any]) -> v1.PlannedCall:
    names = v1._tool_names(tool_definitions)
    question = v1.extract_question(history)
    contract = compile_question(question)
    deps = compile_dependencies(contract)
    trace = _tool_trace(history)
    tickers = _tickers(contract)
    dates = _explicit_dates(question)
    operations = set(str(x) for x in contract.get("operations", []))

    def require(name: str) -> None:
        if name not in names:
            raise v1.BrainNativeFinanceError("REQUIRED_TOOL_UNAVAILABLE:" + name)

    if "SHARE_PRICE_RETURN" in operations and len(dates) >= 2:
        for ticker in tickers:
            if _price_result_for(trace, ticker) is None:
                require("price_history")
                return v1.PlannedCall(
                    "price_history",
                    {
                        "ticker": ticker,
                        "start_date": dates[0],
                        "end_date": dates[-1],
                        "asset_class": "equity",
                    },
                    "MULTI_ENTITY_VISIBLE_MARKET_PRICE_DEPENDENCY",
                )

    market = synthesize_market(question, trace)

    # Pure market-return questions can terminate immediately once every price
    # series is mechanically bound.
    non_market_ops = operations - {
        "SHARE_PRICE_RETURN",
        "MARKET_SENTIMENT_FROM_RETURN",
        "RANK_COMPARISON",
    }
    explicit_revenue_growth = bool(
        re.search(r"(?i)\\brevenue growth\\b|growth in revenue|revenue.*growth", question)
    )
    if market is not None and not non_market_ops and not explicit_revenue_growth:
        require("submit_final_result")
        return v1.PlannedCall(
            "submit_final_result",
            {"final_result": _combined_submission(question, trace, market)},
            "MECHANICALLY_CLOSED_MARKET_SYNTHESIS",
        )

    # Gather one primary source and one Brain-native extraction per visible
    # entity. This avoids V1's one-page structural ceiling.
    for ticker in tickers:
        search = _search_result_for(trace, ticker)
        if search is None:
            require("web_search")
            sec_preferred = bool(
                deps.get("sec_standard_dependency_count", 0)
                or any(
                    str(x).startswith("SEC_") or str(x) == "ANNUAL_FILING"
                    for x in contract.get("source_hints", [])
                )
            )
            base_query = v1._bounded_search_query(
                question, sec_preferred=sec_preferred
            )
            return v1.PlannedCall(
                "web_search",
                {
                    "search_query": f"{ticker} {base_query}"[:480],
                    "number_of_results": 10,
                    "end_date": "2026-03-01",
                },
                "PER_ENTITY_BOUND_SOURCE_DISCOVERY",
            )

        key = _source_key(ticker)
        parsed = _parse_result_for(trace, key)
        if parsed is None:
            urls = v1._extract_urls(search.output)
            url = v1._preferred_url(urls)
            if url is None:
                continue
            require("parse_html_page")
            return v1.PlannedCall(
                "parse_html_page",
                {"url": url, "key": key},
                "PER_ENTITY_PRIMARY_SOURCE_PARSE",
            )

        retrieved = _retrieve_result_for(trace, key)
        if retrieved is None:
            require("retrieve_information")
            return v1.PlannedCall(
                "retrieve_information",
                {
                    "prompt": (
                        "[OBJECTIVE]\nentity="
                        + ticker
                        + "\n"
                        + v1._objective(question)
                        + "\n[/OBJECTIVE]\n[DOCUMENT]{{"
                        + key
                        + "}}[/DOCUMENT]"
                    )
                },
                "PER_ENTITY_BRAIN_NATIVE_DOCUMENT_EXTRACTION",
            )

    require("submit_final_result")
    return v1.PlannedCall(
        "submit_final_result",
        {"final_result": _combined_submission(question, trace, market)},
        "V2_BOUND_EVIDENCE_AND_MECHANICAL_SYNTHESIS",
    )


def create_vals_llm_v2():
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

    class BrainNativeFinanceLLMV2(LLM):
        external_model_calls = 0
        external_reasoning_model_calls = 0
        model_dependency_count = 0

        def __init__(self):
            super().__init__(
                "brain-native-finance-v2",
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
            if not tools:
                prompt = "\n".join(
                    v1._text(item) for item in input if v1._kind(item) == "text"
                )
                output = v1.deterministic_document_extract(prompt)
                marker = RawResponse(
                    response={
                        "schema": SCHEMA,
                        "mode": "DETERMINISTIC_HELPER_EXTRACTION",
                        "output_sha256": v1._sha(output),
                        "external_model_calls": 0,
                    }
                )
                return QueryResult(
                    output_text=output,
                    history=[*input, marker],
                    finish_reason=FinishReasonInfo(
                        reason=FinishReason.STOP, raw="brain_native_helper_v2"
                    ),
                )

            call = plan_next_v2(input, tools)
            tc = ToolCall(
                id="brain-v2-"
                + v1._sha(
                    call.name
                    + "\n"
                    + json.dumps(call.args, sort_keys=True, default=str)
                    + "\n"
                    + str(len(_tool_trace(input)))
                )[:20],
                name=call.name,
                args=call.args,
                sequence=0,
            )
            marker = RawResponse(
                response={
                    "schema": SCHEMA,
                    "mode": "BRAIN_NATIVE_TOOL_POLICY_V2",
                    "tool_name": call.name,
                    "reason": call.reason,
                    "args_sha256": v1._sha(
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
                    reason=FinishReason.TOOL_CALLS, raw="brain_native_tool_call_v2"
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
            raise NotImplementedError("BRAIN_NATIVE_FINANCE_V2_HAS_NO_FILE_UPLOAD")

    return BrainNativeFinanceLLMV2()


def ownership_receipt_v2() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "BRAIN_NATIVE_MULTI_ENTITY_ZERO_MODEL_LLM_BOUNDARY",
        "external_model_calls": 0,
        "external_reasoning_model_calls": 0,
        "model_dependency_count": 0,
        "custom_endpoint_used": False,
        "teacher_runtime_calls": 0,
        "retrieve_information_helper": "SAME_BRAIN_NATIVE_DETERMINISTIC_LLM",
        "multi_entity_source_binding": True,
        "mechanical_market_synthesis": True,
        "target_score_claimed": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = [
    "SCHEMA",
    "TraceRow",
    "create_vals_llm_v2",
    "ownership_receipt_v2",
    "plan_next_v2",
    "synthesize_market",
]
