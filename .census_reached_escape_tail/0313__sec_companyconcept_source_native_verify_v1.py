#!/usr/bin/env python3
"""Independent byte-to-semantic verification for SEC CompanyConcept V1."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.parse
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_VERIFY_V1"
PRODUCER_SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_SEMANTICS_V1"
_ALLOWED_TAXONOMIES = {"us-gaap", "ifrs-full", "dei", "srt"}
_TAG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,255}$")


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return path


def _clean_text(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(name + "_REQUIRED")
    text = " ".join(value.strip().split())
    if len(text) > limit:
        raise RuntimeError(name + "_TOO_LONG")
    return text


def _cik10(value: Any) -> str:
    if isinstance(value, bool):
        raise RuntimeError("CIK_INVALID")
    n = int(value)
    if n <= 0 or n > 9_999_999_999:
        raise RuntimeError("CIK_INVALID")
    return f"{n:010d}"


def _canonical_url(cik10: str, taxonomy: str, tag: str) -> str:
    return (
        "https://data.sec.gov/api/xbrl/companyconcept/"
        f"CIK{cik10}/{taxonomy}/{urllib.parse.quote(tag, safe='._-')}.json"
    )


def _canonical_rows(units: Any) -> list[dict[str, Any]]:
    if not isinstance(units, Mapping) or not units:
        raise RuntimeError("UNITS_REQUIRED")
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for unit, values in sorted(units.items(), key=lambda x: str(x[0])):
        unit = _clean_text(unit, "UNIT", 128)
        if not isinstance(values, list):
            raise RuntimeError("UNIT_FACTS_NOT_ARRAY:" + unit)
        for raw in values:
            if not isinstance(raw, Mapping):
                raise RuntimeError(f"FACT_ROW_NOT_OBJECT:{ordinal}")
            if "val" not in raw:
                raise RuntimeError(f"FACT_VALUE_MISSING:{ordinal}")
            row: dict[str, Any] = {"unit": unit, "val": raw["val"]}
            for key in ("start", "end", "filed", "accn", "fp", "form", "frame"):
                if raw.get(key) is not None:
                    row[key] = _clean_text(
                        raw[key], f"FACT_{key.upper()}:{ordinal}", 256
                    )
            if raw.get("fy") is not None:
                if isinstance(raw["fy"], bool) or not isinstance(raw["fy"], int):
                    raise RuntimeError(f"FACT_FY_INVALID:{ordinal}")
                row["fy"] = raw["fy"]
            for required in ("end", "filed", "accn", "form"):
                if required not in row:
                    raise RuntimeError(
                        f"FACT_REQUIRED_METADATA_MISSING:{ordinal}:{required}"
                    )
            rows.append(row)
            ordinal += 1
    if not rows:
        raise RuntimeError("NO_FACT_ROWS")
    rows.sort(
        key=lambda r: (
            str(r.get("filed", "")),
            str(r.get("accn", "")),
            str(r.get("start", "")),
            str(r.get("end", "")),
            str(r.get("unit", "")),
            json.dumps(
                r.get("val"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )
    )
    return rows


def _expected_contract(
    *,
    payload: Mapping[str, Any],
    source_path: str,
    source_sha256: str,
    source_url: str,
) -> dict[str, Any]:
    cik10 = _cik10(payload.get("cik"))
    taxonomy = str(payload.get("taxonomy") or "").strip()
    tag = str(payload.get("tag") or "").strip()
    if taxonomy not in _ALLOWED_TAXONOMIES:
        raise RuntimeError("TAXONOMY_OUTSIDE_V1_STANDARD_SCOPE")
    if not _TAG_RE.fullmatch(tag):
        raise RuntimeError("TAG_INVALID")
    entity_name = _clean_text(payload.get("entityName"), "ENTITY_NAME", 512)
    label = payload.get("label")
    description = payload.get("description")
    label = _clean_text(label, "LABEL", 1000) if label is not None else None
    description = (
        _clean_text(description, "DESCRIPTION", 8000)
        if description is not None
        else None
    )
    rows = _canonical_rows(payload.get("units"))
    source = {"path": source_path, "artifact": source_sha256, "uri": source_url}
    qname = taxonomy + ":" + tag
    concept_id = "XBRL_CONCEPT:" + qname
    issuer_id = "SEC_CIK:" + cik10

    entities = [
        {"id": issuer_id, "type": "SEC_REPORTING_ENTITY", "source": source},
        {
            "id": concept_id,
            "type": "XBRL_STANDARD_TAXONOMY_CONCEPT",
            "source": source,
        },
    ]
    facts = [
        {
            "subject": issuer_id,
            "predicate": "entity_name",
            "object": entity_name,
            "source": source,
        },
        {
            "subject": concept_id,
            "predicate": "taxonomy",
            "object": taxonomy,
            "source": source,
        },
        {
            "subject": concept_id,
            "predicate": "tag",
            "object": tag,
            "source": source,
        },
        {
            "subject": concept_id,
            "predicate": "concept_qname",
            "object": qname,
            "source": source,
        },
    ]
    if label is not None:
        facts.append(
            {
                "subject": concept_id,
                "predicate": "sec_api_label",
                "object": label,
                "source": source,
            }
        )
    if description is not None:
        facts.append(
            {
                "subject": concept_id,
                "predicate": "sec_api_description",
                "object": description,
                "source": source,
            }
        )

    relations: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        fact_id = f"XBRL_FACT:{qname}:{i}"
        entities.append({"id": fact_id, "type": "XBRL_FACT", "source": source})
        relations.extend(
            [
                {
                    "subject": fact_id,
                    "predicate": "instantiates_xbrl_concept",
                    "object": concept_id,
                    "source": source,
                },
                {
                    "subject": fact_id,
                    "predicate": "reported_by",
                    "object": issuer_id,
                    "source": source,
                },
            ]
        )
        for key in (
            "val",
            "unit",
            "start",
            "end",
            "filed",
            "accn",
            "fy",
            "fp",
            "form",
            "frame",
        ):
            if key in row:
                facts.append(
                    {
                        "subject": fact_id,
                        "predicate": key,
                        "object": row[key],
                        "source": source,
                    }
                )

    return {
        "entities": entities,
        "facts": facts,
        "relations": relations,
        "templates": [],
        "ambiguities": [],
    }


def verify(*, root: Any, raw_path: Any, semantic_path: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    raw_file = _safe_path(root, raw_path)
    semantic_file = _safe_path(root, semantic_path)
    errors: list[str] = []
    try:
        raw = raw_file.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        semantic = json.loads(semantic_file.read_text(encoding="utf-8"))
        if semantic.get("schema") != PRODUCER_SCHEMA:
            errors.append("PRODUCER_SCHEMA_INVALID")

        cik10 = _cik10(payload.get("cik"))
        taxonomy = str(payload.get("taxonomy") or "").strip()
        tag = str(payload.get("tag") or "").strip()
        if taxonomy not in _ALLOWED_TAXONOMIES:
            errors.append("TAXONOMY_OUTSIDE_V1_STANDARD_SCOPE")
        if not _TAG_RE.fullmatch(tag):
            errors.append("TAG_INVALID")
        qname = taxonomy + ":" + tag
        url = _canonical_url(cik10, taxonomy, tag)
        sha = hashlib.sha256(raw).hexdigest()
        rows = _canonical_rows(payload.get("units"))
        count = len(rows)
        source_path = str(raw_file.relative_to(root)).replace("\\", "/")

        expected = {
            "source_url": url,
            "source_path": source_path,
            "source_sha256": sha,
            "cik": cik10,
            "taxonomy": taxonomy,
            "tag": tag,
            "concept_qname": qname,
            "entity_name": _clean_text(payload.get("entityName"), "ENTITY_NAME", 512),
            "label": (
                _clean_text(payload.get("label"), "LABEL", 1000)
                if payload.get("label") is not None else None
            ),
            "description": (
                _clean_text(payload.get("description"), "DESCRIPTION", 8000)
                if payload.get("description") is not None else None
            ),
            "fact_row_count": count,
        }
        for key, value in expected.items():
            if semantic.get(key) != value:
                errors.append("SEMANTIC_FIELD_MISMATCH:" + key)

        if semantic.get("source_native_identity_extracted") is not True:
            errors.append("SOURCE_NATIVE_IDENTITY_FLAG_MISSING")
        if semantic.get("semantic_authority_claimed") is not False:
            errors.append("SEMANTIC_AUTHORITY_MUST_REMAIN_FALSE")
        if semantic.get("custom_taxonomy_covered") is not False:
            errors.append("CUSTOM_TAXONOMY_SCOPE_OVERCLAIM")
        if semantic.get("raw_prose_wsd_claimed") is not False:
            errors.append("RAW_PROSE_WSD_SCOPE_OVERCLAIM")
        if semantic.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_FORBIDDEN")

        contract = semantic.get("semantic_contract")
        if not isinstance(contract, Mapping):
            errors.append("SEMANTIC_CONTRACT_REQUIRED")
        else:
            expected_contract = _expected_contract(
                payload=payload,
                source_path=source_path,
                source_sha256=sha,
                source_url=url,
            )
            if contract != expected_contract:
                errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_DERIVED_FROM_SOURCE_BYTES")

        return {
            "schema": SCHEMA,
            "verified": not errors,
            "status": (
                "PASS__SEC_COMPANYCONCEPT_SOURCE_NATIVE_BYTES_MATCH_SEMANTIC_CONTRACT"
                if not errors
                else "FAIL_CLOSED"
            ),
            "errors": sorted(set(errors)),
            "producer_independent": True,
            "full_contract_rederived_from_raw_bytes": True,
            "source_sha256": sha if "sha" in locals() else None,
            "concept_qname": qname if "qname" in locals() else None,
            "fact_row_count": count if "count" in locals() else None,
            "semantic_authority_claimed": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "verified": False,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "producer_independent": True,
            "full_contract_rederived_from_raw_bytes": True,
            "semantic_authority_claimed": False,
            "terminal_authority": False,
        }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    return verify(
        root=root,
        raw_path=args.get("raw_path"),
        semantic_path=args.get("semantic_path"),
    )
