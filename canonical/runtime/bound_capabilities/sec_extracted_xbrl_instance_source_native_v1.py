#!/usr/bin/env python3
"""Bounded SEC extracted-XBRL-instance source-native fact semantics.

V1 consumes an SEC-published extracted XBRL instance document (`*_htm.xml`)
and emits normalized filing-local source facts: exact expanded concept QName,
context/entity/period/dimensions, unit structure, and lexical/finite-decimal value.

No nearby prose semantics, custom-concept domain meaning, ontology
classification, policy adequacy, acceptance, or terminal truth is inferred.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"
_XBRLI = "http://www.xbrl.org/2003/instance"
_XBRLDI = "http://xbrl.org/2006/xbrldi"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"
MAX_BYTES = 20_000_000
MAX_FACTS = 50_000
MAX_CONTEXTS = 20_000
MAX_UNITS = 10_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

class ExtractedInstanceError(RuntimeError):
    pass

def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise ExtractedInstanceError("PATH_OUTSIDE_REPOSITORY")
    return path

def _user_agent(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 240:
        raise ExtractedInstanceError("SEC_USER_AGENT_REQUIRED")
    text = " ".join(value.strip().split())
    if len(text.split()) < 2 or not any(
        _EMAIL_RE.fullmatch(x.strip("<>()[]{};,") or "") for x in text.split()
    ):
        raise ExtractedInstanceError("SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED")
    return text

def _instance_url(value: Any) -> str:
    text = str(value or "").strip()
    p = urllib.parse.urlsplit(text)
    if (
        p.scheme != "https"
        or p.hostname != "www.sec.gov"
        or p.username is not None or p.password is not None
        or p.port not in (None, 443)
        or p.query or p.fragment
        or not p.path.startswith("/Archives/edgar/data/")
        or not p.path.lower().endswith("_htm.xml")
    ):
        raise ExtractedInstanceError("SEC_ARCHIVE_EXTRACTED_INSTANCE_URL_REQUIRED")
    return urllib.parse.urlunsplit(("https", "www.sec.gov", p.path, "", ""))

def _fetch(url: str, user_agent: str, timeout: int, max_bytes: int):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
        return (
            raw,
            response.geturl(),
            str(response.headers.get("Content-Type", "")),
            int(getattr(response, "status", 200)),
        )

def _reject_unsafe_xml(raw: bytes) -> None:
    head = raw[:200000].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise ExtractedInstanceError("DTD_OR_ENTITY_FORBIDDEN")

def _namespace_map(raw: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for _, pair in ET.iterparse(BytesIO(raw), events=("start-ns",)):
            prefix, uri = pair
            prefix = prefix or ""
            if prefix in out and out[prefix] != uri:
                raise ExtractedInstanceError("NAMESPACE_PREFIX_REBOUND:" + prefix)
            out[prefix] = uri
    except ExtractedInstanceError:
        raise
    except Exception as exc:
        raise ExtractedInstanceError("XML_NAMESPACE_PARSE_FAILED") from exc
    return out

def _expand(value: Any, nsmap: Mapping[str, str]) -> str:
    text = str(value or "").strip()
    if ":" in text:
        prefix, local = text.split(":", 1)
        if not _NAME_RE.fullmatch(prefix) or not _NAME_RE.fullmatch(local):
            raise ExtractedInstanceError("QNAME_INVALID:" + text)
        uri = nsmap.get(prefix)
        if not uri:
            raise ExtractedInstanceError("QNAME_PREFIX_UNBOUND:" + prefix)
        return "{" + uri + "}" + local
    if not _NAME_RE.fullmatch(text):
        raise ExtractedInstanceError("QNAME_INVALID:" + text)
    uri = nsmap.get("")
    return ("{" + uri + "}" + text) if uri else text

def _split_tag(tag: Any) -> tuple[str, str]:
    text = str(tag)
    if text.startswith("{") and "}" in text:
        return tuple(text[1:].split("}", 1))
    return "", text

def _txt(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()

def _period(context: ET.Element) -> dict[str, Any]:
    p = context.find("{" + _XBRLI + "}period")
    if p is None:
        raise ExtractedInstanceError("CONTEXT_PERIOD_REQUIRED")
    instant = p.find("{" + _XBRLI + "}instant")
    if instant is not None:
        return {"kind": "instant", "instant": _txt(instant)}
    start, end = p.find("{" + _XBRLI + "}startDate"), p.find("{" + _XBRLI + "}endDate")
    if start is not None and end is not None:
        return {"kind": "duration", "start": _txt(start), "end": _txt(end)}
    if p.find("{" + _XBRLI + "}forever") is not None:
        return {"kind": "forever"}
    raise ExtractedInstanceError("CONTEXT_PERIOD_FORM_UNSUPPORTED")

def _dimensions(context: ET.Element, nsmap: Mapping[str, str]) -> list[dict[str, Any]]:
    out = []
    for elem in context.iter():
        if elem.tag == "{" + _XBRLDI + "}explicitMember":
            out.append({
                "kind": "explicit",
                "dimension": _expand(elem.attrib.get("dimension"), nsmap),
                "member": _expand(_txt(elem), nsmap),
            })
        elif elem.tag == "{" + _XBRLDI + "}typedMember":
            children = list(elem)
            if len(children) != 1:
                raise ExtractedInstanceError("TYPED_DIMENSION_SINGLE_CHILD_REQUIRED")
            uri, local = _split_tag(children[0].tag)
            out.append({
                "kind": "typed",
                "dimension": _expand(elem.attrib.get("dimension"), nsmap),
                "typed_value_qname": ("{" + uri + "}" + local) if uri else local,
                "typed_text": _txt(children[0]),
            })
    return sorted(out, key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))

def _contexts(root: ET.Element, nsmap: Mapping[str, str], limit: int) -> dict[str, Any]:
    out = {}
    for c in root.findall("{" + _XBRLI + "}context"):
        cid = str(c.attrib.get("id") or "").strip()
        if not cid or cid in out:
            raise ExtractedInstanceError("CONTEXT_ID_INVALID_OR_DUPLICATE")
        ident = c.find("./{" + _XBRLI + "}entity/{" + _XBRLI + "}identifier")
        if ident is None:
            raise ExtractedInstanceError("CONTEXT_ENTITY_IDENTIFIER_REQUIRED")
        out[cid] = {
            "entity": {
                "scheme": str(ident.attrib.get("scheme") or "").strip(),
                "identifier": _txt(ident),
            },
            "period": _period(c),
            "dimensions": _dimensions(c, nsmap),
        }
        if len(out) > limit:
            raise ExtractedInstanceError("CONTEXT_LIMIT_EXCEEDED")
    return out

def _units(root: ET.Element, nsmap: Mapping[str, str], limit: int) -> dict[str, Any]:
    out = {}
    for u in root.findall("{" + _XBRLI + "}unit"):
        uid = str(u.attrib.get("id") or "").strip()
        if not uid or uid in out:
            raise ExtractedInstanceError("UNIT_ID_INVALID_OR_DUPLICATE")
        measures = u.findall("{" + _XBRLI + "}measure")
        divide = u.find("{" + _XBRLI + "}divide")
        if measures and divide is None:
            out[uid] = {"kind": "measure", "measures": sorted(_expand(_txt(m), nsmap) for m in measures)}
        elif divide is not None and not measures:
            nums = divide.findall("./{" + _XBRLI + "}unitNumerator/{" + _XBRLI + "}measure")
            dens = divide.findall("./{" + _XBRLI + "}unitDenominator/{" + _XBRLI + "}measure")
            if not nums or not dens:
                raise ExtractedInstanceError("DIVIDE_UNIT_MEASURES_REQUIRED")
            out[uid] = {
                "kind": "divide",
                "numerator": sorted(_expand(_txt(m), nsmap) for m in nums),
                "denominator": sorted(_expand(_txt(m), nsmap) for m in dens),
            }
        else:
            raise ExtractedInstanceError("UNIT_FORM_UNSUPPORTED")
        if len(out) > limit:
            raise ExtractedInstanceError("UNIT_LIMIT_EXCEEDED")
    return out

def _decimal(text: str) -> str | None:
    try:
        d = Decimal(text.strip())
    except InvalidOperation:
        return None
    if not d.is_finite():
        return None
    return format(d, "f")

def _facts(root: ET.Element, contexts: Mapping[str, Any], units: Mapping[str, Any], limit: int):
    out = []
    for child in list(root):
        context_ref = str(child.attrib.get("contextRef") or "").strip()
        if not context_ref:
            continue
        if context_ref not in contexts:
            raise ExtractedInstanceError("FACT_CONTEXT_REF_UNKNOWN:" + context_ref)
        uri, local = _split_tag(child.tag)
        if uri == _XBRLI:
            continue
        unit_ref = str(child.attrib.get("unitRef") or "").strip() or None
        if unit_ref is not None and unit_ref not in units:
            raise ExtractedInstanceError("FACT_UNIT_REF_UNKNOWN:" + unit_ref)
        nil = str(child.attrib.get("{" + _XSI + "}nil") or "").casefold() in {"true", "1"}
        lexical = "" if nil else _txt(child)
        out.append({
            "ordinal": len(out),
            "concept_qname": ("{" + uri + "}" + local) if uri else local,
            "namespace_uri": uri,
            "local_name": local,
            "context_ref": context_ref,
            "context": contexts[context_ref],
            "unit_ref": unit_ref,
            "unit": units.get(unit_ref) if unit_ref else None,
            "decimals": child.attrib.get("decimals"),
            "precision": child.attrib.get("precision"),
            "nil": nil,
            "lexical_value": lexical,
            "normalized_decimal": None if nil else _decimal(lexical),
        })
        if len(out) > limit:
            raise ExtractedInstanceError("FACT_LIMIT_EXCEEDED")
    return out

def _contract(facts, source_path: str, source_sha256: str, source_url: str):
    return {
        "schema": "PROJECT_BRAIN_SOURCE_NATIVE_XBRL_INSTANCE_FACT_CONTRACT_V1",
        "source": {"path": source_path, "sha256": source_sha256, "uri": source_url},
        "facts": [{
            "id": "XBRL_INSTANCE_FACT:" + str(row["ordinal"]),
            "type": "SOURCE_NATIVE_XBRL_INSTANCE_FACT",
            "concept_qname": row["concept_qname"],
            "context": row["context"],
            "unit": row["unit"],
            "lexical_value": row["lexical_value"],
            "normalized_decimal": row["normalized_decimal"],
            "nil": row["nil"],
            "source": {"path": source_path, "observation_id": str(row["ordinal"])},
        } for row in facts],
    }

def _extract(raw: bytes, max_facts: int, max_contexts: int, max_units: int):
    _reject_unsafe_xml(raw)
    nsmap = _namespace_map(raw)
    try:
        root = ET.fromstring(raw)
    except Exception as exc:
        raise ExtractedInstanceError("XML_PARSE_FAILED") from exc
    if root.tag != "{" + _XBRLI + "}xbrl":
        raise ExtractedInstanceError("XBRL_INSTANCE_ROOT_REQUIRED")
    contexts = _contexts(root, nsmap, max_contexts)
    units = _units(root, nsmap, max_units)
    facts = _facts(root, contexts, units, max_facts)
    return contexts, units, facts

def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    config_path = _safe_path(root, args.get("config_path"))
    raw_path = _safe_path(root, args.get("raw_output_path"))
    semantic_path = _safe_path(root, args.get("semantic_output_path"))
    if not config_path.is_file() or config_path.suffix.lower() != ".json":
        raise ExtractedInstanceError("CONFIG_JSON_REQUIRED")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    url = _instance_url(config.get("instance_url"))
    user_agent = _user_agent(config.get("sec_user_agent"))
    timeout = max(2, min(int(args.get("timeout_s", 30)), 60))
    max_bytes = max(4096, min(int(args.get("max_bytes", MAX_BYTES)), MAX_BYTES))
    raw, final_url, content_type, status = _fetch(url, user_agent, timeout, max_bytes)
    if status != 200:
        raise ExtractedInstanceError("HTTP_STATUS:" + str(status))
    if final_url != url:
        raise ExtractedInstanceError("SEC_FINAL_URL_MISMATCH")
    if len(raw) > max_bytes:
        raise ExtractedInstanceError("HTTP_BODY_TOO_LARGE")
    if "xml" not in content_type.casefold() and "text/plain" not in content_type.casefold():
        raise ExtractedInstanceError("SEC_CONTENT_TYPE_NOT_XML")
    contexts, units, facts = _extract(
        raw,
        max(1, min(int(args.get("max_facts", MAX_FACTS)), MAX_FACTS)),
        max(1, min(int(args.get("max_contexts", MAX_CONTEXTS)), MAX_CONTEXTS)),
        max(1, min(int(args.get("max_units", MAX_UNITS)), MAX_UNITS)),
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_path = str(raw_path.relative_to(root)).replace("\\", "/")
    result = {
        "schema": SCHEMA,
        "status": "PASS__SEC_EXTRACTED_XBRL_INSTANCE_FACTS_NORMALIZED",
        "source_url": url,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "http_status": status,
        "content_type": content_type,
        "context_count": len(contexts),
        "unit_count": len(units),
        "fact_count": len(facts),
        "contexts": contexts,
        "units": units,
        "facts": facts,
        "semantic_contract": _contract(facts, source_path, source_sha256, url),
        "source_native_instance_fact_semantics_proved": True,
        "inline_transform_semantics_reimplemented": False,
        "custom_concept_domain_semantics_claimed": False,
        "nearby_visible_label_semantics_claimed": False,
        "raw_prose_wsd_claimed": False,
        "ontology_classification_claimed": False,
        "policy_adequacy_authority": False,
        "semantic_truth_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    semantic_path.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
