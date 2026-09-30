#!/usr/bin/env python3
"""Fail-closed typed support/relation evaluation over generic evidence units.

Verified scope only:
1. exact normalized substring occurrence inside one or more integrity-checked
   evidence units;
2. explicit Decimal numeric relations over caller-referenced numeric literals
   inside integrity-checked evidence units, with exact normalized unit matching.

This module does NOT infer paraphrases, semantic entailment, factual truth,
causality, evidence sufficiency/quality/independence, or the semantic role of a
numeric literal.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from decimal import Decimal, InvalidOperation

SCHEMA="PROJECT_BRAIN_GENERIC_EVIDENCE_CLAIM_RELATION_V1"
EXTRACTION_SCHEMA="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2"
OPS={"LT","LTE","GT","GTE","EQ","NE","ABS_DIFF_LTE"}

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

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _validated_units(extraction):
    if not isinstance(extraction,dict) or extraction.get("schema")!=EXTRACTION_SCHEMA:
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or extraction.get("output_verified") is not True:
        raise ValueError("VERIFIED_GENERIC_EXTRACTION_REQUIRED")

    multi_source=extraction.get("multi_source") is True
    page_sha=str(extraction.get("page_raw_sha256") or "")
    visible_sha=str(extraction.get("visible_text_sha256") or "")
    if not multi_source:
        if not re.fullmatch(r"[0-9a-f]{64}",page_sha) or not re.fullmatch(r"[0-9a-f]{64}",visible_sha):
            raise ValueError("EXTRACTION_PAGE_HASH_INVALID")

    rows=extraction.get("evidence_units")
    if not isinstance(rows,list) or not rows:
        raise ValueError("EVIDENCE_UNITS_REQUIRED")

    declared_sources=extraction.get("source_urls") if multi_source else None
    if multi_source:
        if not isinstance(declared_sources,list) or len(set(str(x) for x in declared_sources if x))<2:
            raise ValueError("MULTI_SOURCE_DECLARATION_INVALID")

    out={}
    observed_sources=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("EVIDENCE_UNIT_INVALID")
        uid=str(row.get("evidence_unit_id") or "")
        text=_canon(row.get("text"))
        text_sha=str(row.get("text_sha256") or "")
        row_page=str(row.get("page_raw_sha256") or "")
        row_visible=str(row.get("visible_text_sha256") or "")
        start=row.get("visible_text_start")
        end=row.get("visible_text_end")
        source_url=str(row.get("source_url") or extraction.get("source_url") or "")
        if not re.fullmatch(r"[0-9a-f]{64}",uid):
            raise ValueError("EVIDENCE_UNIT_ID_INVALID")
        if uid in out:
            raise ValueError("EVIDENCE_UNIT_ID_DUPLICATE")
        if not text or _sha(text)!=text_sha:
            raise ValueError("EVIDENCE_UNIT_TEXT_HASH_MISMATCH")
        if not re.fullmatch(r"[0-9a-f]{64}",row_page) or not re.fullmatch(r"[0-9a-f]{64}",row_visible):
            raise ValueError("EVIDENCE_UNIT_PAGE_HASH_INVALID")
        if not multi_source and (row_page!=page_sha or row_visible!=visible_sha):
            raise ValueError("EVIDENCE_UNIT_PAGE_BINDING_MISMATCH")
        if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start or end-start!=len(text):
            raise ValueError("EVIDENCE_UNIT_OFFSET_INVALID")
        expected_uid=_sha(f"{row_page}:{start}:{end}:{text_sha}")
        if uid!=expected_uid:
            raise ValueError("EVIDENCE_UNIT_ID_BINDING_MISMATCH")
        if multi_source:
            if not source_url or source_url not in set(str(x) for x in declared_sources):
                raise ValueError("MULTI_SOURCE_UNIT_SOURCE_UNDECLARED")
            observed_sources.add(source_url)
        out[uid]={
            "evidence_unit_id":uid,
            "text":text,
            "text_sha256":text_sha,
            "source_url":source_url,
            "page_raw_sha256":row_page,
            "visible_text_sha256":row_visible,
            "visible_text_start":start,
            "visible_text_end":end,
        }

    if multi_source and len(observed_sources)<2:
        raise ValueError("MULTI_SOURCE_EVIDENCE_REQUIRES_DISTINCT_SOURCES")
    return out

def _numbers(unit):
    out=[]
    for index,m in enumerate(_NUMERIC.finditer(unit["text"])):
        raw=m.group(0).strip()
        number=m.group(1).replace(",","")
        unit_text=_canon(m.group(2)).lower().rstrip(".,;:")
        try:
            value=Decimal(number)
        except InvalidOperation as exc:
            raise ValueError("NUMERIC_LITERAL_PARSE_FAILED") from exc
        if not value.is_finite():
            raise ValueError("NUMERIC_LITERAL_NONFINITE")
        out.append({
            "numeric_literal_index":index,
            "raw":raw,
            "value":value,
            "unit":unit_text,
            "char_start":m.start(),
            "char_end":m.end(),
        })
    return out

def _resolve_numeric(units,ref):
    if not isinstance(ref,dict):
        raise ValueError("NUMERIC_REFERENCE_INVALID")
    uid=str(ref.get("evidence_unit_id") or "")
    if uid not in units:
        raise ValueError("EVIDENCE_UNIT_REFERENCE_NOT_FOUND")
    index=ref.get("numeric_literal_index")
    if not isinstance(index,int) or index<0:
        raise ValueError("NUMERIC_LITERAL_INDEX_INVALID")
    nums=_numbers(units[uid])
    if index>=len(nums):
        raise ValueError("NUMERIC_LITERAL_INDEX_INVALID")
    x=dict(nums[index])
    x.update({
        "evidence_unit_id":uid,
        "text_sha256":units[uid]["text_sha256"],
        "source_url":units[uid]["source_url"],
    })
    return x

def _threshold(units,spec,expected_unit):
    if isinstance(spec,dict):
        x=_resolve_numeric(units,spec)
        value=x["value"]; unit=x["unit"]; provenance=x
    elif isinstance(spec,(int,float,str)) and not isinstance(spec,bool):
        m=re.fullmatch(
            r"\s*([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
            r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?\s*",
            str(spec),
        )
        if not m:
            raise ValueError("NUMERIC_RELATION_THRESHOLD_INVALID")
        value=Decimal(m.group(1).replace(",",""))
        unit=_canon(m.group(2)).lower().rstrip(".,;:")
        provenance=None
    else:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_REQUIRED")
    if value<0:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_NEGATIVE")
    if unit!=expected_unit:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_UNIT_MISMATCH")
    return value,unit,provenance

def evaluate(extraction,spec):
    units=_validated_units(extraction)
    if not isinstance(spec,dict):
        raise ValueError("CLAIM_RELATION_SPEC_INVALID")
    mode=str(spec.get("mode") or "").upper()
    base={
        "schema":SCHEMA,
        "mode":mode,
        "semantic_entailment_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "causal_direction_status":"UNVERIFIED",
        "evidence_quality_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "source_independence_status":"UNVERIFIED",
        "numeric_literal_semantic_role_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }

    if mode=="VERBATIM_SUPPORT":
        claim=_canon(spec.get("claim_text"))
        if not claim:
            raise ValueError("CLAIM_TEXT_REQUIRED")
        requested=spec.get("evidence_unit_id")
        candidates=[units[str(requested)]] if requested is not None and str(requested) in units else list(units.values())
        if requested is not None and str(requested) not in units:
            raise ValueError("EVIDENCE_UNIT_REFERENCE_NOT_FOUND")
        needle=claim.casefold()
        matches=[]
        for unit in candidates:
            hay=unit["text"].casefold()
            pos=hay.find(needle)
            if pos>=0:
                matches.append({
                    "evidence_unit_id":unit["evidence_unit_id"],
                    "source_url":unit["source_url"],
                    "text_sha256":unit["text_sha256"],
                    "claim_text":claim,
                    "match_start":pos,
                    "match_end":pos+len(claim),
                })
        return {
            **base,
            "status":"EXACT_TEXT_SUPPORT_VERIFIED" if matches else "EXACT_TEXT_SUPPORT_NOT_VERIFIED",
            "support_scope":"EXACT_NORMALIZED_SUBSTRING_OCCURRENCE_ONLY",
            "claim_text":claim,
            "matches":matches,
            "output_verified":True,
        }

    if mode=="NUMERIC_RELATION":
        op=str(spec.get("operator") or "").upper()
        if op not in OPS:
            raise ValueError("NUMERIC_RELATION_OPERATOR_INVALID")
        left=_resolve_numeric(units,spec.get("left"))
        right=_resolve_numeric(units,spec.get("right"))
        if left["unit"]!=right["unit"]:
            raise ValueError("NUMERIC_RELATION_UNIT_MISMATCH")
        lv,rv=left["value"],right["value"]
        threshold_value=None
        threshold_unit=None
        threshold_provenance=None
        if op=="LT": predicate=lv<rv
        elif op=="LTE": predicate=lv<=rv
        elif op=="GT": predicate=lv>rv
        elif op=="GTE": predicate=lv>=rv
        elif op=="EQ": predicate=lv==rv
        elif op=="NE": predicate=lv!=rv
        else:
            threshold_value,threshold_unit,threshold_provenance=_threshold(units,spec.get("threshold"),left["unit"])
            predicate=abs(lv-rv)<=threshold_value
        def public(x):
            return {
                **{k:v for k,v in x.items() if k!="value"},
                "value":str(x["value"]),
            }
        return {
            **base,
            "status":"NUMERIC_RELATION_VERIFIED",
            "relation_scope":"EXPLICIT_DECIMAL_RELATION_OVER_CALLER_REFERENCED_LITERALS_ONLY",
            "operator":op,
            "predicate":bool(predicate),
            "left":public(left),
            "right":public(right),
            "threshold":(
                {
                    "value":str(threshold_value),
                    "unit":threshold_unit,
                    "provenance":public(threshold_provenance) if threshold_provenance else None,
                }
                if threshold_value is not None else None
            ),
            "output_verified":True,
        }

    raise ValueError("CLAIM_RELATION_MODE_UNSUPPORTED")

def run(args,root):
    args=dict(args or {})
    extraction_path=_safe_path(root,args.get("extraction_path"))
    output_path=_safe_path(root,args.get("output_path"))
    if not extraction_path.is_file():
        raise ValueError("EXTRACTION_INPUT_MISSING")
    extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
    spec=args.get("spec")
    if spec is None and args.get("spec_path"):
        sp=_safe_path(root,args.get("spec_path"))
        if not sp.is_file():
            raise ValueError("CLAIM_RELATION_SPEC_MISSING")
        spec=json.loads(sp.read_text(encoding="utf-8"))
    result=evaluate(extraction,spec)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(output_path.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    return result
