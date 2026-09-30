#!/usr/bin/env python3
"""Generic evidence extraction from provenance-verified BM25-selected web sources.

ROR/organization identity is intentionally not required. This capability reuses
the already-qualified BM25 lexical relevance ranker, requires live retrieval
provenance, re-fetches the selected source, requires the fresh fetch to remain on
the same normalized host, and emits verbatim objective-anchored passages plus
numeric literals. It makes no authority, truth, support, or sufficiency claim.
"""
from __future__ import annotations
import hashlib
import html
import importlib.util
import pathlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_GENERIC_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"
UA="ProjectBrain-GenericEvidenceExtraction/1.0"

def _load(name):
    path=pathlib.Path(__file__).resolve().with_name(name+".py")
    spec=importlib.util.spec_from_file_location("project_brain_generic_"+name,path)
    if spec is None or spec.loader is None: raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _canon(v): return " ".join(str(v or "").strip().split())

def _host(url):
    try:
        h=(urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h

class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0; self.title=[]; self.in_title=False
    def handle_starttag(self,tag,attrs):
        low=tag.lower()
        if low in {"script","style","noscript","svg"}: self.skip+=1
        if low=="title": self.in_title=True
    def handle_endtag(self,tag):
        low=tag.lower()
        if low in {"script","style","noscript","svg"} and self.skip: self.skip-=1
        if low=="title": self.in_title=False
    def handle_data(self,data):
        if self.skip:return
        t=_canon(data)
        if not t:return
        self.parts.append(t)
        if self.in_title:self.title.append(t)

def _fetch(url,timeout=20,max_bytes=1_500_000):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.4"})
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes); return raw,r.geturl(),str(r.headers.get("Content-Type") or ""),int(getattr(r,"status",200))

def _sentences(text):
    text=_canon(text)
    parts=re.split(r"(?<=[.!?])\s+|\s*[|•]\s*",text)
    return [x for x in (_canon(p) for p in parts) if 35<=len(x)<=1200]

def _numbers(text):
    vals=re.findall(
      r"(?<![A-Za-z0-9])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?(?:\s*%|\s*[A-Za-zµμ°/][A-Za-z0-9µμ°/^*.-]{0,15})?",
      str(text or "")
    )
    out=[]
    for v in vals:
        v=_canon(v)
        if v and v not in out:out.append(v)
    return out[:24]

def extract(objective,verified_candidates,timeout=20,max_passages=10,fetch=None):
    objective=_canon(objective)
    base={
      "schema":SCHEMA,"objective":objective,
      "authority_identity_required":False,"ror_metadata_requirement":"OPTIONAL",
      "claim_scope":"PROVENANCE_VERIFIED_BM25_SELECTED_SAME_HOST_FRESH_PAGE_OBJECTIVE_ANCHORED_PASSAGES",
      "factual_correctness_status":"UNVERIFIED","claim_support_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED","semantic_entailment_status":"UNVERIFIED",
      "model_dependency_count":0,"incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"OBJECTIVE_REQUIRED","evidence_records":[]}
    if not isinstance(verified_candidates,list):
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"CANDIDATES_REQUIRED","evidence_records":[]}
    eligible=[]
    for item in verified_candidates:
        if not isinstance(item,dict):continue
        candidate=dict(item.get("candidate") or {})
        prov=dict(item.get("verification") or item.get("provenance") or {})
        if prov.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":continue
        enriched=dict(candidate)
        if not enriched.get("title") and prov.get("page_title"):enriched["title"]=prov.get("page_title")
        eligible.append({"candidate":candidate,"provenance":prov,"rank_input":enriched})
    if not eligible:
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"RETRIEVAL_PROVENANCE_VERIFIED_CANDIDATE_REQUIRED","evidence_records":[]}

    bm25=_load("objective_relevance_bm25")
    ranking=bm25.rank(objective,[x["rank_input"] for x in eligible],limit=len(eligible))
    if ranking.get("status")!="LEXICAL_RELEVANCE_RANKED":
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"BM25_RELEVANCE_UNRESOLVED","relevance":ranking,"evidence_records":[]}

    fetch=fetch or _fetch
    objective_tokens=list(ranking.get("query_tokens") or [])
    failures=[]
    for ranked in ranking.get("ranked_candidates") or []:
        if float(ranked.get("lexical_relevance_score") or 0)<=0:continue
        i=int(ranked["original_index"])
        selected=eligible[i]
        prov=selected["provenance"]; candidate=selected["candidate"]
        url=str(prov.get("final_url") or candidate.get("url") or "")
        expected_host=_host(prov.get("final_host") or url)
        if not url or not expected_host:continue
        try: raw,observed,ctype,http_status=fetch(url,timeout)
        except Exception as exc:
            failures.append({"url":url,"reason":"FRESH_FETCH_FAILED","error_class":type(exc).__name__});continue
        observed_host=_host(observed)
        if observed_host!=expected_host:
            failures.append({"url":url,"reason":"FRESH_HOST_MISMATCH","expected_host":expected_host,"observed_host":observed_host});continue
        raw=bytes(raw); decoded=raw.decode("utf-8","replace")
        if "html" in ctype.lower() or "<html" in decoded[:1000].lower():
            p=_Visible()
            try:p.feed(decoded)
            except Exception:pass
            visible=html.unescape(" ".join(p.parts)); page_title=_canon(" ".join(p.title))
        else:
            visible=decoded; page_title=""
        records=[]
        for ordinal,passage in enumerate(_sentences(visible)):
            words=set(re.findall(r"[a-z0-9]+",passage.lower()))
            matched=[t for t in objective_tokens if t in words]
            if not matched:continue
            records.append({
              "record_type":"GENERIC_OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
              "ordinal":ordinal,"text":passage,
              "text_sha256":hashlib.sha256(passage.encode("utf-8")).hexdigest(),
              "matched_objective_tokens":matched,
              "matched_objective_token_count":len(matched),
              "numeric_literals":_numbers(passage),
              "source_url":observed,
              "source_host":observed_host,
              "retrieval_provenance_status":"VERIFIED",
              "ror_authority_status":"OPTIONAL_NOT_REQUIRED",
            })
        records.sort(key=lambda x:(-x["matched_objective_token_count"],-len(x["numeric_literals"]),x["ordinal"]))
        records=records[:max(1,min(int(max_passages),20))]
        if not records:
            failures.append({"url":observed,"reason":"NO_OBJECTIVE_ANCHORED_PASSAGES"});continue
        return {
          **base,
          "status":"GENERIC_OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
          "selected_candidate_original_index":i,
          "selected_candidate":candidate,
          "selected_provenance":prov,
          "bm25_relevance":ranking,
          "fresh_url":observed,"fresh_host":observed_host,"http_status":http_status,
          "content_type":ctype,"page_title":page_title or None,
          "page_sha256":hashlib.sha256(raw).hexdigest(),
          "evidence_record_count":len(records),"evidence_records":records,
          "fresh_same_host_verified":True,"output_verified":True,
          "candidate_failures_before_selection":failures,
        }
    return {**base,"status":"EXTRACTION_BLOCKED","reason":"NO_BM25_SELECTED_CANDIDATE_YIELDED_EVIDENCE","relevance":ranking,"candidate_failures":failures,"evidence_records":[]}
