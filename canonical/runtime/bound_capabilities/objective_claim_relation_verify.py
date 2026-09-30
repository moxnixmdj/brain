#!/usr/bin/env python3
"""Independent verifier for bounded open-research claim/relation results.

The verifier intentionally does not import the objective binder or the generic
relation evaluator. It revalidates evidence integrity and recomputes the
consequential exact-text or Decimal relation from the producer's explicit
references.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation

SCHEMA="PROJECT_BRAIN_OBJECTIVE_CLAIM_RELATION_INDEPENDENT_VERIFY_V1"
_NUMERIC=re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?"
)

def _canon(value):
    return " ".join(str(value or "").split())

def _sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def _units(extraction):
    if not isinstance(extraction,dict) or extraction.get("schema")!="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2":
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or extraction.get("output_verified") is not True:
        raise ValueError("VERIFIED_EXTRACTION_REQUIRED")
    page=str(extraction.get("page_raw_sha256") or "")
    visible=str(extraction.get("visible_text_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",page) or not re.fullmatch(r"[0-9a-f]{64}",visible):
        raise ValueError("PAGE_HASH_INVALID")
    out={}
    for row in extraction.get("evidence_units") or []:
        uid=str(row.get("evidence_unit_id") or "")
        text=_canon(row.get("text"))
        tsha=str(row.get("text_sha256") or "")
        start=row.get("visible_text_start"); end=row.get("visible_text_end")
        if not re.fullmatch(r"[0-9a-f]{64}",uid) or uid in out:
            raise ValueError("EVIDENCE_UNIT_ID_INVALID")
        if not text or _sha(text)!=tsha:
            raise ValueError("EVIDENCE_TEXT_HASH_MISMATCH")
        if row.get("page_raw_sha256")!=page or row.get("visible_text_sha256")!=visible:
            raise ValueError("EVIDENCE_PAGE_BINDING_MISMATCH")
        if not isinstance(start,int) or not isinstance(end,int) or end-start!=len(text) or start<0:
            raise ValueError("EVIDENCE_OFFSET_INVALID")
        if uid!=_sha(f"{page}:{start}:{end}:{tsha}"):
            raise ValueError("EVIDENCE_UNIT_BINDING_MISMATCH")
        out[uid]={"text":text,"source_url":str(row.get("source_url") or extraction.get("source_url") or "")}
    if not out:
        raise ValueError("EVIDENCE_UNITS_REQUIRED")
    return out

def _numbers(text):
    out=[]
    for m in _NUMERIC.finditer(text):
        try:
            value=Decimal(m.group(1).replace(",",""))
        except InvalidOperation as exc:
            raise ValueError("NUMERIC_PARSE_FAILED") from exc
        if not value.is_finite():
            raise ValueError("NUMERIC_NONFINITE")
        out.append({
          "value":value,
          "unit":_canon(m.group(2)).lower().rstrip(".,;:"),
          "raw":m.group(0).strip().rstrip(".,;:"),
        })
    return out

def _resolve(units,ref):
    if not isinstance(ref,dict):
        raise ValueError("NUMERIC_REFERENCE_INVALID")
    uid=str(ref.get("evidence_unit_id") or "")
    if uid not in units:
        raise ValueError("NUMERIC_UNIT_NOT_FOUND")
    index=ref.get("numeric_literal_index")
    nums=_numbers(units[uid]["text"])
    if not isinstance(index,int) or index<0 or index>=len(nums):
        raise ValueError("NUMERIC_INDEX_INVALID")
    return nums[index]

def _threshold(raw,expected_unit):
    m=re.fullmatch(
      r"\s*([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
      r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?\s*",
      str(raw),
    )
    if not m:
        raise ValueError("THRESHOLD_INVALID")
    value=Decimal(m.group(1).replace(",",""))
    unit=_canon(m.group(2)).lower().rstrip(".,;:")
    if value<0 or unit!=expected_unit:
        raise ValueError("THRESHOLD_UNIT_OR_SIGN_INVALID")
    return value

def verify(objective,extraction,binding):
    base={"schema":SCHEMA,"verified":False,"model_dependency_count":0}
    try:
        if not _canon(objective):
            return {**base,"reason":"OBJECTIVE_REQUIRED"}
        if not isinstance(binding,dict) or binding.get("status") not in {"CLAIM_SPEC_AND_OPERANDS_BOUND","CLAIM_SPEC_BOUND"}:
            return {**base,"reason":"BOUND_RESULT_REQUIRED"}
        units=_units(extraction)
        spec=binding.get("relation_spec") or {}
        result=binding.get("relation_result") or {}
        mode=str(spec.get("mode") or "").upper()
        if mode=="VERBATIM_SUPPORT":
            claim=_canon(spec.get("claim_text"))
            uid=str(spec.get("evidence_unit_id") or "")
            if not claim or uid not in units:
                return {**base,"reason":"VERBATIM_SPEC_INVALID"}
            found=claim.casefold() in units[uid]["text"].casefold()
            expected="EXACT_TEXT_SUPPORT_VERIFIED" if found else "EXACT_TEXT_SUPPORT_NOT_VERIFIED"
            if result.get("status")!=expected:
                return {**base,"reason":"VERBATIM_STATUS_MISMATCH"}
            return {
              **base,"verified":True,"reason":"VERIFIED",
              "mode":mode,"supported":found,"evidence_unit_id":uid,
            }
        if mode!="NUMERIC_RELATION":
            return {**base,"reason":"MODE_UNSUPPORTED"}
        left=_resolve(units,spec.get("left"))
        right=_resolve(units,spec.get("right"))
        if left["unit"]!=right["unit"]:
            return {**base,"reason":"UNIT_MISMATCH"}
        op=str(spec.get("operator") or "").upper()
        lv,rv=left["value"],right["value"]
        if op=="LT": predicate=lv<rv
        elif op=="LTE": predicate=lv<=rv
        elif op=="GT": predicate=lv>rv
        elif op=="GTE": predicate=lv>=rv
        elif op=="EQ": predicate=lv==rv
        elif op=="NE": predicate=lv!=rv
        elif op=="ABS_DIFF_LTE":
            threshold=_threshold(spec.get("threshold"),left["unit"])
            predicate=abs(lv-rv)<=threshold
        else:
            return {**base,"reason":"OPERATOR_UNSUPPORTED"}
        if result.get("status")!="NUMERIC_RELATION_VERIFIED":
            return {**base,"reason":"RELATION_STATUS_MISMATCH"}
        if bool(result.get("predicate"))!=bool(predicate):
            return {**base,"reason":"PREDICATE_MISMATCH"}
        observed_left=str((result.get("left") or {}).get("value") or "")
        observed_right=str((result.get("right") or {}).get("value") or "")
        if observed_left!=str(lv) or observed_right!=str(rv):
            return {**base,"reason":"OPERAND_VALUE_MISMATCH"}
        return {
          **base,"verified":True,"reason":"VERIFIED","mode":mode,
          "operator":op,"predicate":bool(predicate),
          "left_value":str(lv),"right_value":str(rv),"unit":left["unit"],
        }
    except Exception as exc:
        return {
          **base,"reason":"VERIFIER_EXCEPTION",
          "error_class":type(exc).__name__,"error":str(exc)[:500],
        }
