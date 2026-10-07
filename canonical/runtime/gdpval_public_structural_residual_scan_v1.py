"""Deterministic structural residual scan for the public GDPval 220-task population.

This scanner is diagnostic only. It does not infer semantic equivalence, P2 membership,
human-preference quality, or terminal capability. It reports explicit rubric/output
surface signals that identify where a bare plan-selection theorem is insufficient
without an additional authenticated execution/quality/source binding.

Input pages are Hugging Face datasets-server JSON row pages.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, Sequence

SCHEMA = "BRAIN_GDPVAL_PUBLIC_STRUCTURAL_RESIDUAL_SCAN_V1"

_PATTERNS: dict[str, re.Pattern[str]] = {
    "overall_format_style": re.compile(
        r"overall formatting and style of the deliverable", re.I
    ),
    "native_artifact_mechanics": re.compile(
        r"\b(workbook|spreadsheet|excel|powerpoint|presentation|slide|worksheet|tab named|pdf|docx)\b",
        re.I,
    ),
    "explicit_calculation": re.compile(
        r"\b(formula|calculate|calculation|arithmetic|equation|variance|percentage|sum|average|ratio|rate|npv|irr|ebitda)\b",
        re.I,
    ),
    "source_reference_fidelity": re.compile(
        r"\b(reference|source|attached|corresponding row|identical to)\b", re.I
    ),
    "visual_layout_quality": re.compile(
        r"\b(layout|readability|formatting|style|visual|font|color|spacing|alignment|presentation quality)\b",
        re.I,
    ),
    "code_or_schema_execution": re.compile(
        r"\b(python|code|script|api|openapi|notebook|yaml|sql)\b", re.I
    ),
}


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _rubric_criteria(row: dict[str, Any]) -> list[str]:
    raw = row.get("rubric_json")
    if not isinstance(raw, str):
        raise ValueError("RUBRIC_JSON_NOT_STRING")
    items = json.loads(raw)
    if not isinstance(items, list):
        raise ValueError("RUBRIC_JSON_NOT_LIST")
    out: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"RUBRIC_ITEM_NOT_OBJECT:{i}")
        criterion = item.get("criterion")
        if not isinstance(criterion, str):
            raise ValueError(f"RUBRIC_CRITERION_NOT_STRING:{i}")
        out.append(criterion)
    return out


def scan_pages(page_paths: Sequence[str | Path]) -> dict[str, Any]:
    if not page_paths:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["PAGE_PATHS_EMPTY"],
            "terminal_authority": False,
        }

    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    page_receipts: list[dict[str, Any]] = []

    for p0 in page_paths:
        p = Path(p0)
        try:
            raw = p.read_bytes()
            doc = json.loads(raw)
        except Exception as exc:
            errors.append(f"PAGE_READ_OR_JSON_FAIL:{p}:{type(exc).__name__}")
            continue
        page_receipts.append(
            {"path": str(p), "bytes": len(raw), "sha256": _sha(raw)}
        )
        xs = doc.get("rows")
        if not isinstance(xs, list):
            errors.append(f"PAGE_ROWS_INVALID:{p}")
            continue
        for i, wrapped in enumerate(xs):
            if not isinstance(wrapped, dict) or not isinstance(wrapped.get("row"), dict):
                errors.append(f"ROW_WRAPPER_INVALID:{p}:{i}")
                continue
            rows.append(wrapped["row"])

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "page_receipts": page_receipts,
            "terminal_authority": False,
        }

    ids: list[str] = []
    counts: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    tasks: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        tid = row.get("task_id")
        if not isinstance(tid, str) or not tid:
            errors.append(f"TASK_ID_INVALID:{i}")
            continue
        ids.append(tid)
        try:
            criteria = _rubric_criteria(row)
        except Exception as exc:
            errors.append(f"RUBRIC_INVALID:{tid}:{exc}")
            continue

        joined = "\n".join(criteria)
        flags = {name: bool(pattern.search(joined)) for name, pattern in _PATTERNS.items()}
        for name, value in flags.items():
            if value:
                counts[name] += 1

        refs = row.get("reference_files") or []
        deliverables = row.get("deliverable_files") or []
        if not isinstance(refs, list) or not isinstance(deliverables, list):
            errors.append(f"FILE_LIST_INVALID:{tid}")
            continue
        if refs:
            counts["has_reference_files"] += 1
        if deliverables:
            counts["has_gold_deliverables"] += 1
        for item in deliverables:
            if isinstance(item, str):
                ext = os.path.splitext(item)[1].lower().lstrip(".") or "<none>"
                extensions[ext] += 1

        tasks.append(
            {
                "task_id": tid,
                "reference_file_count": len(refs),
                "deliverable_file_count": len(deliverables),
                "rubric_item_count": len(criteria),
                "flags": flags,
            }
        )

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "page_receipts": page_receipts,
            "terminal_authority": False,
        }

    if len(ids) != len(set(ids)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["DUPLICATE_TASK_ID"],
            "page_receipts": page_receipts,
            "terminal_authority": False,
        }

    matched = sum(1 for task in tasks if any(task["flags"].values()))
    id_set_digest = _sha(("\n".join(sorted(ids)) + "\n").encode("utf-8"))

    return {
        "schema": SCHEMA,
        "status": "PASS__DIAGNOSTIC_ONLY",
        "row_count": len(rows),
        "task_id_set_sha256": id_set_digest,
        "page_receipts": page_receipts,
        "counts": dict(sorted(counts.items())),
        "deliverable_extension_counts": dict(sorted(extensions.items())),
        "tasks_with_any_explicit_structural_signal": matched,
        "tasks_without_explicit_structural_signal": len(tasks) - matched,
        "tasks": tasks,
        "interpretation": (
            "SIGNALS_ARE_LITERAL_RUBRIC_SURFACE_DIAGNOSTICS_ONLY__THEY_LOCALIZE_"
            "CANDIDATE_EXECUTION_QUALITY_SOURCE_OR_CALCULATION_OBLIGATIONS_BUT_DO_NOT_"
            "PROVE_SEMANTIC_SCOPE_EQUIVALENCE_OR_CAPABILITY"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
