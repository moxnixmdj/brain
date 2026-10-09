#!/usr/bin/env python3
"""Independent verifier for release-relative FASB metadata bound to inline XBRL."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_FASB_RELEASE_METADATA_VERIFY_V1"
PRODUCER_SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_FASB_RELEASE_METADATA_V1"
ANCHOR_SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_SOURCE_NATIVE_FACT_ANCHOR_V1"
_US_GAAP_NS_RE = re.compile(r"^http://fasb\.org/us-gaap/(2024|2025|2026)$")
_LOCAL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,255}$")
_XS = "http://www.w3.org/2001/XMLSchema"
_XBRLI = "http://www.xbrl.org/2003/instance"
_LINK = "http://www.xbrl.org/2003/linkbase"
_XLINK = "http://www.w3.org/1999/xlink"
_DOC_ROLE = "http://www.xbrl.org/2003/role/documentation"


class VerifyError(RuntimeError):
    pass


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise VerifyError("PATH_OUTSIDE_REPOSITORY")
    return path


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _release(namespace_uri: str) -> str:
    m = _US_GAAP_NS_RE.fullmatch(str(namespace_uri or "").strip())
    if m is None:
        raise VerifyError("US_GAAP_NAMESPACE_RELEASE_OUTSIDE_V1")
    return m.group(1)


def _local(value: Any) -> str:
    text = str(value or "").strip()
    if not _LOCAL_RE.fullmatch(text):
        raise VerifyError("CONCEPT_LOCAL_NAME_INVALID")
    return text


def _urls(release: str) -> tuple[str, str]:
    base = f"https://xbrl.fasb.org/us-gaap/{release}/elts"
    return f"{base}/us-gaap-{release}.xsd", f"{base}/us-gaap-doc-{release}.xml"


def _xml(raw: bytes, name: str) -> ET.Element:
    lowered = raw[:4096].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise VerifyError(name + "_DTD_OR_ENTITY_FORBIDDEN")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise VerifyError(name + "_XML_INVALID") from exc


def _schema(raw: bytes, namespace_uri: str, local_name: str) -> dict[str, Any]:
    root = _xml(raw, "XSD")
    if root.tag != f"{{{_XS}}}schema" or root.attrib.get("targetNamespace") != namespace_uri:
        raise VerifyError("XSD_NAMESPACE_INVALID")
    rows = [n for n in root.findall(f".//{{{_XS}}}element") if n.attrib.get("name") == local_name]
    if len(rows) != 1:
        raise VerifyError("XSD_CONCEPT_NOT_UNIQUE")
    node = rows[0]
    element_id = str(node.attrib.get("id") or "").strip()
    if not element_id:
        raise VerifyError("XSD_CONCEPT_ID_REQUIRED")
    out: dict[str, Any] = {"element_id": element_id, "name": local_name}
    for src, dst in {
        "type":"xsd_type",
        "substitutionGroup":"substitution_group",
        f"{{{_XBRLI}}}periodType":"period_type",
        f"{{{_XBRLI}}}balance":"balance",
        "abstract":"abstract",
        "nillable":"nillable",
    }.items():
        if node.attrib.get(src) is not None:
            out[dst] = str(node.attrib[src])
    return out


def _doc(raw: bytes, release: str, element_id: str) -> str:
    root = _xml(raw, "DOC")
    suffix = f"us-gaap-{release}.xsd#{element_id}"
    found: set[str] = set()
    for link in root.findall(f".//{{{_LINK}}}labelLink"):
        locs: dict[str, str] = {}
        labels: dict[str, str] = {}
        arcs: list[tuple[str, str]] = []
        for n in link.findall(f"{{{_LINK}}}loc"):
            a = str(n.attrib.get(f"{{{_XLINK}}}label") or "").strip()
            b = str(n.attrib.get(f"{{{_XLINK}}}href") or "").strip()
            if a and b:
                locs[a] = b
        for n in link.findall(f"{{{_LINK}}}label"):
            if str(n.attrib.get(f"{{{_XLINK}}}role") or "").strip() != _DOC_ROLE:
                continue
            a = str(n.attrib.get(f"{{{_XLINK}}}label") or "").strip()
            b = " ".join("".join(n.itertext()).split())
            if a and b:
                labels[a] = b
        for n in link.findall(f"{{{_LINK}}}labelArc"):
            a = str(n.attrib.get(f"{{{_XLINK}}}from") or "").strip()
            b = str(n.attrib.get(f"{{{_XLINK}}}to") or "").strip()
            if a and b:
                arcs.append((a, b))
        found.update(labels[b] for a, b in arcs if locs.get(a, "").endswith(suffix) and b in labels)
    if len(found) != 1:
        raise VerifyError("DOCUMENTATION_LABEL_NOT_UNIQUE")
    return next(iter(found))


def _load_anchor(path: pathlib.Path, ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != ANCHOR_SCHEMA or doc.get("source_native_fact_identity_proved") is not True:
        raise VerifyError("ANCHOR_IDENTITY_INVALID")
    anchors = doc.get("anchors")
    if not isinstance(anchors, list):
        raise VerifyError("ANCHORS_REQUIRED")
    rows = [x for x in anchors if isinstance(x, Mapping) and x.get("ordinal") == ordinal]
    if len(rows) != 1:
        raise VerifyError("ANCHOR_ORDINAL_NOT_UNIQUE")
    return doc, dict(rows[0])


def _contract(
    *,
    anchor_doc: Mapping[str, Any],
    anchor: Mapping[str, Any],
    metadata: Mapping[str, Any],
    documentation: str,
    xsd_path: str,
    xsd_sha: str,
    xsd_url: str,
    doc_path: str,
    doc_sha: str,
    doc_url: str,
) -> dict[str, Any]:
    cid = "XBRL_CONCEPT:{" + str(anchor["namespace_uri"]) + "}" + str(anchor["local_name"])
    oid = "IX_FACT:" + str(anchor["ordinal"])
    anchor_source = {
        "path": str(anchor_doc["source_path"]),
        "artifact": str(anchor_doc["source_sha256"]),
        "uri": str(anchor_doc["source_url"]),
        "observation_id": oid,
        "span": [anchor["source_line"], anchor["source_column"]],
    }
    xs = {"path": xsd_path, "artifact": xsd_sha, "uri": xsd_url}
    ds = {"path": doc_path, "artifact": doc_sha, "uri": doc_url}
    facts = [
        {"subject":cid,"predicate":"taxonomy_release","object":metadata["release"],"source":xs},
        {"subject":cid,"predicate":"element_id","object":metadata["element_id"],"source":xs},
        {"subject":cid,"predicate":"documentation_label","object":documentation,"source":ds},
    ]
    for key in ("xsd_type","substitution_group","period_type","balance","abstract","nillable"):
        if key in metadata:
            facts.append({"subject":cid,"predicate":key,"object":metadata[key],"source":xs})
    return {
        "entities":[
            {"id":oid,"type":"INLINE_XBRL_FACT_OCCURRENCE","source":anchor_source},
            {"id":cid,"type":"XBRL_STANDARD_TAXONOMY_CONCEPT","source":xs},
        ],
        "facts":facts,
        "relations":[
            {"subject":oid,"predicate":"source_declares_xbrl_concept","object":cid,"source":anchor_source},
            {"subject":cid,"predicate":"documented_by_exact_taxonomy_release","object":metadata["release"],"source":ds},
        ],
        "templates":[],
        "ambiguities":[],
    }


def verify(
    *,
    root: Any,
    anchor_semantic_path: Any,
    xsd_path: Any,
    documentation_path: Any,
    metadata_path: Any,
) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    errors: list[str] = []
    try:
        ap = _safe_path(root, anchor_semantic_path)
        xp = _safe_path(root, xsd_path)
        dp = _safe_path(root, documentation_path)
        mp = _safe_path(root, metadata_path)
        result = json.loads(mp.read_text(encoding="utf-8"))
        if result.get("schema") != PRODUCER_SCHEMA:
            errors.append("PRODUCER_SCHEMA_INVALID")
        ordinal = int(result.get("fact_ordinal"))
        anchor_doc, anchor = _load_anchor(ap, ordinal)
        namespace_uri = str(anchor.get("namespace_uri") or "").strip()
        local_name = _local(anchor.get("local_name"))
        release = _release(namespace_uri)
        xsd_url, doc_url = _urls(release)
        xsd_raw = xp.read_bytes()
        doc_raw = dp.read_bytes()
        metadata = {"release":release, **_schema(xsd_raw, namespace_uri, local_name)}
        documentation = _doc(doc_raw, release, metadata["element_id"])
        xsd_rel = str(xp.relative_to(root)).replace("\\", "/")
        doc_rel = str(dp.relative_to(root)).replace("\\", "/")
        anchor_rel = str(ap.relative_to(root)).replace("\\", "/")
        xsd_sha = _sha(xsd_raw)
        doc_sha = _sha(doc_raw)

        expected = {
            "anchor_semantic_path": anchor_rel,
            "fact_ordinal": ordinal,
            "namespace_uri": namespace_uri,
            "local_name": local_name,
            "release": release,
            "xsd_url": xsd_url,
            "xsd_path": xsd_rel,
            "xsd_sha256": xsd_sha,
            "documentation_url": doc_url,
            "documentation_path": doc_rel,
            "documentation_sha256": doc_sha,
            "concept_metadata": metadata,
            "documentation_label": documentation,
        }
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append("METADATA_FIELD_MISMATCH:" + key)

        expected_contract = _contract(
            anchor_doc=anchor_doc,
            anchor=anchor,
            metadata=metadata,
            documentation=documentation,
            xsd_path=xsd_rel,
            xsd_sha=xsd_sha,
            xsd_url=xsd_url,
            doc_path=doc_rel,
            doc_sha=doc_sha,
            doc_url=doc_url,
        )
        if result.get("semantic_contract") != expected_contract:
            errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_REDERIVED")

        if result.get("release_relative_standard_concept_metadata_proved") is not True:
            errors.append("RELEASE_METADATA_PROOF_FLAG_MISSING")
        for key in (
            "custom_concept_semantics_claimed",
            "nearby_visible_label_semantics_claimed",
            "free_text_policy_semantics_claimed",
            "ontology_classification_claimed",
            "semantic_truth_authority",
            "policy_adequacy_authority",
            "terminal_authority",
        ):
            if result.get(key) is not False:
                errors.append("AUTHORITY_BOUNDARY_INVALID:" + key)
        if result.get("terminal_credit_delta") != 0:
            errors.append("TERMINAL_CREDIT_FORBIDDEN")

        return {
            "schema":SCHEMA,
            "verified":not errors,
            "status":"PASS__FASB_RELEASE_METADATA_REDERIVED_FROM_RAW_BYTES" if not errors else "FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "producer_independent":True,
            "taxonomy_bytes_rederived":True,
            "upstream_inline_anchor_verification_required":True,
            "release":release,
            "local_name":local_name,
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "verified":False,
            "status":"FAIL_CLOSED",
            "errors":[type(exc).__name__ + ":" + str(exc)],
            "producer_independent":True,
            "taxonomy_bytes_rederived":True,
            "upstream_inline_anchor_verification_required":True,
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    return verify(
        root=root,
        anchor_semantic_path=args.get("anchor_semantic_path"),
        xsd_path=args.get("xsd_path"),
        documentation_path=args.get("documentation_path"),
        metadata_path=args.get("metadata_path"),
    )
