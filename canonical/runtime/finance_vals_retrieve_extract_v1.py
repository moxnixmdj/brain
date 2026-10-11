#!/usr/bin/env python3
"""Deterministic evidence extraction for Finance Agent v2 stored documents.

The Vals retrieve_information tool substitutes stored document text into a
prompt before querying the configured LLM. Project Brain uses this module to
extract exact source evidence without a donor model.

Specialized paths:
- SEC company_tickers.json -> exact ticker/CIK/title rows.
- SEC CompanyConcept JSON -> exact source fact rows.
- Other text -> deterministic lexical/numeric evidence spans.

No semantic synthesis, hidden rubric use, or benchmark score authority.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_VALS_RETRIEVE_EXTRACT_V1"
_PREFIX = "BRAIN_EXTRACTIVE_EVIDENCE_ONLY\n"
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


class FinanceRetrieveExtractError(ValueError):
    pass


def embedded_json_object(text: str) -> tuple[dict[str, Any], int, int] | None:
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for match in re.finditer(r"\{", str(text or "")):
        start = match.start()
        try:
            obj, consumed = decoder.raw_decode(text[start:])
        except Exception:
            continue
        if isinstance(obj, dict):
            candidates.append((consumed, start, obj))
    if not candidates:
        return None
    consumed, start, obj = max(candidates, key=lambda x: x[0])
    return obj, start, start + consumed


def _requested_tickers(instruction: str) -> set[str]:
    out = {
        x.upper()
        for x in re.findall(
            r"(?:NASDAQ|NYSE)\s*:\s*([A-Z0-9.-]{1,12})",
            instruction,
            flags=re.I,
        )
    }
    out.update(
        x.upper()
        for x in re.findall(
            r"\bticker\s*[=:]\s*([A-Z0-9.-]{1,12})",
            instruction,
            flags=re.I,
        )
    )
    return out


def sec_json_evidence(raw: str) -> str | None:
    embedded = embedded_json_object(raw)
    if embedded is None:
        return None
    obj, start, _end = embedded
    instruction = raw[:start]

    if obj and all(isinstance(v, Mapping) for v in obj.values()):
        registry_rows = [
            v for v in obj.values()
            if isinstance(v, Mapping)
            and "ticker" in v
            and "cik_str" in v
            and "title" in v
        ]
        if registry_rows:
            requested = _requested_tickers(instruction)
            rows = [
                {
                    "ticker": str(row.get("ticker") or "").upper(),
                    "cik_str": row.get("cik_str"),
                    "title": row.get("title"),
                }
                for row in registry_rows
                if not requested
                or str(row.get("ticker") or "").upper() in requested
            ]
            if rows:
                return _PREFIX + "\n".join(
                    "[SEC_TICKER_IDENTITY] "
                    + json.dumps(row, sort_keys=True, default=str)
                    for row in rows[:50]
                )

    units = obj.get("units")
    if (
        isinstance(units, Mapping)
        and isinstance(obj.get("taxonomy"), str)
        and isinstance(obj.get("tag"), str)
        and obj.get("cik") is not None
    ):
        years = {
            int(x)
            for x in re.findall(r"\b(20[0-3][0-9])\b", instruction)
        }
        forms = {
            x.upper()
            for x in re.findall(r"\b(10-K|10-Q|8-K)\b", instruction, flags=re.I)
        }
        rows: list[dict[str, Any]] = []
        for unit, raw_rows in units.items():
            if not isinstance(raw_rows, list):
                continue
            for row in raw_rows:
                if not isinstance(row, Mapping):
                    continue
                fy = row.get("fy")
                form = str(row.get("form") or "").upper()
                if years and fy not in years:
                    continue
                if forms and form not in forms:
                    continue
                rows.append({
                    "unit": unit,
                    "val": row.get("val"),
                    "start": row.get("start"),
                    "end": row.get("end"),
                    "fy": fy,
                    "fp": row.get("fp"),
                    "form": row.get("form"),
                    "filed": row.get("filed"),
                    "accn": row.get("accn"),
                    "frame": row.get("frame"),
                })
        rows.sort(
            key=lambda row: (
                str(row.get("filed") or ""),
                str(row.get("end") or ""),
                str(row.get("start") or ""),
            ),
            reverse=True,
        )
        header = {
            "cik": obj.get("cik"),
            "entityName": obj.get("entityName"),
            "taxonomy": obj.get("taxonomy"),
            "tag": obj.get("tag"),
            "label": obj.get("label"),
        }
        return (
            _PREFIX
            + "[SEC_COMPANYCONCEPT] "
            + json.dumps(header, sort_keys=True, default=str)
            + "\n"
            + "\n".join(
                "[SEC_FACT] " + json.dumps(row, sort_keys=True, default=str)
                for row in rows[:80]
            )
        )
    return None


def _query_terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN.findall(text[:1600])
        if len(token) >= 4 and token.lower() not in _STOPWORDS
    }


def extract_evidence(text: str, *, max_fragments: int = 36) -> str:
    raw = str(text or "")
    if not raw.strip():
        raise FinanceRetrieveExtractError("HELPER_PROMPT_EMPTY")
    if (
        not isinstance(max_fragments, int)
        or isinstance(max_fragments, bool)
        or not 1 <= max_fragments <= 100
    ):
        raise FinanceRetrieveExtractError("MAX_FRAGMENTS_INVALID")

    structured = sec_json_evidence(raw)
    if structured is not None:
        return structured

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
        return _PREFIX + raw[:6000]

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

    return _PREFIX + "\n".join(
        f"[SOURCE_FRAGMENT_{i + 1}] {fragment}"
        for i, fragment in enumerate(chosen)
    )


__all__ = [
    "FinanceRetrieveExtractError",
    "SCHEMA",
    "embedded_json_object",
    "extract_evidence",
    "sec_json_evidence",
]
