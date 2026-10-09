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


def _row_count(units: Any) -> int:
    if not isinstance(units, Mapping) or not units:
        raise RuntimeError("UNITS_REQUIRED")
    total = 0
    for unit, rows in units.items():
        if (
            not isinstance(unit, str)
            or not unit.strip()
            or not isinstance(rows, list)
        ):
            raise RuntimeError("UNITS_INVALID")
        total += len(rows)
    if total <= 0:
        raise RuntimeError("NO_FACT_ROWS")
    return total


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
        count = _row_count(payload.get("units"))

        expected = {
            "source_url": url,
            "source_path": str(raw_file.relative_to(root)).replace("\\", "/"),
            "source_sha256": sha,
            "cik": cik10,
            "taxonomy": taxonomy,
            "tag": tag,
            "concept_qname": qname,
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
            entities = contract.get("entities")
            facts = contract.get("facts")
            relations = contract.get("relations")
            if (
                not isinstance(entities, list)
                or not isinstance(facts, list)
                or not isinstance(relations, list)
            ):
                errors.append("SEMANTIC_CONTRACT_COLLECTIONS_INVALID")
            else:
                concept_id = "XBRL_CONCEPT:" + qname
                issuer_id = "SEC_CIK:" + cik10
                entity_ids = {
                    x.get("id") for x in entities if isinstance(x, Mapping)
                }
                if concept_id not in entity_ids:
                    errors.append("CONCEPT_ENTITY_MISSING")
                if issuer_id not in entity_ids:
                    errors.append("ISSUER_ENTITY_MISSING")
                expected_fact = {
                    ("taxonomy", taxonomy),
                    ("tag", tag),
                    ("concept_qname", qname),
                }
                observed = {
                    (x.get("predicate"), x.get("object"))
                    for x in facts
                    if isinstance(x, Mapping)
                    and x.get("subject") == concept_id
                }
                if not expected_fact.issubset(observed):
                    errors.append("CONCEPT_IDENTITY_FACTS_INCOMPLETE")
                instantiates = [
                    x
                    for x in relations
                    if isinstance(x, Mapping)
                    and x.get("predicate") == "instantiates_xbrl_concept"
                    and x.get("object") == concept_id
                ]
                if len(instantiates) != count:
                    errors.append("FACT_TO_CONCEPT_RELATION_COUNT_MISMATCH")

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
            "semantic_authority_claimed": False,
            "terminal_authority": False,
        }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    return verify(
        root=root,
        raw_path=args.get("raw_path"),
        semantic_path=args.get("semantic_path"),
    )
