#!/usr/bin/env python3
"""Independent verifier for bounded open-research claim results.

Does not import the claim-spec binder or generic relation evaluator. It checks
V2 evidence-unit integrity and independently recomputes exact-text support or
Decimal numeric relations from the producer-emitted relation specification.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation

SCHEMA="PROJECT_BRAIN_OPEN_RESEARCH_CLAIM_VERIFICATION_V1"
_NUM=re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"(?:\s*([A-Za-z%°][A-Za-z0-9%°/_^.-]*))?"
)
OPS={"LT","LTE","GT","GTE","EQ","NE","ABS_DIFF_LTE"}
_NON_UNIT={"was","were","is","are","be","been","being","and","or","to","from","in","on","at","by"}

def _canon(value):
    return " ".join(str(value or "").split())

def _sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def _units(extraction):
    if not isinstance(extraction,dict):
        raise ValueError("EXTRACTION_REQUIRED")
    if extraction.get("schema")!="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2":
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or extraction.get("output_verified") is not True:
        raise ValueError("VERIFIED_EXTRACTION_REQUIRED")
    page=str(extraction.get("page_raw_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",page):
        raise ValueError("PAGE_HASH_INVALID")
    out={}
    for row in extraction.get("evidence_units") or []:
        if not isinstance(row,dict):
            raise ValueError("EVIDENCE_UNIT_INVALID")
        uid=str(row.get("evidence_unit_id") or "")
        text=_canon(row.get("text"))
        text_sha=str(row.get("text_sha256") or "")
        if _sha(text)!=text_sha:
            raise ValueError("TEXT_HASH_MISMATCH")
        try:
            start=int(row.get("visible_text_start"))
            end=int(row.get("visible_text_end"))
        except Exception as exc:
            raise ValueError("OFFSET_INVALID") from exc
        if start<0 or end<=start or end-start!=len(text):
            raise ValueError("OFFSET_INVALID")
        expected=_sha(f"{page}:{start}:{end}:{text_sha}")
        if uid!=expected:
            raise ValueError("EVIDENCE_UNIT_ID_MISMATCH")
        if uid in out:
            raise ValueError("EVIDENCE_UNIT_DUPLICATE")
        out[uid]={"text":text,"source_url":str(row.get("source_url") or "")}
    if not out:
        raise ValueError("EVIDENCE_UNITS_REQUIRED")
    return out

def _numbers(text):
    rows=[]
    for m in _NUM.finditer(text):
        surface=m.group(0).strip().rstrip(".,;:")
        unit=_canon(m.group(2)).lower().rstrip(".,;:") if m.group(2) else ""
        if unit in _NON_UNIT:
            unit=""
        try:
            value=Decimal(m.group(1))
        except InvalidOperation as exc:
            raise ValueError("NUMERIC_LITERAL_INVALID") from exc
        if not value.is_finite():
            raise ValueError("NUMERIC_LITERAL_NONFINITE")
        rows.append({"value":value,"unit":unit,"surface":surface})
    return rows

def _resolve(units,ref):
    if not isinstance(ref,dict):
        raise ValueError("NUMERIC_REFERENCE_INVALID")
    uid=str(ref.get("evidence_unit_id") or "")
    if uid not in units:
        raise ValueError("EVIDENCE_UNIT_REFERENCE_NOT_FOUND")
    try:
        idx=int(ref.get("numeric_literal_index"))
    except Exception as exc:
        raise ValueError("NUMERIC_INDEX_INVALID") from exc
    rows=_numbers(units[uid]["text"])
    if idx<0 or idx>=len(rows):
        raise ValueError("NUMERIC_INDEX_OUT_OF_RANGE")
    return rows[idx]

def _literal_threshold(raw,unit):
    text=_canon(raw).rstrip(".,;:")
    m=_NUM.fullmatch(text)
    if not m:
        raise ValueError("THRESHOLD_LITERAL_INVALID")
    value=Decimal(m.group(1))
    tunit=_canon(m.group(2)).lower().rstrip(".,;:") if m.group(2) else ""
    if not value.is_finite() or value<0:
        raise ValueError("THRESHOLD_INVALID")
    if tunit!=unit:
        raise ValueError("THRESHOLD_UNIT_MISMATCH")
    return value

def verify(extraction,binding):
    base={
      "schema":SCHEMA,
      "verified":False,
      "producer_independent":True,
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    try:
        units=_units(extraction)
        if not isinstance(binding,dict) or binding.get("output_verified") is not True:
            return {**base,"reason":"BINDING_NOT_VERIFIED"}
        if binding.get("model_dependency_count")!=0:
            return {**base,"reason":"MODEL_DEPENDENCY_NONZERO"}
        spec=binding.get("relation_spec")
        observed=binding.get("relation_result")
        if not isinstance(spec,dict) or not isinstance(observed,dict):
            return {**base,"reason":"RELATION_SPEC_OR_RESULT_MISSING"}
        mode=str(spec.get("mode") or "").upper()

        if mode=="VERBATIM_SUPPORT":
            claim=_canon(spec.get("claim_text"))
            uid=str(spec.get("evidence_unit_id") or "")
            if not claim or uid not in units:
                return {**base,"reason":"VERBATIM_SPEC_INVALID"}
            needle=claim.casefold()
            matches=[u for u,row in units.items() if needle in row["text"].casefold()]
            expected=(len(matches)==1 and matches[0]==uid)
            expected_status="EXACT_TEXT_SUPPORT_VERIFIED" if expected else "EXACT_TEXT_SUPPORT_NOT_VERIFIED"
            if observed.get("status")!=expected_status:
                return {**base,"reason":"VERBATIM_STATUS_MISMATCH"}
            return {
              **base,"verified":True,"reason":"VERIFIED",
              "mode":mode,"predicate":expected,
              "source_urls":sorted({x["source_url"] for x in units.values() if x["source_url"]}),
            }

        if mode!="NUMERIC_RELATION":
            return {**base,"reason":"RELATION_MODE_UNSUPPORTED"}
        op=str(spec.get("operator") or "").upper()
        if op not in OPS:
            return {**base,"reason":"RELATION_OPERATOR_INVALID"}
        left=_resolve(units,spec.get("left"))
        right=_resolve(units,spec.get("right"))
        if left["unit"]!=right["unit"]:
            return {**base,"reason":"UNIT_MISMATCH"}
        lv,rv=left["value"],right["value"]
        threshold=None
        if op=="LT": expected=lv<rv
        elif op=="LTE": expected=lv<=rv
        elif op=="GT": expected=lv>rv
        elif op=="GTE": expected=lv>=rv
        elif op=="EQ": expected=lv==rv
        elif op=="NE": expected=lv!=rv
        else:
            threshold=_literal_threshold(spec.get("threshold"),left["unit"])
            expected=abs(lv-rv)<=threshold
        if observed.get("status")!="NUMERIC_RELATION_VERIFIED":
            return {**base,"reason":"RELATION_STATUS_MISMATCH"}
        if bool(observed.get("predicate"))!=bool(expected):
            return {**base,"reason":"PREDICATE_MISMATCH"}
        return {
          **base,"verified":True,"reason":"VERIFIED",
          "mode":mode,"operator":op,"predicate":bool(expected),
          "left_value":str(lv),"right_value":str(rv),
          "unit":left["unit"] or None,
          "threshold":str(threshold) if threshold is not None else None,
          "source_urls":sorted({x["source_url"] for x in units.values() if x["source_url"]}),
        }
    except Exception as exc:
        return {**base,"reason":"VERIFIER_EXCEPTION:"+type(exc).__name__+":"+str(exc)}

