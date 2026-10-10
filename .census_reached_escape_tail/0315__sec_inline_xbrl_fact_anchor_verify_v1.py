#!/usr/bin/env python3
"""Independent raw-byte verification for SEC inline-XBRL fact anchors V1.

This verifier does not import the producer. It re-derives fact start-tags with
a separate regex scanner and proves only occurrence -> QName identity.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.parse
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_FACT_ANCHOR_VERIFY_V1"
PRODUCER_SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_SOURCE_NATIVE_FACT_ANCHOR_V1"
_INLINE_NAMESPACES = {
    "http://www.xbrl.org/2013/inlineXBRL",
    "http://www.xbrl.org/2008/inlineXBRL",
}
_XMLNS_RE = re.compile(
    r"""\bxmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_HTML_START_RE = re.compile(r"""<html\b[^<>]*>""", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(
    r"""<([A-Za-z_][A-Za-z0-9_.-]*):(nonfraction|nonnumeric)\b([^<>]*?)>""",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(
    r"""([A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*(["'])(.*?)\2""",
    re.DOTALL,
)
_QNAME_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*):([A-Za-z_][A-Za-z0-9_.-]*)$")


class VerifyError(RuntimeError):
    pass


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise VerifyError("PATH_OUTSIDE_REPOSITORY")
    return path


def _filing_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urllib.parse.urlsplit(text)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.sec.gov"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/Archives/edgar/data/")
        or not parsed.path.lower().endswith((".htm", ".html"))
    ):
        raise VerifyError("SEC_ARCHIVE_INLINE_FILING_URL_REQUIRED")
    return urllib.parse.urlunsplit(("https", "www.sec.gov", parsed.path, "", ""))


def _namespace_map(text: str) -> dict[str, str]:
    root_match = _HTML_START_RE.search(text)
    if root_match is None:
        raise VerifyError("ROOT_HTML_START_TAG_REQUIRED")
    root_tag = root_match.group(0)
    out: dict[str, str] = {}
    for match in _XMLNS_RE.finditer(root_tag):
        prefix = match.group(1)
        uri = match.group(2).strip()
        prior = out.get(prefix)
        if prior is not None and prior != uri:
            raise VerifyError("ROOT_NAMESPACE_PREFIX_REBOUND:" + prefix)
        out[prefix] = uri
    if not any(uri in _INLINE_NAMESPACES for uri in out.values()):
        raise VerifyError("INLINE_XBRL_NAMESPACE_REQUIRED")

    # V1 refuses scoped namespace mutation instead of applying declarations
    # outside their lexical scope. All QName prefixes must be root-declared.
    root_start, root_end = root_match.span()
    for match in _XMLNS_RE.finditer(text):
        if root_start <= match.start() and match.end() <= root_end:
            continue
        raise VerifyError("NESTED_NAMESPACE_DECLARATION_OUTSIDE_V1:" + match.group(1))
    return out

def _line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    prior = text.rfind("\n", 0, offset)
    column = offset if prior < 0 else offset - prior - 1
    return line, column


def _scan(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerifyError("INLINE_FILING_UTF8_REQUIRED") from exc
    namespaces = _namespace_map(text)
    ix_prefixes = {
        p.casefold() for p, uri in namespaces.items() if uri in _INLINE_NAMESPACES
    }
    rows: list[dict[str, Any]] = []
    for match in _TAG_RE.finditer(text):
        tag_prefix = match.group(1)
        if tag_prefix.casefold() not in ix_prefixes:
            continue
        local = match.group(2).casefold()
        raw_tag = match.group(0)
        attrs: dict[str, str] = {}
        for am in _ATTR_RE.finditer(match.group(3)):
            key = am.group(1).casefold()
            if key in attrs:
                raise VerifyError("DUPLICATE_INLINE_FACT_ATTRIBUTE:" + key)
            attrs[key] = am.group(3)
        lexical_qname = str(attrs.get("name") or "").strip()
        qm = _QNAME_RE.fullmatch(lexical_qname)
        if qm is None:
            raise VerifyError("INLINE_FACT_QNAME_INVALID")
        prefix, local_name = qm.groups()
        namespace_uri = namespaces.get(prefix)
        if namespace_uri is None:
            raise VerifyError("INLINE_FACT_QNAME_PREFIX_UNBOUND:" + prefix)
        context_ref = str(attrs.get("contextref") or "").strip()
        if not context_ref:
            raise VerifyError("INLINE_FACT_CONTEXTREF_REQUIRED")
        line, column = _line_col(text, match.start())
        row: dict[str, Any] = {
            "ordinal": len(rows),
            "ix_kind": local,
            "lexical_qname": lexical_qname,
            "namespace_uri": namespace_uri,
            "local_name": local_name,
            "context_ref": context_ref,
            "source_line": line,
            "source_column": column,
            "start_tag_sha256": hashlib.sha256(raw_tag.encode("utf-8")).hexdigest(),
        }
        for source_key, target_key in (
            ("id", "xml_id"),
            ("unitref", "unit_ref"),
            ("decimals", "decimals"),
            ("precision", "precision"),
            ("scale", "scale"),
            ("sign", "sign"),
            ("format", "format"),
        ):
            value = attrs.get(source_key)
            if value is not None and str(value).strip():
                row[target_key] = str(value).strip()
        rows.append(row)
    if not rows:
        raise VerifyError("NO_SUPPORTED_INLINE_XBRL_FACTS")
    return rows


def _concept_id(row: Mapping[str, Any]) -> str:
    return "XBRL_CONCEPT:{" + str(row["namespace_uri"]) + "}" + str(row["local_name"])


def _expected_contract(
    *,
    rows: list[dict[str, Any]],
    source_path: str,
    source_sha256: str,
    source_url: str,
) -> dict[str, Any]:
    base_source = {"path": source_path, "artifact": source_sha256, "uri": source_url}
    concepts: set[str] = set()
    entities: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for row in rows:
        cid = _concept_id(row)
        if cid not in concepts:
            concepts.add(cid)
            entities.append({"id": cid, "type": "XBRL_CONCEPT_IDENTITY", "source": base_source})
            facts.extend(
                [
                    {
                        "subject": cid,
                        "predicate": "namespace_uri",
                        "object": row["namespace_uri"],
                        "source": base_source,
                    },
                    {
                        "subject": cid,
                        "predicate": "local_name",
                        "object": row["local_name"],
                        "source": base_source,
                    },
                ]
            )
        fid = "IX_FACT:" + str(row["ordinal"])
        source = {
            **base_source,
            "observation_id": fid,
            "span": [row["source_line"], row["source_column"]],
        }
        entities.append({"id": fid, "type": "INLINE_XBRL_FACT_OCCURRENCE", "source": source})
        relations.append(
            {
                "subject": fid,
                "predicate": "source_declares_xbrl_concept",
                "object": cid,
                "source": source,
            }
        )
        for key in (
            "lexical_qname",
            "context_ref",
            "ix_kind",
            "xml_id",
            "unit_ref",
            "decimals",
            "precision",
            "scale",
            "sign",
            "format",
            "start_tag_sha256",
        ):
            if key in row:
                facts.append(
                    {
                        "subject": fid,
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
        semantic = json.loads(semantic_file.read_text(encoding="utf-8"))
        if semantic.get("schema") != PRODUCER_SCHEMA:
            errors.append("PRODUCER_SCHEMA_INVALID")
        sha = hashlib.sha256(raw).hexdigest()
        source_path = str(raw_file.relative_to(root)).replace("\\", "/")
        source_url = _filing_url(semantic.get("source_url"))
        rows = _scan(raw)

        expected_fields = {
            "source_path": source_path,
            "source_sha256": sha,
            "fact_anchor_count": len(rows),
            "anchors": rows,
        }
        for key, value in expected_fields.items():
            if semantic.get(key) != value:
                errors.append("SEMANTIC_FIELD_MISMATCH:" + key)

        if semantic.get("source_native_fact_identity_proved") is not True:
            errors.append("SOURCE_NATIVE_IDENTITY_FLAG_MISSING")
        for key in (
            "nearby_visible_label_semantics_claimed",
            "custom_concept_domain_semantics_claimed",
            "raw_prose_wsd_claimed",
            "policy_adequacy_authority",
            "semantic_truth_authority",
            "terminal_authority",
        ):
            if semantic.get(key) is not False:
                errors.append("AUTHORITY_BOUNDARY_INVALID:" + key)
        if semantic.get("terminal_credit_delta") != 0:
            errors.append("TERMINAL_CREDIT_FORBIDDEN")

        expected_contract = _expected_contract(
            rows=rows,
            source_path=source_path,
            source_sha256=sha,
            source_url=source_url,
        )
        if semantic.get("semantic_contract") != expected_contract:
            errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_DERIVED_FROM_SOURCE_BYTES")

        return {
            "schema": SCHEMA,
            "verified": not errors,
            "status": (
                "PASS__INLINE_XBRL_FACT_ANCHORS_REDERIVED_FROM_RAW_BYTES"
                if not errors
                else "FAIL_CLOSED"
            ),
            "errors": sorted(set(errors)),
            "producer_independent": True,
            "full_contract_rederived_from_raw_bytes": True,
            "source_sha256": sha,
            "fact_anchor_count": len(rows),
            "semantic_truth_authority": False,
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
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    return verify(
        root=root,
        raw_path=args.get("raw_path"),
        semantic_path=args.get("semantic_path"),
    )
