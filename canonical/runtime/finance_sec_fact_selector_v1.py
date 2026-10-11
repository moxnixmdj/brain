#!/usr/bin/env python3
"""Fail-closed selector for verified SEC CompanyConcept semantic output.

Selects a fact only when the requested concept/period/form/unit filters and the
latest-filing policy leave a value-consistent set. It never chooses between
conflicting surviving values.

Input is the semantic document emitted by sec_companyconcept_source_native.py.
Independent verification of that document remains a caller obligation.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_SEC_FACT_SELECTOR_V1"
SOURCE_SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_SEMANTICS_V1"

_FACT_ID = re.compile(r"^XBRL_FACT:(?P<qname>[^:]+:[^:]+):(?P<ordinal>[0-9]+)$")


class FinanceFactSelectionError(ValueError):
    pass


def _date(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise FinanceFactSelectionError(code)
    try:
        return date.fromisoformat(value).isoformat()
    except Exception as exc:
        raise FinanceFactSelectionError(code) from exc


def _rows(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(doc, Mapping) or doc.get("schema") != SOURCE_SCHEMA:
        raise FinanceFactSelectionError("SOURCE_SCHEMA_INVALID")
    if doc.get("source_native_identity_extracted") is not True:
        raise FinanceFactSelectionError("SOURCE_NATIVE_IDENTITY_NOT_PROVED")
    contract = doc.get("semantic_contract")
    if not isinstance(contract, Mapping):
        raise FinanceFactSelectionError("SEMANTIC_CONTRACT_REQUIRED")
    facts = contract.get("facts")
    if not isinstance(facts, list):
        raise FinanceFactSelectionError("SEMANTIC_FACTS_REQUIRED")

    grouped: dict[str, dict[str, Any]] = defaultdict(dict)
    for raw in facts:
        if not isinstance(raw, Mapping):
            continue
        subject = raw.get("subject")
        predicate = raw.get("predicate")
        if not isinstance(subject, str) or _FACT_ID.fullmatch(subject) is None:
            continue
        if not isinstance(predicate, str):
            continue
        if predicate in grouped[subject]:
            raise FinanceFactSelectionError(
                "FACT_PREDICATE_DUPLICATE:" + subject + ":" + predicate
            )
        grouped[subject][predicate] = deepcopy(raw.get("object"))

    out: list[dict[str, Any]] = []
    for subject, row in grouped.items():
        m = _FACT_ID.fullmatch(subject)
        assert m is not None
        row = dict(row)
        row["fact_id"] = subject
        row["concept_qname"] = m.group("qname")
        row["ordinal"] = int(m.group("ordinal"))
        for required in ("val", "unit", "end", "filed", "accn", "form"):
            if required not in row:
                raise FinanceFactSelectionError(
                    "FACT_FIELD_MISSING:" + subject + ":" + required
                )
        _date(row["end"], "FACT_END_DATE_INVALID")
        _date(row["filed"], "FACT_FILED_DATE_INVALID")
        if "start" in row:
            _date(row["start"], "FACT_START_DATE_INVALID")
        out.append(row)

    if not out:
        raise FinanceFactSelectionError("NO_XBRL_FACT_ROWS")
    return sorted(out, key=lambda x: x["ordinal"])


def _norm_value(value: Any) -> tuple[str, Any]:
    if isinstance(value, bool):
        return ("json", value)
    if isinstance(value, int):
        return ("decimal", Decimal(value))
    if isinstance(value, float):
        return ("decimal", Decimal(str(value)))
    if isinstance(value, str):
        raw = value.strip()
        try:
            d = Decimal(raw)
        except InvalidOperation:
            return ("text", raw)
        if d.is_finite():
            return ("decimal", d)
        return ("text", raw)
    return ("json", value)


def select_fact(
    doc: Mapping[str, Any],
    *,
    fiscal_year: int | None = None,
    period_end: str | None = None,
    period_start: str | None = None,
    forms: Sequence[str] | None = None,
    unit: str | None = None,
    period_kind: str | None = None,
    prefer_latest_filing: bool = True,
) -> dict[str, Any]:
    rows = _rows(doc)
    qname = str(doc.get("concept_qname") or "")
    rows = [r for r in rows if r["concept_qname"] == qname]
    if not rows:
        raise FinanceFactSelectionError("CONCEPT_ROW_MISMATCH")

    if fiscal_year is not None:
        if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
            raise FinanceFactSelectionError("FISCAL_YEAR_INVALID")
        rows = [r for r in rows if r.get("fy") == fiscal_year]

    if period_end is not None:
        end = _date(period_end, "PERIOD_END_INVALID")
        rows = [r for r in rows if r.get("end") == end]

    if period_start is not None:
        start = _date(period_start, "PERIOD_START_INVALID")
        rows = [r for r in rows if r.get("start") == start]

    if forms is not None:
        if (
            not isinstance(forms, Sequence)
            or isinstance(forms, (str, bytes))
            or not forms
            or any(not isinstance(x, str) or not x.strip() for x in forms)
        ):
            raise FinanceFactSelectionError("FORMS_INVALID")
        allowed = {x.strip().upper() for x in forms}
        rows = [r for r in rows if str(r.get("form") or "").upper() in allowed]

    if unit is not None:
        if not isinstance(unit, str) or not unit.strip():
            raise FinanceFactSelectionError("UNIT_INVALID")
        rows = [r for r in rows if r.get("unit") == unit.strip()]

    if period_kind is not None:
        if period_kind not in {"instant", "duration"}:
            raise FinanceFactSelectionError("PERIOD_KIND_INVALID")
        if period_kind == "instant":
            rows = [r for r in rows if "start" not in r]
        else:
            rows = [r for r in rows if "start" in r]

    if not rows:
        raise FinanceFactSelectionError("NO_FACT_MATCH")

    before_latest = len(rows)
    latest_filed = None
    if prefer_latest_filing:
        latest_filed = max(str(r["filed"]) for r in rows)
        rows = [r for r in rows if r["filed"] == latest_filed]

    normalized = {_norm_value(r["val"]) for r in rows}
    if len(normalized) != 1:
        raise FinanceFactSelectionError("CONFLICTING_SURVIVING_VALUES")

    # Multiple rows are acceptable only when their values agree. This commonly
    # occurs when the same restated historical value appears in more than one
    # context/frame in the latest filing.
    chosen = sorted(
        rows,
        key=lambda r: (
            str(r.get("accn", "")),
            str(r.get("start", "")),
            str(r.get("end", "")),
            str(r.get("frame", "")),
            int(r["ordinal"]),
        ),
    )[0]
    return {
        "schema": SCHEMA,
        "status": "PASS__UNIQUE_VALUE_CONSISTENT_SEC_FACT_SELECTED",
        "pass": True,
        "concept_qname": qname,
        "value": deepcopy(chosen["val"]),
        "unit": chosen["unit"],
        "selected_fact": deepcopy(chosen),
        "surviving_row_count": len(rows),
        "pre_latest_filing_row_count": before_latest,
        "latest_filed": latest_filed,
        "all_surviving_values_equal": True,
        "source_sha256": doc.get("source_sha256"),
        "source_url": doc.get("source_url"),
        "source_independent_verification_required": True,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "semantic_truth_beyond_bound_xbrl_concept_claimed": False,
        "terminal_authority": False,
    }


__all__ = [
    "FinanceFactSelectionError",
    "SCHEMA",
    "select_fact",
]
