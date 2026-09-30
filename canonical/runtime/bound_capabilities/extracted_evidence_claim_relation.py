#!/usr/bin/env python3
"""Typed claim support and numeric relation evaluation over extracted evidence.

Verified scope:
- exact normalized verbatim substring support inside provenance-bound extracted passages;
- explicit numeric relations over caller-referenced extracted numeric literals.

Not verified: paraphrase/semantic entailment, factual correctness, evidence
sufficiency, causality, or whether a numeric literal has the intended meaning.
"""
from __future__ import annotations
import json, math, pathlib, re
from decimal import Decimal, InvalidOperation

SCHEMA="PROJECT_BRAIN_EXTRACTED_EVIDENCE_CLAIM_RELATION_V1"
EXTRACTION_SCHEMA="PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"
NUM_RE=re.compile(r"^\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
OPS={"LT","LTE","GT","GTE","EQ","NE","ABS_DIFF_LTE"}

def _canon(x):
    return " ".join(str(x or "").split())

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve(); p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load_extraction(data):
    if not isinstance(data,dict) or data.get("schema")!=EXTRACTION_SCHEMA:
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if data.get("status")!="OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED" or not data.get("output_verified"):
        raise ValueError("VERIFIED_EXTRACTION_REQUIRED")
    rows=data.get("evidence_records")
    if not isinstance(rows,list) or not rows: raise ValueError("EXTRACTED_EVIDENCE_REQUIRED")
    out=[]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict): raise ValueError("EVIDENCE_RECORD_INVALID")
        ordinal=row.get("ordinal")
        if not isinstance(ordinal,int) or ordinal<0 or ordinal in seen: raise ValueError("EVIDENCE_ORDINAL_INVALID")
        seen.add(ordinal)
        text=_canon(row.get("text"))
        nums=row.get("numeric_literals")
        if not text or not isinstance(nums,list): raise ValueError("EVIDENCE_RECORD_CONTRACT_INVALID")
        out.append({
          "ordinal":ordinal,
          "text":text,
          "text_sha256":str(row.get("text_sha256") or ""),
          "source_url":str(row.get("source_url") or data.get("fresh_url") or ""),
          "numeric_literals":[str(x) for x in nums],
        })
    return out

def _row(rows,ordinal):
    found=[x for x in rows if x["ordinal"]==ordinal]
    if len(found)!=1: raise ValueError("EVIDENCE_ORDINAL_NOT_FOUND")
    return found[0]

def _literal(rows,ref):
    if not isinstance(ref,dict): raise ValueError("NUMERIC_REFERENCE_INVALID")
    row=_row(rows,int(ref.get("record_ordinal")))
    idx=ref.get("numeric_literal_index")
    if not isinstance(idx,int) or idx<0 or idx>=len(row["numeric_literals"]):
        raise ValueError("NUMERIC_LITERAL_INDEX_INVALID")
    raw=row["numeric_literals"][idx]
    m=NUM_RE.fullmatch(raw)
    if not m: raise ValueError("NUMERIC_LITERAL_PARSE_FAILED")
    try: value=Decimal(m.group(1))
    except InvalidOperation as exc: raise ValueError("NUMERIC_LITERAL_PARSE_FAILED") from exc
    if not value.is_finite(): raise ValueError("NUMERIC_LITERAL_NONFINITE")
    unit=_canon(m.group(2)).lower()
    return {"value":value,"unit":unit,"raw":raw,"record_ordinal":row["ordinal"],"numeric_literal_index":idx,"source_url":row["source_url"],"text_sha256":row["text_sha256"]}

def _unit_compatible(a,b):
    return a["unit"]==b["unit"]

def evaluate(extraction,claim_spec):
    rows=_load_extraction(extraction)
    if not isinstance(claim_spec,dict): raise ValueError("CLAIM_SPEC_INVALID")
    mode=str(claim_spec.get("mode") or "").upper()
    base={
      "schema":SCHEMA,
      "claim_mode":mode,
      "factual_correctness_status":"UNVERIFIED",
      "semantic_entailment_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "causality_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if mode=="VERBATIM_TEXT":
        claim=_canon(claim_spec.get("claim_text"))
        if not claim: raise ValueError("CLAIM_TEXT_REQUIRED")
        ordinal=claim_spec.get("record_ordinal")
        candidates=[_row(rows,ordinal)] if isinstance(ordinal,int) else rows
        matches=[]
        needle=claim.casefold()
        for row in candidates:
            if needle in row["text"].casefold():
                matches.append({
                  "record_ordinal":row["ordinal"],
                  "source_url":row["source_url"],
                  "text_sha256":row["text_sha256"],
                  "matched_text":claim,
                })
        return {
          **base,
          "status":"SUPPORT_VERIFIED" if matches else "SUPPORT_NOT_VERIFIED",
          "support_method":"EXACT_NORMALIZED_VERBATIM_SUBSTRING",
          "claim_text":claim,
          "matches":matches,
          "output_verified":True,
        }
    if mode=="NUMERIC_RELATION":
        op=str(claim_spec.get("operator") or "").upper()
        if op not in OPS: raise ValueError("NUMERIC_RELATION_OPERATOR_INVALID")
        left=_literal(rows,claim_spec.get("left"))
        right=_literal(rows,claim_spec.get("right"))
        if not _unit_compatible(left,right): raise ValueError("NUMERIC_RELATION_UNIT_MISMATCH")
        lv,rv=left["value"],right["value"]
        threshold=None
        if op=="LT": pred=lv<rv
        elif op=="LTE": pred=lv<=rv
        elif op=="GT": pred=lv>rv
        elif op=="GTE": pred=lv>=rv
        elif op=="EQ": pred=lv==rv
        elif op=="NE": pred=lv!=rv
        else:
            raw=claim_spec.get("threshold")
            if isinstance(raw,(int,float,str)):
                m=NUM_RE.fullmatch(str(raw))
                if not m: raise ValueError("NUMERIC_RELATION_THRESHOLD_INVALID")
                threshold={"value":Decimal(m.group(1)),"unit":_canon(m.group(2)).lower()}
            elif isinstance(raw,dict):
                threshold=_literal(rows,raw)
            else: raise ValueError("NUMERIC_RELATION_THRESHOLD_REQUIRED")
            if threshold["value"]<0: raise ValueError("NUMERIC_RELATION_THRESHOLD_NEGATIVE")
            if threshold.get("unit","")!=left["unit"]: raise ValueError("NUMERIC_RELATION_THRESHOLD_UNIT_MISMATCH")
            pred=abs(lv-rv)<=threshold["value"]
        return {
          **base,
          "status":"RELATION_VERIFIED",
          "relation_method":"EXPLICIT_DECIMAL_RELATION_OVER_REFERENCED_EXTRACTED_LITERALS",
          "operator":op,
          "predicate":bool(pred),
          "left":{**left,"value":str(left["value"])},
          "right":{**right,"value":str(right["value"])},
          "threshold":({**threshold,"value":str(threshold["value"])} if isinstance(threshold,dict) else None),
          "output_verified":True,
        }
    raise ValueError("CLAIM_MODE_UNSUPPORTED")

def run(args,root):
    inp=_safe_path(root,args.get("extraction_path")); out=_safe_path(root,args.get("output_path"))
    if not inp.is_file(): raise ValueError("EXTRACTION_INPUT_MISSING")
    data=json.loads(inp.read_text(encoding="utf-8"))
    claim=args.get("claim_spec")
    if claim is None:
        claim_path=args.get("claim_spec_path")
        if claim_path:
            cp=_safe_path(root,claim_path)
            if not cp.is_file(): raise ValueError("CLAIM_SPEC_MISSING")
            claim=json.loads(cp.read_text(encoding="utf-8"))
    result=evaluate(data,claim)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    return result
