#!/usr/bin/env python3
"""Normalize raw SEC CompanyConcept JSON into Brain source-native semantics.

This is a pure parser/validator. Transport is outside this module. It accepts a
raw SEC CompanyConcept payload already obtained through an authorized route and
emits the semantic shape consumed by finance_sec_fact_selector_v1.

No model, fuzzy matching, hidden benchmark data, or arithmetic is used.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_SEMANTICS_V1"
_URL = re.compile(
    r"^https://data\.sec\.gov/api/xbrl/companyconcept/"
    r"CIK(?P<cik>[0-9]{10})/(?P<taxonomy>[A-Za-z0-9_.-]+)/"
    r"(?P<tag>[A-Za-z0-9_.-]+)\.json$"
)


class SecCompanyConceptNormalizationError(ValueError):
    pass


def _payload(raw: Any) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise SecCompanyConceptNormalizationError("SOURCE_EMPTY")
        try:
            parsed = json.loads(text)
        except Exception as exc:
            raise SecCompanyConceptNormalizationError("SOURCE_JSON_INVALID") from exc
        if not isinstance(parsed, Mapping):
            raise SecCompanyConceptNormalizationError("SOURCE_JSON_NOT_OBJECT")
        return parsed
    raise SecCompanyConceptNormalizationError("SOURCE_TYPE_UNSUPPORTED")


def normalize_companyconcept(
    raw: Any,
    *,
    source_url: str,
    expected_cik10: str | None = None,
    expected_taxonomy: str | None = None,
    expected_tag: str | None = None,
) -> dict[str, Any]:
    m = _URL.fullmatch(str(source_url or "").strip())
    if m is None:
        raise SecCompanyConceptNormalizationError("SOURCE_URL_INVALID")
    url_cik = m.group("cik")
    url_taxonomy = m.group("taxonomy")
    url_tag = m.group("tag")

    if expected_cik10 is not None and str(expected_cik10) != url_cik:
        raise SecCompanyConceptNormalizationError("EXPECTED_CIK_URL_MISMATCH")
    if expected_taxonomy is not None and str(expected_taxonomy) != url_taxonomy:
        raise SecCompanyConceptNormalizationError("EXPECTED_TAXONOMY_URL_MISMATCH")
    if expected_tag is not None and str(expected_tag) != url_tag:
        raise SecCompanyConceptNormalizationError("EXPECTED_TAG_URL_MISMATCH")

    doc = _payload(raw)
    try:
        cik_int = int(doc.get("cik"))
    except Exception as exc:
        raise SecCompanyConceptNormalizationError("PAYLOAD_CIK_INVALID") from exc
    if f"{cik_int:010d}" != url_cik:
        raise SecCompanyConceptNormalizationError("PAYLOAD_CIK_URL_MISMATCH")

    taxonomy = str(doc.get("taxonomy") or "")
    tag = str(doc.get("tag") or "")
    if taxonomy != url_taxonomy:
        raise SecCompanyConceptNormalizationError("PAYLOAD_TAXONOMY_URL_MISMATCH")
    if tag != url_tag:
        raise SecCompanyConceptNormalizationError("PAYLOAD_TAG_URL_MISMATCH")

    entity_name = doc.get("entityName")
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise SecCompanyConceptNormalizationError("ENTITY_NAME_REQUIRED")

    units = doc.get("units")
    if not isinstance(units, Mapping) or not units:
        raise SecCompanyConceptNormalizationError("UNITS_REQUIRED")

    source_text = (
        raw if isinstance(raw, str)
        else json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str)
    )
    source_sha = sha256(
        source_text.encode("utf-8")
        if isinstance(source_text, str)
        else bytes(source_text)
    ).hexdigest()

    facts: list[dict[str, Any]] = []
    ordinal = 0
    qname = taxonomy + ":" + tag
    for unit, rows in units.items():
        if not isinstance(unit, str) or not unit:
            raise SecCompanyConceptNormalizationError("UNIT_KEY_INVALID")
        if not isinstance(rows, list):
            raise SecCompanyConceptNormalizationError("UNIT_ROWS_NOT_LIST:" + unit)
        for raw_row in rows:
            if not isinstance(raw_row, Mapping):
                raise SecCompanyConceptNormalizationError("FACT_ROW_NOT_OBJECT")
            for required in ("val", "end", "accn", "fy", "fp", "form", "filed"):
                if required not in raw_row:
                    raise SecCompanyConceptNormalizationError(
                        "FACT_FIELD_MISSING:" + required
                    )
            subject = f"XBRL_FACT:{qname}:{ordinal}"
            row = dict(raw_row)
            facts.extend([
                {"subject": subject, "predicate": "val", "object": deepcopy(row["val"])},
                {"subject": subject, "predicate": "unit", "object": unit},
                {"subject": subject, "predicate": "end", "object": deepcopy(row["end"])},
                {"subject": subject, "predicate": "accn", "object": deepcopy(row["accn"])},
                {"subject": subject, "predicate": "fy", "object": deepcopy(row["fy"])},
                {"subject": subject, "predicate": "fp", "object": deepcopy(row["fp"])},
                {"subject": subject, "predicate": "form", "object": deepcopy(row["form"])},
                {"subject": subject, "predicate": "filed", "object": deepcopy(row["filed"])},
            ])
            for optional in ("start", "frame"):
                if optional in row and row[optional] is not None:
                    facts.append({
                        "subject": subject,
                        "predicate": optional,
                        "object": deepcopy(row[optional]),
                    })
            ordinal += 1

    if ordinal == 0:
        raise SecCompanyConceptNormalizationError("NO_FACT_ROWS")

    return {
        "schema": SCHEMA,
        "status": "PASS__SOURCE_NATIVE_SEC_COMPANYCONCEPT_NORMALIZED",
        "source_native_identity_extracted": True,
        "source_url": source_url,
        "source_sha256": source_sha,
        "cik": cik_int,
        "cik10": url_cik,
        "entity_name": " ".join(entity_name.split()),
        "taxonomy": taxonomy,
        "tag": tag,
        "concept_qname": qname,
        "semantic_contract": {
            "facts": facts,
            "fact_row_count": ordinal,
        },
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "fuzzy_matching_used": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = [
    "SCHEMA",
    "SecCompanyConceptNormalizationError",
    "normalize_companyconcept",
]
