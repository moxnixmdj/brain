#!/usr/bin/env python3
"""Independent raw-byte verifier for SEC extracted XBRL instance facts V1.

Does not import the producer. Re-derives the complete emitted source-native
contract from preserved SEC instance bytes using xml.dom.minidom.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import pathlib
import re
from typing import Any, Mapping
from xml.dom import minidom, Node

SCHEMA = "PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_VERIFY_V1"
PRODUCER_SCHEMA = "PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"
_XBRLI = "http://www.xbrl.org/2003/instance"
_XBRLDI = "http://xbrl.org/2006/xbrldi"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"
_XMLNS = "http://www.w3.org/2000/xmlns/"
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

class VerifyError(RuntimeError):
    pass

def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise VerifyError("PATH_OUTSIDE_REPOSITORY")
    return path

def _text(node) -> str:
    return "".join(
        c.data for c in node.childNodes
        if c.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)
    ).strip()

def _namespace_map(doc) -> dict[str, str]:
    out = {}
    for elem in doc.getElementsByTagName("*"):
        if not elem.attributes:
            continue
        for i in range(elem.attributes.length):
            a = elem.attributes.item(i)
            if a.namespaceURI == _XMLNS or a.name == "xmlns" or a.name.startswith("xmlns:"):
                prefix = "" if a.name == "xmlns" else a.name.split(":", 1)[1]
                if prefix in out and out[prefix] != a.value:
                    raise VerifyError("NAMESPACE_PREFIX_REBOUND:" + prefix)
                out[prefix] = a.value
    return out

def _expand(value: Any, nsmap: Mapping[str, str]) -> str:
    text = str(value or "").strip()
    if ":" in text:
        p, l = text.split(":", 1)
        if not _NAME_RE.fullmatch(p) or not _NAME_RE.fullmatch(l):
            raise VerifyError("QNAME_INVALID:" + text)
        uri = nsmap.get(p)
        if not uri:
            raise VerifyError("QNAME_PREFIX_UNBOUND:" + p)
        return "{" + uri + "}" + l
    if not _NAME_RE.fullmatch(text):
        raise VerifyError("QNAME_INVALID:" + text)
    uri = nsmap.get("")
    return ("{" + uri + "}" + text) if uri else text

def _children(node, ns, local):
    return [
        c for c in node.childNodes
        if c.nodeType == Node.ELEMENT_NODE and c.namespaceURI == ns and c.localName == local
    ]

def _period(context):
    ps = _children(context, _XBRLI, "period")
    if len(ps) != 1:
        raise VerifyError("CONTEXT_PERIOD_REQUIRED")
    p = ps[0]
    ins = p.getElementsByTagNameNS(_XBRLI, "instant")
    if len(ins) == 1:
        return {"kind": "instant", "instant": _text(ins[0])}
    starts = p.getElementsByTagNameNS(_XBRLI, "startDate")
    ends = p.getElementsByTagNameNS(_XBRLI, "endDate")
    if len(starts) == 1 and len(ends) == 1:
        return {"kind": "duration", "start": _text(starts[0]), "end": _text(ends[0])}
    if len(p.getElementsByTagNameNS(_XBRLI, "forever")) == 1:
        return {"kind": "forever"}
    raise VerifyError("CONTEXT_PERIOD_FORM_UNSUPPORTED")

def _dimensions(context, nsmap):
    out = []
    for e in context.getElementsByTagName("*"):
        if e.namespaceURI == _XBRLDI and e.localName == "explicitMember":
            out.append({
                "kind": "explicit",
                "dimension": _expand(e.getAttribute("dimension"), nsmap),
                "member": _expand(_text(e), nsmap),
            })
        elif e.namespaceURI == _XBRLDI and e.localName == "typedMember":
            kids = [c for c in e.childNodes if c.nodeType == Node.ELEMENT_NODE]
            if len(kids) != 1:
                raise VerifyError("TYPED_DIMENSION_SINGLE_CHILD_REQUIRED")
            c = kids[0]
            out.append({
                "kind": "typed",
                "dimension": _expand(e.getAttribute("dimension"), nsmap),
                "typed_value_qname": ("{" + str(c.namespaceURI) + "}" + str(c.localName)) if c.namespaceURI else str(c.localName or c.tagName),
                "typed_text": _text(c),
            })
    return sorted(out, key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))

def _contexts(doc, nsmap):
    out = {}
    for c in doc.getElementsByTagNameNS(_XBRLI, "context"):
        cid = c.getAttribute("id").strip()
        if not cid or cid in out:
            raise VerifyError("CONTEXT_ID_INVALID_OR_DUPLICATE")
        ids = c.getElementsByTagNameNS(_XBRLI, "identifier")
        if len(ids) != 1:
            raise VerifyError("CONTEXT_ENTITY_IDENTIFIER_REQUIRED")
        ident = ids[0]
        out[cid] = {
            "entity": {"scheme": ident.getAttribute("scheme").strip(), "identifier": _text(ident)},
            "period": _period(c),
            "dimensions": _dimensions(c, nsmap),
        }
    return out

def _units(doc, nsmap):
    out = {}
    for u in doc.getElementsByTagNameNS(_XBRLI, "unit"):
        uid = u.getAttribute("id").strip()
        if not uid or uid in out:
            raise VerifyError("UNIT_ID_INVALID_OR_DUPLICATE")
        direct = _children(u, _XBRLI, "measure")
        divide = _children(u, _XBRLI, "divide")
        if direct and not divide:
            out[uid] = {"kind": "measure", "measures": sorted(_expand(_text(x), nsmap) for x in direct)}
        elif len(divide) == 1 and not direct:
            nums = divide[0].getElementsByTagNameNS(_XBRLI, "unitNumerator")
            dens = divide[0].getElementsByTagNameNS(_XBRLI, "unitDenominator")
            if len(nums) != 1 or len(dens) != 1:
                raise VerifyError("DIVIDE_UNIT_MEASURES_REQUIRED")
            nm = nums[0].getElementsByTagNameNS(_XBRLI, "measure")
            dm = dens[0].getElementsByTagNameNS(_XBRLI, "measure")
            if not nm or not dm:
                raise VerifyError("DIVIDE_UNIT_MEASURES_REQUIRED")
            out[uid] = {
                "kind": "divide",
                "numerator": sorted(_expand(_text(x), nsmap) for x in nm),
                "denominator": sorted(_expand(_text(x), nsmap) for x in dm),
            }
        else:
            raise VerifyError("UNIT_FORM_UNSUPPORTED")
    return out

def _decimal(text: str):
    try:
        d = Decimal(text.strip())
    except InvalidOperation:
        return None
    if not d.is_finite():
        return None
    return format(d, "f")

def _facts(doc, contexts, units):
    out = []
    root = doc.documentElement
    for c in root.childNodes:
        if c.nodeType != Node.ELEMENT_NODE or not c.hasAttribute("contextRef"):
            continue
        cref = c.getAttribute("contextRef").strip()
        if cref not in contexts:
            raise VerifyError("FACT_CONTEXT_REF_UNKNOWN:" + cref)
        if c.namespaceURI == _XBRLI:
            continue
        uref = c.getAttribute("unitRef").strip() or None
        if uref is not None and uref not in units:
            raise VerifyError("FACT_UNIT_REF_UNKNOWN:" + uref)
        nil = c.getAttributeNS(_XSI, "nil").casefold() in {"true", "1"}
        lexical = "" if nil else _text(c)
        uri, local = str(c.namespaceURI or ""), str(c.localName or c.tagName)
        out.append({
            "ordinal": len(out),
            "concept_qname": ("{" + uri + "}" + local) if uri else local,
            "namespace_uri": uri,
            "local_name": local,
            "context_ref": cref,
            "context": contexts[cref],
            "unit_ref": uref,
            "unit": units.get(uref) if uref else None,
            "decimals": c.getAttribute("decimals") if c.hasAttribute("decimals") else None,
            "precision": c.getAttribute("precision") if c.hasAttribute("precision") else None,
            "nil": nil,
            "lexical_value": lexical,
            "normalized_decimal": None if nil else _decimal(lexical),
        })
    return out

def _contract(facts, source_path, source_sha256, source_url):
    return {
        "schema": "PROJECT_BRAIN_SOURCE_NATIVE_XBRL_INSTANCE_FACT_CONTRACT_V1",
        "source": {"path": source_path, "sha256": source_sha256, "uri": source_url},
        "facts": [{
            "id": "XBRL_INSTANCE_FACT:" + str(r["ordinal"]),
            "type": "SOURCE_NATIVE_XBRL_INSTANCE_FACT",
            "concept_qname": r["concept_qname"],
            "context": r["context"],
            "unit": r["unit"],
            "lexical_value": r["lexical_value"],
            "normalized_decimal": r["normalized_decimal"],
            "nil": r["nil"],
            "source": {"path": source_path, "observation_id": str(r["ordinal"])},
        } for r in facts],
    }

def verify(*, root: Any, raw_path: Any, semantic_path: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    errors = []
    try:
        raw_file = _safe_path(root, raw_path)
        semantic_file = _safe_path(root, semantic_path)
        raw = raw_file.read_bytes()
        if b"<!doctype" in raw[:200000].lower() or b"<!entity" in raw[:200000].lower():
            raise VerifyError("DTD_OR_ENTITY_FORBIDDEN")
        doc = minidom.parseString(raw)
        if doc.documentElement.namespaceURI != _XBRLI or doc.documentElement.localName != "xbrl":
            raise VerifyError("XBRL_INSTANCE_ROOT_REQUIRED")
        nsmap = _namespace_map(doc)
        contexts, units = _contexts(doc, nsmap), _units(doc, nsmap)
        facts = _facts(doc, contexts, units)
        sem = json.loads(semantic_file.read_text(encoding="utf-8"))
        if sem.get("schema") != PRODUCER_SCHEMA:
            errors.append("PRODUCER_SCHEMA_INVALID")
        sha = hashlib.sha256(raw).hexdigest()
        rel = str(raw_file.relative_to(root)).replace("\\", "/")
        for k, value in {
            "source_path": rel,
            "source_sha256": sha,
            "context_count": len(contexts),
            "unit_count": len(units),
            "fact_count": len(facts),
            "contexts": contexts,
            "units": units,
            "facts": facts,
        }.items():
            if sem.get(k) != value:
                errors.append("SEMANTIC_FIELD_MISMATCH:" + k)
        expected_contract = _contract(facts, rel, sha, str(sem.get("source_url") or ""))
        if sem.get("semantic_contract") != expected_contract:
            errors.append("SEMANTIC_CONTRACT_NOT_EXACTLY_REDERIVED_FROM_RAW_BYTES")
        if sem.get("source_native_instance_fact_semantics_proved") is not True:
            errors.append("SOURCE_NATIVE_INSTANCE_FACT_PROOF_FLAG_MISSING")
        if sem.get("inline_transform_semantics_reimplemented") is not False:
            errors.append("INLINE_TRANSFORM_REIMPLEMENTATION_FLAG_INVALID")
        for key in (
            "custom_concept_domain_semantics_claimed",
            "nearby_visible_label_semantics_claimed",
            "raw_prose_wsd_claimed",
            "ontology_classification_claimed",
            "policy_adequacy_authority",
            "semantic_truth_authority",
            "terminal_authority",
        ):
            if sem.get(key) is not False:
                errors.append("AUTHORITY_BOUNDARY_INVALID:" + key)
        if sem.get("terminal_credit_delta") != 0:
            errors.append("TERMINAL_CREDIT_FORBIDDEN")
        return {
            "schema": SCHEMA,
            "verified": not errors,
            "status": "PASS__SEC_EXTRACTED_INSTANCE_FACTS_REDERIVED_FROM_RAW_BYTES" if not errors else "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "producer_independent": True,
            "full_contract_rederived_from_raw_bytes": True,
            "source_sha256": sha,
            "context_count": len(contexts),
            "unit_count": len(units),
            "fact_count": len(facts),
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
    return verify(root=root, raw_path=args.get("raw_path"), semantic_path=args.get("semantic_path"))
