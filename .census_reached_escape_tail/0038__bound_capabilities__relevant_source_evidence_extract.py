#!/usr/bin/env python3
"""Extract provenance-bound objective-anchored evidence from a verified relevant page.

This composes the already-qualified first-party objective relevance verifier and
captures the exact same fresh page bytes it verifies. It emits bounded textual
claim candidates and numeric literals with hashes/provenance. It does NOT claim
that extracted text is factually correct, sufficient, causal, or supportive of
a requested conclusion.
"""
from __future__ import annotations
import hashlib
import html
import importlib.util
import pathlib
import re

SCHEMA="PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"

def _load_relevance():
    path=pathlib.Path(__file__).resolve().with_name("first_party_objective_relevance_verify.py")
    spec=importlib.util.spec_from_file_location("project_brain_evidence_relevance",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RELEVANCE_VERIFIER_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _canon(text):
    return " ".join(str(text or "").split())

def _sentences(text):
    text=_canon(text)
    if not text:
        return []
    parts=re.split(r"(?<=[.!?])\s+|\s*[|•]\s*",text)
    out=[]
    for part in parts:
        part=_canon(part)
        if 35<=len(part)<=1200:
            out.append(part)
        elif len(part)>1200:
            for i in range(0,len(part),800):
                chunk=_canon(part[i:i+800])
                if len(chunk)>=35: out.append(chunk)
    return out

def _words(text):
    return set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()))

def _numbers(text):
    vals=re.findall(
      r"(?<![A-Za-z0-9])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?(?:\s*%|\s*[A-Za-zµμ°/][A-Za-z0-9µμ°/^*.-]{0,15})?",
      str(text or "")
    )
    out=[]
    for v in vals:
        v=_canon(v)
        if v and v not in out: out.append(v)
    return out[:24]

def extract(objective,candidate,provenance,authority_identity,timeout=20,fetch=None,max_passages=10):
    relevance=_load_relevance()
    captured={}
    underlying=fetch or relevance._fetch
    def capture(url,t):
        result=underlying(url,t)
        captured["result"]=result
        return result
    rel=relevance.verify(
      objective,candidate,provenance,authority_identity,timeout=timeout,fetch=capture
    )
    base={
      "schema":SCHEMA,
      "relevance_verification":rel,
      "claim_scope":"VERBATIM_OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATES_FROM_THE_SAME_FRESH_PAGE_BYTES",
      "factual_correctness_status":"UNVERIFIED",
      "claim_support_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "semantic_entailment_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if rel.get("status")!="FIRST_PARTY_RELEVANT_SOURCE_VERIFIED":
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"VERIFIED_RELEVANT_SOURCE_REQUIRED","evidence_records":[]}
    if "result" not in captured:
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"VERIFIED_PAGE_BYTES_NOT_CAPTURED","evidence_records":[]}
    raw,url,ctype,http_status=captured["result"]
    raw=bytes(raw)
    decoded=raw.decode("utf-8","replace")
    if "html" in str(ctype).lower() or "<html" in decoded[:1000].lower():
        parser=relevance._Visible()
        try: parser.feed(decoded)
        except Exception: pass
        visible=html.unescape(" ".join(parser.parts))
    else:
        visible=decoded
    objective_tokens=list(rel.get("objective_tokens") or [])
    rows=[]
    for ordinal,passage in enumerate(_sentences(visible)):
        wordset=_words(passage)
        matched=[t for t in objective_tokens if t in wordset]
        if not matched:
            continue
        nums=_numbers(passage)
        rows.append({
          "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
          "ordinal":ordinal,
          "text":passage,
          "text_sha256":hashlib.sha256(passage.encode("utf-8")).hexdigest(),
          "matched_objective_tokens":matched,
          "matched_objective_token_count":len(matched),
          "numeric_literals":nums,
          "numeric_literal_count":len(nums),
          "source_url":str(rel.get("fresh_url") or url),
        })
    rows.sort(key=lambda x:(-x["matched_objective_token_count"],-x["numeric_literal_count"],x["ordinal"]))
    limit=max(1,min(int(max_passages),20))
    rows=rows[:limit]
    if not rows:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"NO_OBJECTIVE_ANCHORED_PASSAGES_AFTER_VERIFIED_RELEVANCE",
          "fresh_url":rel.get("fresh_url"),
          "page_sha256":hashlib.sha256(raw).hexdigest(),
          "evidence_records":[]
        }
    return {
      **base,
      "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
      "fresh_url":rel.get("fresh_url"),
      "http_status":http_status,
      "content_type":ctype,
      "page_sha256":hashlib.sha256(raw).hexdigest(),
      "evidence_record_count":len(rows),
      "evidence_records":rows,
      "output_verified":True,
    }
