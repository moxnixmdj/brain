#!/usr/bin/env python3
"""Bounded release-relative FASB US-GAAP metadata for one inline-XBRL fact.

This module consumes the occurrence-local QName anchor produced by
sec_inline_xbrl_fact_anchor_v1 and binds a standard us-gaap concept to exact
metadata from the matching official FASB taxonomy release.

V1 proves only source-native taxonomy metadata:
- exact namespace release and local concept name;
- schema-declared type/substitution-group/period/balance/abstract/nillable fields;
- exact documentation label from the matching release linkbase.

It does not infer custom-concept meaning, nearby visible-label semantics,
free-text policy atoms, ontology class membership, policy adequacy, or terminal truth.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_FASB_RELEASE_METADATA_V1"
ANCHOR_SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_SOURCE_NATIVE_FACT_ANCHOR_V1"
_ALLOWED_RELEASES = {"2024", "2025", "2026"}
_US_GAAP_NS_RE = re.compile(r"^http://fasb\.org/us-gaap/(2024|2025|2026)$")
_LOCAL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,255}$")
MAX_XSD_BYTES = 8_000_000
MAX_DOC_BYTES = 20_000_000
_XS = "http://www.w3.org/2001/XMLSchema"
_XBRLI = "http://www.xbrl.org/2003/instance"
_LINK = "http://www.xbrl.org/2003/linkbase"
_XLINK = "http://www.w3.org/1999/xlink"
_DOC_ROLE = "http://www.xbrl.org/2003/role/documentation"


class TaxonomyMetadataError(RuntimeError):
    pass


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise TaxonomyMetadataError("PATH_OUTSIDE_REPOSITORY")
    return path


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _release(namespace_uri: str) -> str:
    match = _US_GAAP_NS_RE.fullmatch(str(namespace_uri or "").strip())
    if match is None or match.group(1) not in _ALLOWED_RELEASES:
        raise TaxonomyMetadataError("US_GAAP_NAMESPACE_RELEASE_OUTSIDE_V1")
    return match.group(1)


def _local(value: Any) -> str:
    text = str(value or "").strip()
    if not _LOCAL_RE.fullmatch(text):
        raise TaxonomyMetadataError("CONCEPT_LOCAL_NAME_INVALID")
    return text


def canonical_urls(release: str) -> tuple[str, str]:
    base = f"https://xbrl.fasb.org/us-gaap/{release}/elts"
    return (
        f"{base}/us-gaap-{release}.xsd",
        f"{base}/us-gaap-doc-{release}.xml",
    )


def _fetch(url: str, timeout: int, max_bytes: int) -> tuple[bytes, str, str, int]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProjectBrain/1.0 taxonomy-metadata",
            "Accept": "application/xml,text/xml,*/*",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        status = int(getattr(response, "status", 200))
        raw = response.read(max_bytes + 1)
        final_url = str(response.geturl())
        content_type = str(response.headers.get("Content-Type") or "")
    return raw, final_url, content_type, status


def _safe_xml(raw: bytes, name: str) -> ET.Element:
    lowered = raw[:4096].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise TaxonomyMetadataError(name + "_DTD_OR_ENTITY_FORBIDDEN")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise TaxonomyMetadataError(name + "_XML_INVALID") from exc


def _schema_metadata(raw: bytes, namespace_uri: str, local_name: str) -> dict[str, Any]:
    root = _safe_xml(raw, "XSD")
    if root.tag != f"{{{_XS}}}schema":
        raise TaxonomyMetadataError("XSD_ROOT_SCHEMA_REQUIRED")
    if root.attrib.get("targetNamespace") != namespace_uri:
        raise TaxonomyMetadataError("XSD_TARGET_NAMESPACE_MISMATCH")
    rows = [
        node
        for node in root.findall(f".//{{{_XS}}}element")
        if node.attrib.get("name") == local_name
    ]
    if len(rows) != 1:
        raise TaxonomyMetadataError("XSD_CONCEPT_NOT_UNIQUE")
    node = rows[0]
    element_id = str(node.attrib.get("id") or "").strip()
    if not element_id:
        raise TaxonomyMetadataError("XSD_CONCEPT_ID_REQUIRED")
    out: dict[str, Any] = {
        "element_id": element_id,
        "name": local_name,
    }
    mapping = {
        "type": "xsd_type",
        "substitutionGroup": "substitution_group",
        f"{{{_XBRLI}}}periodType": "period_type",
        f"{{{_XBRLI}}}balance": "balance",
        "abstract": "abstract",
        "nillable": "nillable",
    }
    for src, dst in mapping.items():
        value = node.attrib.get(src)
        if value is not None:
            out[dst] = str(value)
    return out


def _documentation(raw: bytes, release: str, element_id: str) -> str:
    root = _safe_xml(raw, "DOC")
    expected_suffix = f"us-gaap-{release}.xsd#{element_id}"
    candidates: set[str] = set()
    for link in root.findall(f".//{{{_LINK}}}labelLink"):
        loc_by_label: dict[str, str] = {}
        docs_by_label: dict[str, str] = {}
        arcs: list[tuple[str, str]] = []
        for loc in link.findall(f"{{{_LINK}}}loc"):
            label = str(loc.attrib.get(f"{{{_XLINK}}}label") or "").strip()
            href = str(loc.attrib.get(f"{{{_XLINK}}}href") or "").strip()
            if label and href:
                loc_by_label[label] = href
        for label_node in link.findall(f"{{{_LINK}}}label"):
            role = str(label_node.attrib.get(f"{{{_XLINK}}}role") or "").strip()
            label = str(label_node.attrib.get(f"{{{_XLINK}}}label") or "").strip()
            if role != _DOC_ROLE or not label:
                continue
            text = " ".join("".join(label_node.itertext()).split())
            if text:
                docs_by_label[label] = text
        for arc in link.findall(f"{{{_LINK}}}labelArc"):
            left = str(arc.attrib.get(f"{{{_XLINK}}}from") or "").strip()
            right = str(arc.attrib.get(f"{{{_XLINK}}}to") or "").strip()
            if left and right:
                arcs.append((left, right))
        for left, right in arcs:
            href = loc_by_label.get(left)
            doc = docs_by_label.get(right)
            if href is not None and href.endswith(expected_suffix) and doc:
                candidates.add(doc)
    if len(candidates) != 1:
        raise TaxonomyMetadataError("DOCUMENTATION_LABEL_NOT_UNIQUE")
    return next(iter(candidates))


def _load_anchor(path: pathlib.Path, ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != ANCHOR_SCHEMA:
        raise TaxonomyMetadataError("ANCHOR_SCHEMA_INVALID")
    if doc.get("source_native_fact_identity_proved") is not True:
        raise TaxonomyMetadataError("ANCHOR_IDENTITY_NOT_PROVED")
    anchors = doc.get("anchors")
    if not isinstance(anchors, list):
        raise TaxonomyMetadataError("ANCHORS_REQUIRED")
    matches = [x for x in anchors if isinstance(x, Mapping) and x.get("ordinal") == ordinal]
    if len(matches) != 1:
        raise TaxonomyMetadataError("ANCHOR_ORDINAL_NOT_UNIQUE")
    return doc, dict(matches[0])


def _contract(
    *,
    anchor_doc: Mapping[str, Any],
    anchor: Mapping[str, Any],
    metadata: Mapping[str, Any],
    documentation: str,
    xsd_path: str,
    xsd_sha256: str,
    xsd_url: str,
    doc_path: str,
    doc_sha256: str,
    doc_url: str,
) -> dict[str, Any]:
    concept_id = (
        "XBRL_CONCEPT:{"
        + str(anchor["namespace_uri"])
        + "}"
        + str(anchor["local_name"])
    )
    occurrence_id = "IX_FACT:" + str(anchor["ordinal"])
    anchor_source = {
        "path": str(anchor_doc["source_path"]),
        "artifact": str(anchor_doc["source_sha256"]),
        "uri": str(anchor_doc["source_url"]),
        "observation_id": occurrence_id,
        "span": [anchor["source_line"], anchor["source_column"]],
    }
    xsd_source = {"path": xsd_path, "artifact": xsd_sha256, "uri": xsd_url}
    doc_source = {"path": doc_path, "artifact": doc_sha256, "uri": doc_url}
    facts = [
        {"subject": concept_id, "predicate": "taxonomy_release", "object": metadata["release"], "source": xsd_source},
        {"subject": concept_id, "predicate": "element_id", "object": metadata["element_id"], "source": xsd_source},
        {"subject": concept_id, "predicate": "documentation_label", "object": documentation, "source": doc_source},
    ]
    for key in ("xsd_type", "substitution_group", "period_type", "balance", "abstract", "nillable"):
        if key in metadata:
            facts.append({"subject": concept_id, "predicate": key, "object": metadata[key], "source": xsd_source})
    return {
        "entities": [
            {"id": occurrence_id, "type": "INLINE_XBRL_FACT_OCCURRENCE", "source": anchor_source},
            {"id": concept_id, "type": "XBRL_STANDARD_TAXONOMY_CONCEPT", "source": xsd_source},
        ],
        "facts": facts,
        "relations": [
            {
                "subject": occurrence_id,
                "predicate": "source_declares_xbrl_concept",
                "object": concept_id,
                "source": anchor_source,
            },
            {
                "subject": concept_id,
                "predicate": "documented_by_exact_taxonomy_release",
                "object": metadata["release"],
                "source": doc_source,
            },
        ],
        "templates": [],
        "ambiguities": [],
    }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    anchor_path = _safe_path(root, args.get("anchor_semantic_path"))
    xsd_path = _safe_path(root, args.get("xsd_output_path"))
    doc_path = _safe_path(root, args.get("documentation_output_path"))
    out_path = _safe_path(root, args.get("metadata_output_path"))
    try:
        ordinal = int(args.get("fact_ordinal"))
    except Exception as exc:
        raise TaxonomyMetadataError("FACT_ORDINAL_INVALID") from exc
    if ordinal < 0:
        raise TaxonomyMetadataError("FACT_ORDINAL_INVALID")

    anchor_doc, anchor = _load_anchor(anchor_path, ordinal)
    namespace_uri = str(anchor.get("namespace_uri") or "").strip()
    local_name = _local(anchor.get("local_name"))
    release = _release(namespace_uri)
    xsd_url, doc_url = canonical_urls(release)

    timeout = max(2, min(int(args.get("timeout_s", 30)), 60))
    xsd_raw, xsd_final, xsd_ctype, xsd_status = _fetch(xsd_url, timeout, MAX_XSD_BYTES)
    doc_raw, doc_final, doc_ctype, doc_status = _fetch(doc_url, timeout, MAX_DOC_BYTES)
    for expected, final, status, raw, limit, name in (
        (xsd_url, xsd_final, xsd_status, xsd_raw, MAX_XSD_BYTES, "XSD"),
        (doc_url, doc_final, doc_status, doc_raw, MAX_DOC_BYTES, "DOC"),
    ):
        if status != 200:
            raise TaxonomyMetadataError(name + "_HTTP_STATUS:" + str(status))
        if final != expected:
            raise TaxonomyMetadataError(name + "_FINAL_URL_MISMATCH")
        if len(raw) > limit:
            raise TaxonomyMetadataError(name + "_BODY_TOO_LARGE")

    schema = _schema_metadata(xsd_raw, namespace_uri, local_name)
    documentation = _documentation(doc_raw, release, schema["element_id"])
    metadata = {"release": release, **schema}

    xsd_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    xsd_path.write_bytes(xsd_raw)
    doc_path.write_bytes(doc_raw)
    xsd_rel = str(xsd_path.relative_to(root)).replace("\\", "/")
    doc_rel = str(doc_path.relative_to(root)).replace("\\", "/")
    xsd_sha256 = _sha(xsd_raw)
    doc_sha256 = _sha(doc_raw)

    contract = _contract(
        anchor_doc=anchor_doc,
        anchor=anchor,
        metadata=metadata,
        documentation=documentation,
        xsd_path=xsd_rel,
        xsd_sha256=xsd_sha256,
        xsd_url=xsd_url,
        doc_path=doc_rel,
        doc_sha256=doc_sha256,
        doc_url=doc_url,
    )
    result = {
        "schema": SCHEMA,
        "status": "PASS__EXACT_FASB_RELEASE_METADATA_BOUND_TO_INLINE_FACT",
        "anchor_semantic_path": str(anchor_path.relative_to(root)).replace("\\", "/"),
        "fact_ordinal": ordinal,
        "namespace_uri": namespace_uri,
        "local_name": local_name,
        "release": release,
        "xsd_url": xsd_url,
        "xsd_path": xsd_rel,
        "xsd_sha256": xsd_sha256,
        "xsd_content_type": xsd_ctype,
        "documentation_url": doc_url,
        "documentation_path": doc_rel,
        "documentation_sha256": doc_sha256,
        "documentation_content_type": doc_ctype,
        "concept_metadata": metadata,
        "documentation_label": documentation,
        "semantic_contract": contract,
        "release_relative_standard_concept_metadata_proved": True,
        "custom_concept_semantics_claimed": False,
        "nearby_visible_label_semantics_claimed": False,
        "free_text_policy_semantics_claimed": False,
        "ontology_classification_claimed": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
