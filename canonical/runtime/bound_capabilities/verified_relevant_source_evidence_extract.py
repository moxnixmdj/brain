#!/usr/bin/env python3
"""Bounded model-independent evidence passage extraction.

Consumes only an upstream FIRST_PARTY_RELEVANT_SOURCE_VERIFIED receipt, re-fetches
that exact URL, revalidates exact host and objective-token continuity, and emits
verbatim visible-text passages ranked by lexical support for the same objective.

This capability does NOT establish semantic entailment, factual correctness,
primary-source status, evidence sufficiency, or claim endorsement.
"""
from __future__ import annotations

import html
import ipaddress
import json
import math
import pathlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_VERIFIED_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"
UA="ProjectBrain-EvidenceExtraction/1.0"

_STOP={
 "about","above","after","again","against","also","among","and","are","because",
 "been","being","between","both","can","could","determine","does","during","each",
 "evaluate","evidence","from","have","identify","into","investigate","more","most",
 "objective","primary","provide","provides","published","research","source",
 "sources","than","that","the","their","then","there","these","this","those",
 "through","under","using","whether","which","while","with","would","assess",
 "authoritative","independent","verify","verification","result","results",
}
_GENERIC={
 "technical","information","report","page","official","organization","university",
 "institute","institution","data","study","analysis","comparison",
}
_BLOCK={"p","li","td","th","h1","h2","h3","h4","h5","h6","article","section","div","br"}

class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.current=[]; self.skip=0; self.title=[]; self.in_title=False
    def _flush(self):
        text=" ".join(" ".join(self.current).split())
        if text: self.parts.append(text)
        self.current=[]
    def handle_starttag(self,tag,attrs):
        low=tag.lower()
        if low in {"script","style","noscript","svg"}: self.skip+=1
        if low=="title": self.in_title=True
        if low in _BLOCK and self.current: self._flush()
    def handle_endtag(self,tag):
        low=tag.lower()
        if low in {"script","style","noscript","svg"} and self.skip: self.skip-=1
        if low=="title": self.in_title=False
        if low in _BLOCK and self.current: self._flush()
    def handle_data(self,data):
        if self.skip: return
        text=" ".join(str(data or "").split())
        if not text: return
        self.current.append(text)
        if self.in_title: self.title.append(text)
    def close(self):
        super().close()
        if self.current: self._flush()

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(text):
    out=[]
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()):
        t=raw.strip("._+-")
        if len(t)<4 or t in _STOP or t in _GENERIC: continue
        if t not in out: out.append(t)
    return out

def _norm_host(raw):
    text=str(raw or "").strip()
    if not text: return None
    try:
        host=(urllib.parse.urlsplit(text).hostname or "") if "://" in text else text
    except Exception:
        return None
    host=host.lower().strip(".")
    if host.startswith("www."): host=host[4:]
    if not host or "." not in host or host.endswith((".local",".internal")): return None
    try: ip=ipaddress.ip_address(host)
    except ValueError: ip=None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+",host): return None
    return host

def _safe_url(raw):
    try: u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception: return None
    if u.scheme not in {"http","https"} or not u.hostname or not _norm_host(u.hostname): return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path or "/",u.query,""))

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _fetch(url,timeout=20,max_bytes=1_500_000):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.4"})
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes)
        return raw,r.geturl(),str(r.headers.get("Content-Type") or ""),int(getattr(r,"status",200))

def _visible(raw,ctype):
    text=raw.decode("utf-8","replace")
    if "html" not in str(ctype).lower() and "<html" not in text[:1000].lower():
        parts=[_canon(x) for x in re.split(r"[\r\n]+",text) if _canon(x)]
        return parts,None
    parser=_Visible()
    try:
        parser.feed(text); parser.close()
    except Exception:
        pass
    return [html.unescape(_canon(x)) for x in parser.parts if _canon(x)],_canon(" ".join(parser.title)) or None

def _windows(parts):
    cleaned=[_canon(x) for x in parts if 24<=len(_canon(x))<=2200]
    out=[]
    for i in range(len(cleaned)):
        joined=""
        for width in range(1,4):
            if i+width>len(cleaned): break
            joined=_canon(" ".join(cleaned[i:i+width]))
            if len(joined)>2400: break
            if len(joined)>=40: out.append((i,width,joined))
    seen=set(); unique=[]
    for row in out:
        if row[2] in seen: continue
        seen.add(row[2]); unique.append(row)
    return unique

def extract_from_visible_text(objective,parts,limit=5):
    objective=_canon(objective)
    q=_tokens(objective)
    if not q:
        return {"status":"EXTRACTION_UNRESOLVED","reason":"NO_DISCRIMINATIVE_OBJECTIVE_TOKENS","passages":[]}
    rows=[]
    for index,width,text in _windows(parts):
        words=set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",text.lower()))
        matched=[t for t in q if t in words]
        if not matched: continue
        numeric=bool(re.search(r"(?<![A-Za-z])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?:\s*[%A-Za-z][A-Za-z0-9/%^.-]*)?",text))
        coverage=len(matched)/len(q)
        score=(len(matched)*10.0)+(coverage*5.0)+(0.5 if numeric else 0.0)-(0.001*len(text))
        rows.append({
          "text":text,
          "matched_objective_tokens":matched,
          "objective_token_coverage":round(coverage,6),
          "contains_numeric_text":numeric,
          "score":round(score,6),
          "source_block_index":index,
          "source_block_span":width,
        })
    rows.sort(key=lambda x:(-x["score"],-len(x["matched_objective_tokens"]),x["source_block_index"],x["text"]))
    required=1 if len(q)<=3 else 2
    rows=[x for x in rows if len(x["matched_objective_tokens"])>=required]
    if not rows:
        return {"status":"EXTRACTION_UNRESOLVED","reason":"NO_PASSAGE_WITH_BOUNDED_OBJECTIVE_SUPPORT","passages":[]}
    return {
      "status":"VERBATIM_EVIDENCE_PASSAGES_EXTRACTED",
      "objective":objective,
      "objective_tokens":q,
      "passages":rows[:max(1,min(int(limit),8))],
    }

def extract(objective,relevance_receipt,timeout=20,limit=5,fetch=None):
    receipt=dict(relevance_receipt or {})
    base={
      "schema":SCHEMA,
      "evidence_claim_scope":"VERBATIM_VISIBLE_TEXT_WITH_BOUNDED_LEXICAL_OBJECTIVE_SUPPORT_ONLY",
      "semantic_entailment_status":"UNVERIFIED",
      "primary_source_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "claim_endorsement_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if receipt.get("status")!="FIRST_PARTY_RELEVANT_SOURCE_VERIFIED":
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"VERIFIED_RELEVANT_SOURCE_RECEIPT_REQUIRED","passages":[]}
    if receipt.get("first_party_source_status")!="VERIFIED" or receipt.get("objective_relevance_status")!="VERIFIED":
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"UPSTREAM_VERIFICATION_INCOMPLETE","passages":[]}
    objective=_canon(objective)
    if not objective:
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"OBJECTIVE_REQUIRED","passages":[]}
    q=_tokens(objective)
    if q!=list(receipt.get("objective_tokens") or []):
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"OBJECTIVE_TOKEN_BINDING_MISMATCH","passages":[]}
    url=_safe_url(receipt.get("fresh_url"))
    bound=_norm_host(receipt.get("bound_domain"))
    if not url or not bound or _norm_host(url)!=bound:
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"UPSTREAM_URL_DOMAIN_BINDING_INVALID","passages":[]}
    fetch=fetch or _fetch
    try:
        raw,observed,ctype,http_status=fetch(url,timeout)
    except Exception as exc:
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"FRESH_SOURCE_FETCH_FAILED","error_class":type(exc).__name__,"passages":[]}
    observed=_safe_url(observed)
    if not observed or _norm_host(observed)!=bound:
        return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"FRESH_SOURCE_REDIRECT_OUTSIDE_BOUND_DOMAIN","passages":[]}
    parts,title=_visible(raw,ctype)
    extracted=extract_from_visible_text(objective,parts,limit=limit)
    if extracted.get("status")!="VERBATIM_EVIDENCE_PASSAGES_EXTRACTED":
        return {**base,**extracted,"source_url":observed,"bound_domain":bound,"http_status":http_status,"page_title":title}
    visible=" ".join(parts)
    for passage in extracted["passages"]:
        if passage["text"] not in visible:
            return {**base,"status":"EXTRACTION_UNRESOLVED","reason":"VERBATIM_PASSAGE_CHECK_FAILED","passages":[]}
    return {
      **base,
      **extracted,
      "source_url":observed,
      "bound_domain":bound,
      "http_status":http_status,
      "content_type":ctype,
      "page_title":title,
      "upstream_relevance_method":receipt.get("verification_method"),
      "output_verified":True,
    }

def run(args,root):
    args=dict(args or {})
    inp=_safe_path(root,args.get("relevance_receipt_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise ValueError("RELEVANCE_RECEIPT_MISSING")
    receipt=json.loads(inp.read_text(encoding="utf-8"))
    result=extract(args.get("objective"),receipt,timeout=args.get("timeout_s",20),limit=args.get("limit",5))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="VERBATIM_EVIDENCE_PASSAGES_EXTRACTED"
    return result
