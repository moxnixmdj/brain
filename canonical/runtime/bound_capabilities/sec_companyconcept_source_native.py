#!/usr/bin/env python3
"""Bounded SEC CompanyConcept source-native semantic extraction.

This capability fetches exactly one standardized SEC XBRL concept for one filer
from data.sec.gov, preserves the exact response bytes, and emits a deterministic
source-traceable semantic contract. It does not infer meaning from visible prose,
does not cover custom extension taxonomies, and has no decision/terminal authority.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_SEMANTICS_V1"
_ALLOWED_TAXONOMIES = {"us-gaap", "ifrs-full", "dei", "srt"}
_TAG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,255}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_BYTES = 4_000_000


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
    try:
        cik = int(value)
    except Exception as exc:
        raise RuntimeError("CIK_INVALID") from exc
    if cik <= 0 or cik > 9_999_999_999:
        raise RuntimeError("CIK_INVALID")
    return f"{cik:010d}"


def _taxonomy(value: Any) -> str:
    text = str(value or "").strip()
    if text not in _ALLOWED_TAXONOMIES:
        raise RuntimeError("TAXONOMY_OUTSIDE_V1_STANDARD_SCOPE")
    return text


def _tag(value: Any) -> str:
    text = str(value or "").strip()
    if not _TAG_RE.fullmatch(text):
        raise RuntimeError("TAG_INVALID")
    return text


def _user_agent(value: Any) -> str:
    text = _clean_text(value, "SEC_USER_AGENT", 240)
    parts = text.split()
    if len(parts) < 2 or not any(
        _EMAIL_RE.fullmatch(x.strip("<>()[]{};,") or "") for x in parts
    ):
        raise RuntimeError("SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED")
    return text


def canonical_url(cik10: str, taxonomy: str, tag: str) -> str:
    return (
        "https://data.sec.gov/api/xbrl/companyconcept/"
        f"CIK{cik10}/{taxonomy}/{urllib.parse.quote(tag, safe='._-')}.json"
    )


def _fetch(url: str, user_agent: str, timeout: int, max_bytes: int):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", 200))
        raw = response.read(max_bytes + 1)
        final_url = str(response.geturl())
        content_type = str(response.headers.get("Content-Type") or "")
    return raw, final_url, content_type, status


def _fact_rows(units: Any, max_rows: int) -> list[dict[str, Any]]:
    if not isinstance(units, Mapping) or not units:
        raise RuntimeError("UNITS_REQUIRED")
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for unit, values in sorted(units.items(), key=lambda x: str(x[0])):
        unit = _clean_text(unit, "UNIT", 128)
        if not isinstance(values, list):
            raise RuntimeError("UNIT_FACTS_NOT_ARRAY:" + unit)
        for raw in values:
            if len(rows) >= max_rows:
                raise RuntimeError("FACT_ROW_LIMIT_EXCEEDED")
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


def _semantic_contract(
    *,
    cik10: str,
    entity_name: str,
    taxonomy: str,
    tag: str,
    label: str | None,
    description: str | None,
    rows: list[dict[str, Any]],
    source_path: str,
    source_sha256: str,
    source_url: str,
) -> dict[str, Any]:
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


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    config_path = _safe_path(root, args.get("config_path"))
    raw_path = _safe_path(root, args.get("raw_output_path"))
    semantic_path = _safe_path(root, args.get("semantic_output_path"))
    if not config_path.is_file() or config_path.suffix.lower() != ".json":
        raise RuntimeError("CONFIG_JSON_REQUIRED")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    cik10 = _cik10(config.get("cik"))
    taxonomy = _taxonomy(config.get("taxonomy"))
    tag = _tag(config.get("tag"))
    user_agent = _user_agent(config.get("sec_user_agent"))
    url = canonical_url(cik10, taxonomy, tag)
    timeout = max(2, min(int(args.get("timeout_s", 30)), 60))
    max_bytes = max(1024, min(int(args.get("max_bytes", MAX_BYTES)), MAX_BYTES))
    max_rows = max(1, min(int(args.get("max_rows", 2000)), 10_000))

    raw, final_url, content_type, status = _fetch(
        url, user_agent, timeout, max_bytes
    )
    if status != 200:
        raise RuntimeError("HTTP_STATUS:" + str(status))
    if final_url != url:
        raise RuntimeError("SEC_FINAL_URL_MISMATCH")
    if len(raw) > max_bytes:
        raise RuntimeError("HTTP_BODY_TOO_LARGE")
    if "json" not in content_type.lower():
        raise RuntimeError("SEC_CONTENT_TYPE_NOT_JSON")

    payload = json.loads(raw.decode("utf-8"))
    if _cik10(payload.get("cik")) != cik10:
        raise RuntimeError("PAYLOAD_CIK_MISMATCH")
    if _taxonomy(payload.get("taxonomy")) != taxonomy:
        raise RuntimeError("PAYLOAD_TAXONOMY_MISMATCH")
    if _tag(payload.get("tag")) != tag:
        raise RuntimeError("PAYLOAD_TAG_MISMATCH")
    entity_name = _clean_text(payload.get("entityName"), "ENTITY_NAME", 512)
    label = payload.get("label")
    description = payload.get("description")
    label = _clean_text(label, "LABEL", 1000) if label is not None else None
    description = (
        _clean_text(description, "DESCRIPTION", 8000)
        if description is not None
        else None
    )
    rows = _fact_rows(payload.get("units"), max_rows)

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_path = str(raw_path.relative_to(root)).replace("\\", "/")
    qname = taxonomy + ":" + tag
    semantic = {
        "schema": SCHEMA,
        "status": "PASS__SEC_COMPANYCONCEPT_SOURCE_NATIVE_IDENTITY_EXTRACTED",
        "source_url": url,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "http_status": status,
        "content_type": content_type,
        "cik": cik10,
        "entity_name": entity_name,
        "taxonomy": taxonomy,
        "tag": tag,
        "concept_qname": qname,
        "label": label,
        "description": description,
        "fact_row_count": len(rows),
        "semantic_contract": _semantic_contract(
            cik10=cik10,
            entity_name=entity_name,
            taxonomy=taxonomy,
            tag=tag,
            label=label,
            description=description,
            rows=rows,
            source_path=source_path,
            source_sha256=source_sha256,
            source_url=url,
        ),
        "source_native_identity_extracted": True,
        "semantic_authority_claimed": False,
        "custom_taxonomy_covered": False,
        "raw_prose_wsd_claimed": False,
        "terminal_authority": False,
    }
    semantic_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_path.write_text(
        json.dumps(semantic, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "adapter": "sec_companyconcept_source_native",
        "concept_qname": qname,
        "fact_row_count": len(rows),
        "raw_output_path": source_path,
        "raw_output_sha256": source_sha256,
        "semantic_output_path": str(semantic_path.relative_to(root)).replace(
            "\\", "/"
        ),
        "semantic_output_sha256": hashlib.sha256(
            semantic_path.read_bytes()
        ).hexdigest(),
        "source_native_identity_extracted": True,
        "semantic_authority_claimed": False,
        "custom_taxonomy_covered": False,
        "raw_prose_wsd_claimed": False,
        "terminal_authority": False,
        "output_verified": False,
        "independent_verification_required": True,
    }
