#!/usr/bin/env python3
"""Donor-free Finance Agent v2 substrate for official Vals tool orchestration.

This implements the three proposal-only calls consumed by
finance_agent_v2_brain_model_boundary_v1 without using a language model:

- SUBPROBLEM: derive the next evidence capability from explicit question state.
- SCHEMA_JUDGMENT: decide whether an anonymous tool schema supports that
  capability.
- ARGUMENTS: synthesize arguments only after Brain has selected the route.

Current closed domain is authoritative evidence acquisition:
historical equity prices, SEC ticker identity, and SEC CompanyConcept facts.
When the deterministic domain is exhausted, the controller fails closed rather
than borrowing cognition and relabeling it as Brain capability.
"""
from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_DONOR_FREE_SUBSTRATE_V1"
SEC_TICKER_REGISTRY_URL = "https://www.sec.gov/files/company_tickers.json"

CAP_PRICE = "FETCH_HISTORICAL_PRICE_DATA"
CAP_STORE_REGISTRY = "STORE_SEC_TICKER_REGISTRY"
CAP_READ_REGISTRY = "EXTRACT_SEC_TICKER_IDENTITY"
CAP_STORE_CONCEPT = "STORE_SEC_COMPANYCONCEPT"
CAP_READ_CONCEPT = "EXTRACT_SEC_COMPANYCONCEPT_EVIDENCE"
CAP_WEB = "SEARCH_PUBLIC_SOURCE_EVIDENCE"
CAP_UNRESOLVED = "DETERMINISTIC_FINANCE_SOLVER_REQUIRED"


class FinanceDonorFreeSubstrateError(ValueError):
    pass


def _task_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("task_context")
    if not isinstance(raw, str) or not raw:
        raise FinanceDonorFreeSubstrateError("TASK_CONTEXT_REQUIRED")
    try:
        doc = json.loads(raw)
    except Exception as exc:
        raise FinanceDonorFreeSubstrateError("TASK_CONTEXT_JSON_INVALID") from exc
    if not isinstance(doc, Mapping):
        raise FinanceDonorFreeSubstrateError("TASK_CONTEXT_NOT_OBJECT")
    conversation = doc.get("conversation")
    if not isinstance(conversation, list):
        raise FinanceDonorFreeSubstrateError("CONVERSATION_REQUIRED")
    return {"conversation": conversation}


def _conversation(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        x for x in _task_context(payload)["conversation"]
        if isinstance(x, Mapping)
    ]


def _question(conversation: Sequence[Mapping[str, Any]]) -> str:
    for row in conversation:
        if str(row.get("role") or "") != "user":
            continue
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        if content.lower().startswith("question:"):
            content = content.split(":", 1)[1].strip()
        if content:
            return content
    raise FinanceDonorFreeSubstrateError("QUESTION_NOT_FOUND")


def _receipts(conversation: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [x for x in conversation if str(x.get("role") or "") == "tool"]


def _ticker(symbol: str) -> str:
    return symbol.split(":", 1)[-1].upper()


def _date_iso(value: str) -> str | None:
    raw = " ".join(str(value or "").replace(",", "").split())
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _price_dates(contract: Mapping[str, Any]) -> tuple[str, str] | None:
    dates = [
        x for x in (_date_iso(str(v)) for v in contract.get("dates", []))
        if x is not None
    ]
    dates = list(dict.fromkeys(dates))
    if len(dates) < 2:
        return None
    return min(dates), max(dates)


def _receipt_args(row: Mapping[str, Any]) -> Mapping[str, Any]:
    args = row.get("arguments")
    return args if isinstance(args, Mapping) else {}


def _has_price_receipt(
    receipts: Sequence[Mapping[str, Any]],
    ticker: str,
    start: str,
    end: str,
) -> bool:
    for row in receipts:
        args = _receipt_args(row)
        if (
            str(args.get("ticker") or "").upper() == ticker
            and str(args.get("start_date") or "") == start
            and str(args.get("end_date") or "") == end
            and str(row.get("status") or "") == "success"
            and "date," in str(row.get("content") or "")
        ):
            return True
    return False


def _stored_key_exists(receipts: Sequence[Mapping[str, Any]], key: str) -> bool:
    return any(
        str(_receipt_args(row).get("key") or "") == key
        and str(row.get("status") or "") == "success"
        for row in receipts
    )


def _retrieval_for_key(
    receipts: Sequence[Mapping[str, Any]],
    key: str,
) -> Mapping[str, Any] | None:
    marker = "{{" + key + "}}"
    for row in reversed(receipts):
        args = _receipt_args(row)
        if marker in str(args.get("prompt") or ""):
            return row
    return None


def _ticker_identity(
    receipts: Sequence[Mapping[str, Any]],
    ticker: str,
) -> dict[str, Any] | None:
    for row in reversed(receipts):
        for line in str(row.get("content") or "").splitlines():
            if not line.startswith("[SEC_TICKER_IDENTITY] "):
                continue
            try:
                payload = json.loads(line.split("] ", 1)[1])
            except Exception:
                continue
            if str(payload.get("ticker") or "").upper() != ticker:
                continue
            try:
                cik = int(payload.get("cik_str"))
            except Exception:
                continue
            if cik <= 0:
                continue
            return {
                "ticker": ticker,
                "cik": cik,
                "cik10": f"{cik:010d}",
                "title": str(payload.get("title") or ""),
            }
    return None


def _metric_requests(question: str) -> list[dict[str, Any]]:
    compiled = compile_question(question)
    return [
        dict(x) for x in compiled.get("metric_requests", [])
        if isinstance(x, Mapping)
    ]


def _concept_key(
    ticker: str,
    metric_id: str,
    taxonomy: str,
    tag: str,
) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", f"{ticker}_{metric_id}_{taxonomy}_{tag}")
    return ("sec_" + token)[:120]


def _concept_candidates(question: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for req in _metric_requests(question):
        metric_id = str(req.get("metric_id") or "")
        for candidate in req.get("candidate_concepts", []):
            if not isinstance(candidate, Mapping):
                continue
            taxonomy = str(candidate.get("taxonomy") or "")
            tag = str(candidate.get("tag") or "")
            if taxonomy and tag:
                out.append({
                    "metric_id": metric_id,
                    "taxonomy": taxonomy,
                    "tag": tag,
                })
    return out


def _companyconcept_url(cik10: str, taxonomy: str, tag: str) -> str:
    return (
        "https://data.sec.gov/api/xbrl/companyconcept/"
        + "CIK" + cik10 + "/"
        + quote(taxonomy, safe="._-") + "/"
        + quote(tag, safe="._-") + ".json"
    )


def _resolved_concept_keys(
    receipts: Sequence[Mapping[str, Any]],
) -> set[str]:
    out: set[str] = set()
    for row in receipts:
        args = _receipt_args(row)
        prompt = str(args.get("prompt") or "")
        m = re.search(r"\{\{([^{}]+)\}\}", prompt)
        if m is None:
            continue
        content = str(row.get("content") or "")
        if "[SEC_COMPANYCONCEPT]" in content and "[SEC_FACT]" in content:
            out.add(m.group(1))
    return out


def next_evidence_capability(payload: Mapping[str, Any]) -> dict[str, Any]:
    conversation = _conversation(payload)
    question = _question(conversation)
    receipts = _receipts(conversation)
    contract = compile_question(question)

    if "SHARE_PRICE_RETURN" in contract.get("operations", []):
        date_pair = _price_dates(contract)
        if date_pair is not None:
            start, end = date_pair
            for symbol in contract.get("tickers", []):
                ticker = _ticker(str(symbol))
                if not _has_price_receipt(receipts, ticker, start, end):
                    return {
                        "goal": f"Obtain requested historical price data for {ticker}.",
                        "required_capabilities": [CAP_PRICE],
                        "constraint": None,
                    }

    metric_requests = _metric_requests(question)
    tickers = [_ticker(str(x)) for x in contract.get("tickers", [])]
    if metric_requests and tickers:
        if not _stored_key_exists(receipts, "sec_ticker_registry"):
            return {
                "goal": "Store the authoritative SEC ticker registry.",
                "required_capabilities": [CAP_STORE_REGISTRY],
                "constraint": None,
            }

        for ticker in tickers:
            if _ticker_identity(receipts, ticker) is None:
                row = _retrieval_for_key(receipts, "sec_ticker_registry")
                if row is None or ticker not in str(row.get("content") or ""):
                    return {
                        "goal": f"Extract authoritative SEC identity for {ticker}.",
                        "required_capabilities": [CAP_READ_REGISTRY],
                        "constraint": None,
                    }

        resolved = _resolved_concept_keys(receipts)
        for ticker in tickers:
            identity = _ticker_identity(receipts, ticker)
            if identity is None:
                continue
            for candidate in _concept_candidates(question):
                key = _concept_key(
                    ticker,
                    candidate["metric_id"],
                    candidate["taxonomy"],
                    candidate["tag"],
                )
                if key in resolved:
                    continue
                if not _stored_key_exists(receipts, key):
                    return {
                        "goal": (
                            "Store an authoritative SEC CompanyConcept source for "
                            f"{ticker} {candidate['metric_id']}."
                        ),
                        "required_capabilities": [CAP_STORE_CONCEPT],
                        "constraint": None,
                    }
                retrieval = _retrieval_for_key(receipts, key)
                if retrieval is None:
                    return {
                        "goal": (
                            "Extract exact SEC CompanyConcept evidence for "
                            f"{ticker} {candidate['metric_id']}."
                        ),
                        "required_capabilities": [CAP_READ_CONCEPT],
                        "constraint": None,
                    }
                # Candidate returned no fact rows. Continue to the next standard
                # concept rather than pretending the metric was bound.
                if "[SEC_FACT]" not in str(retrieval.get("content") or ""):
                    continue

        # Every standard candidate has either been attempted or resolved.
        return {
            "goal": "Execute the remaining deterministic finance computation.",
            "required_capabilities": [CAP_UNRESOLVED],
            "constraint": None,
        }

    # Non-standard narrative evidence has not yet been fully compiled into a
    # donor-free source workflow. We expose one public-search capability and
    # then fail closed rather than loop or borrow cognition.
    if not any(
        str(row.get("status") or "") == "success"
        and isinstance(_receipt_args(row).get("search_query"), str)
        for row in receipts
    ):
        return {
            "goal": "Acquire public source evidence explicitly requested by the question.",
            "required_capabilities": [CAP_WEB],
            "constraint": None,
        }

    return {
        "goal": "Execute the remaining deterministic finance computation.",
        "required_capabilities": [CAP_UNRESOLVED],
        "constraint": None,
    }


def _tool_capability(description: str, schema: Mapping[str, Any]) -> set[str]:
    props = schema.get("properties")
    keys = set(props) if isinstance(props, Mapping) else set()
    desc = str(description or "").lower()
    out: set[str] = set()
    if {"ticker", "start_date", "end_date", "asset_class"} <= keys:
        out.add(CAP_PRICE)
    if {"url", "key"} <= keys and "parse" in desc:
        out.update({CAP_STORE_REGISTRY, CAP_STORE_CONCEPT})
    if "prompt" in keys and "stored" in desc:
        out.update({CAP_READ_REGISTRY, CAP_READ_CONCEPT})
    if "search_query" in keys:
        out.add(CAP_WEB)
    return out


def schema_judgment(payload: Mapping[str, Any]) -> dict[str, Any]:
    capability = str(payload.get("required_capability") or "")
    tool = payload.get("anonymous_tool")
    if not isinstance(tool, Mapping):
        raise FinanceDonorFreeSubstrateError("ANONYMOUS_TOOL_REQUIRED")
    schema = tool.get("input_schema")
    if not isinstance(schema, Mapping):
        schema = {}
    supported = capability in _tool_capability(
        str(tool.get("description") or ""),
        schema,
    )
    return {
        "supported": supported,
        "reason": (
            "DETERMINISTIC_SCHEMA_MATCH"
            if supported
            else "DETERMINISTIC_SCHEMA_MISMATCH"
        ),
    }


def _selected_capability(payload: Mapping[str, Any]) -> str:
    caps = payload.get("selected_capabilities")
    if not isinstance(caps, list) or len(caps) != 1:
        raise FinanceDonorFreeSubstrateError("ONE_SELECTED_CAPABILITY_REQUIRED")
    return str(caps[0])


def _argument_state(payload: Mapping[str, Any]) -> tuple[
    list[Mapping[str, Any]], str, list[Mapping[str, Any]], dict[str, Any]
]:
    conversation = _conversation(payload)
    question = _question(conversation)
    receipts = _receipts(conversation)
    contract = compile_question(question)
    return conversation, question, receipts, contract


def arguments(payload: Mapping[str, Any]) -> dict[str, Any]:
    cap = _selected_capability(payload)
    _conversation_rows, question, receipts, contract = _argument_state(payload)

    if cap == CAP_PRICE:
        pair = _price_dates(contract)
        if pair is None:
            raise FinanceDonorFreeSubstrateError("PRICE_DATE_PAIR_REQUIRED")
        start, end = pair
        for symbol in contract.get("tickers", []):
            ticker = _ticker(str(symbol))
            if not _has_price_receipt(receipts, ticker, start, end):
                return {"arguments": {
                    "ticker": ticker,
                    "start_date": start,
                    "end_date": end,
                    "asset_class": "equity",
                }}
        raise FinanceDonorFreeSubstrateError("PRICE_WORK_ALREADY_COMPLETE")

    if cap == CAP_STORE_REGISTRY:
        return {"arguments": {
            "url": SEC_TICKER_REGISTRY_URL,
            "key": "sec_ticker_registry",
        }}

    if cap == CAP_READ_REGISTRY:
        for symbol in contract.get("tickers", []):
            ticker = _ticker(str(symbol))
            if _ticker_identity(receipts, ticker) is None:
                return {"arguments": {
                    "prompt": (
                        f"Return the exact SEC ticker identity for ticker={ticker}.\n"
                        "{{sec_ticker_registry}}"
                    )
                }}
        raise FinanceDonorFreeSubstrateError("TICKER_IDENTITIES_ALREADY_COMPLETE")

    if cap in {CAP_STORE_CONCEPT, CAP_READ_CONCEPT}:
        resolved = _resolved_concept_keys(receipts)
        for symbol in contract.get("tickers", []):
            ticker = _ticker(str(symbol))
            identity = _ticker_identity(receipts, ticker)
            if identity is None:
                continue
            for candidate in _concept_candidates(question):
                key = _concept_key(
                    ticker,
                    candidate["metric_id"],
                    candidate["taxonomy"],
                    candidate["tag"],
                )
                if key in resolved:
                    continue
                if cap == CAP_STORE_CONCEPT and not _stored_key_exists(receipts, key):
                    return {"arguments": {
                        "url": _companyconcept_url(
                            identity["cik10"],
                            candidate["taxonomy"],
                            candidate["tag"],
                        ),
                        "key": key,
                    }}
                if cap == CAP_READ_CONCEPT and _stored_key_exists(receipts, key):
                    if _retrieval_for_key(receipts, key) is None:
                        years = sorted({
                            int(x) for x in re.findall(r"\b(20[0-3][0-9])\b", question)
                        })
                        year_hint = " ".join(str(x) for x in years)
                        return {"arguments": {
                            "prompt": (
                                "Extract exact SEC CompanyConcept fact rows needed "
                                f"for ticker={ticker} metric={candidate['metric_id']} "
                                f"{year_hint} 10-K.\n"
                                "{{" + key + "}}"
                            )
                        }}
        raise FinanceDonorFreeSubstrateError("COMPANYCONCEPT_WORK_NOT_IDENTIFIED")

    if cap == CAP_WEB:
        return {"arguments": {
            "search_query": question,
            "number_of_results": 10,
        }}

    raise FinanceDonorFreeSubstrateError(
        "CAPABILITY_OUTSIDE_DONOR_FREE_CLOSED_DOMAIN:" + cap
    )


class FinanceDonorFreeSubstrate:
    """Callable substrate compatible with Brain Finance boundary V1."""

    def __call__(self, mode: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if mode == "SUBPROBLEM":
            return next_evidence_capability(payload)
        if mode == "SCHEMA_JUDGMENT":
            return schema_judgment(payload)
        if mode == "ARGUMENTS":
            return arguments(payload)
        raise FinanceDonorFreeSubstrateError("UNKNOWN_MODE:" + str(mode))


__all__ = [
    "FinanceDonorFreeSubstrate",
    "FinanceDonorFreeSubstrateError",
    "SCHEMA",
    "arguments",
    "next_evidence_capability",
    "schema_judgment",
]
