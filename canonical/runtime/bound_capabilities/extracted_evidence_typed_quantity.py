#!/usr/bin/env python3
"""Type numeric quantity candidates already extracted from provenance-bound evidence.

This is deliberately narrower than semantic claim understanding. It converts
verbatim numeric literal surfaces into finite numeric values plus literal unit
surfaces and preserves the exact passage/source provenance. It never guesses a
unit, converts units, binds operands to objective entities, or claims truth.
"""
from __future__ import annotations
import math
import re

SCHEMA="PROJECT_BRAIN_TYPED_QUANTITY_CANDIDATES_V1"
NUM=re.compile(
  r"^\s*(?P<value>[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)"
  r"(?P<unit>.*)\s*$"
)
SAFE_UNIT=re.compile(r"^[%A-Za-zµμ°][%A-Za-z0-9µμ°/^*._-]{0,23}$")

def _canon(v):
    return " ".join(str(v or "").strip().split())

def _parse_surface(surface):
    s=_canon(surface)
    m=NUM.match(s)
    if not m:
        return None
    try:
        value=float(m.group("value"))
    except Exception:
        return None
    if not math.isfinite(value):
        return None
    unit=_canon(m.group("unit"))
    if unit:
        if " " in unit or not SAFE_UNIT.fullmatch(unit):
            return None
    else:
        unit=None
    return {"value":value,"unit_surface":unit,"surface":s}

def extract(evidence_result):
    if not isinstance(evidence_result,dict) or evidence_result.get("status")!="OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED":
        return {
          "schema":SCHEMA,"status":"TYPED_QUANTITY_EXTRACTION_BLOCKED",
          "reason":"VERIFIED_EXTRACTED_EVIDENCE_REQUIRED",
          "typed_quantity_candidates":[],
          "model_dependency_count":0,"incremental_spend_usd":0,
        }
    out=[]
    seen=set()
    for record in evidence_result.get("evidence_records") or []:
        if not isinstance(record,dict):
            continue
        text_sha=str(record.get("text_sha256") or "")
        source_url=str(record.get("source_url") or evidence_result.get("fresh_url") or "")
        for surface in record.get("numeric_literals") or []:
            parsed=_parse_surface(surface)
            if parsed is None:
                continue
            key=(text_sha,parsed["surface"])
            if key in seen:
                continue
            seen.add(key)
            out.append({
              "record_type":"PROVENANCE_BOUND_TYPED_QUANTITY_CANDIDATE",
              "value":parsed["value"],
              "unit_surface":parsed["unit_surface"],
              "surface":parsed["surface"],
              "source_url":source_url,
              "page_sha256":evidence_result.get("page_sha256"),
              "passage_text_sha256":text_sha,
              "passage_text":record.get("text"),
              "matched_objective_tokens":list(record.get("matched_objective_tokens") or []),
              "factual_correctness_status":"UNVERIFIED",
              "semantic_role_status":"UNBOUND",
            })
    return {
      "schema":SCHEMA,
      "status":"TYPED_QUANTITY_CANDIDATES_EXTRACTED" if out else "NO_TYPED_QUANTITY_CANDIDATES",
      "typed_quantity_candidate_count":len(out),
      "typed_quantity_candidates":out,
      "unit_normalization_status":"NOT_PERFORMED",
      "operand_binding_status":"NOT_PERFORMED",
      "factual_correctness_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
