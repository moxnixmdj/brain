#!/usr/bin/env python3
"""Deterministic document extraction with local context windows for Finance V2.

The extractor selects objective-overlapping source rows, then preserves a small
number of adjacent rows around each hit. This is specifically intended to keep
financial table headers (years/periods/units) attached to the metric rows they
qualify.

No semantic model is used. Selection is lexical and numeric-density based.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from canonical.runtime import finance_agent_v2_brain_native_llm_v1 as v1

SCHEMA = "PROJECT_BRAIN_FINANCE_NATIVE_DOCUMENT_EXTRACT_V2"


class FinanceDocumentExtractError(ValueError):
    pass


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_with_context(
    prompt: str,
    *,
    max_hit_rows: int = 24,
    context_before: int = 2,
    context_after: int = 2,
    max_output_rows: int = 120,
) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise FinanceDocumentExtractError("HELPER_PROMPT_REQUIRED")
    if max_hit_rows <= 0 or max_output_rows <= 0:
        raise FinanceDocumentExtractError("ROW_BUDGET_INVALID")
    if context_before < 0 or context_after < 0:
        raise FinanceDocumentExtractError("CONTEXT_WINDOW_INVALID")

    om = re.search(r"(?is)\[OBJECTIVE\](.*?)\[/OBJECTIVE\]", prompt)
    dm = re.search(r"(?is)\[DOCUMENT\](.*?)\[/DOCUMENT\]", prompt)
    if not om or not dm:
        return "BRAIN_NATIVE_HELPER_UNRESOLVED"

    objective = " ".join(om.group(1).split())
    document = dm.group(1)
    terms = v1._content_tokens(objective, limit=48)
    if not terms:
        return "BRAIN_NATIVE_HELPER_NO_OBJECTIVE_TERMS"

    # Preserve line boundaries first because filing tables frequently use one
    # row per line. Only split long prose-only lines into sentence-like rows.
    rows: list[str] = []
    for raw in document.splitlines():
        clean = " ".join(raw.split())
        if not clean:
            continue
        if len(clean) <= 2400:
            rows.append(clean)
            continue
        rows.extend(
            " ".join(x.split())
            for x in re.split(r"(?<=[.;!?])\s+", clean)
            if x.strip()
        )

    ranked: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        low = row.casefold()
        overlap = sum(1 for term in terms if term in low)
        if overlap == 0:
            continue
        numeric = len(v1._NUMERIC.findall(row))
        year_count = len(re.findall(r"\b20\d{2}\b", row))
        score = overlap * 100 + min(numeric, 12) * 7 + min(year_count, 6) * 11
        ranked.append((score, index))
    ranked.sort(key=lambda x: (-x[0], x[1]))

    hit_indices = [index for _, index in ranked[:max_hit_rows]]
    if not hit_indices:
        return "BRAIN_NATIVE_HELPER_NO_RELEVANT_ROWS"

    selected_indices: set[int] = set()
    for index in hit_indices:
        lo = max(0, index - context_before)
        hi = min(len(rows), index + context_after + 1)
        selected_indices.update(range(lo, hi))

    ordered = sorted(selected_indices)[:max_output_rows]
    output_rows = [f"[row {index}] {rows[index]}" for index in ordered]
    return "\n".join(
        [
            "BRAIN_NATIVE_EXTRACTIVE_EVIDENCE_V2",
            f"schema={SCHEMA}",
            f"objective_sha256={_sha(objective)}",
            f"selected_hit_count={len(hit_indices)}",
            f"selected_row_count={len(output_rows)}",
            *output_rows,
        ]
    )


def ownership_receipt() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "DETERMINISTIC_CONTEXT_WINDOW_EXTRACTION",
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "teacher_runtime_calls": 0,
        "semantic_completion_performed": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = [
    "FinanceDocumentExtractError",
    "SCHEMA",
    "extract_with_context",
    "ownership_receipt",
]
