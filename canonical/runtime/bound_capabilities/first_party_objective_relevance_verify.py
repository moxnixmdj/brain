#!/usr/bin/env python3
"""Fail-closed first-party source and objective-relevance verification.

This capability proves only two narrow facts for a live web candidate:
1. the freshly retrieved page remains on the exact domain independently bound
   to the source organization by the qualified ROR identity primitive; and
2. the freshly retrieved page text has bounded lexical evidence of relevance
   to the supplied research objective.

It deliberately does NOT claim original/primary research status, factual
correctness, evidence sufficiency, or endorsement of a downstream conclusion.
"""
from __future__ import annotations

import html
import ipaddress
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_FIRST_PARTY_OBJECTIVE_RELEVANCE_V1"
UA="ProjectBrain-FirstPartyRelevance/1.0"

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
        if self.skip: return
        text=" ".join(str(data or "").split())
        if not text: return
        self.parts.append(text)
        if self.in_title: self.title.append(text)

def _norm_host(raw):
    text=str(raw or "").strip()
    if not text: return None
    try:
        host=(urllib.parse.urlsplit(text).hostname or "") if "://" in text else text
    except Exception:
        return None
    host=host.lower().strip(".")
    if host.startswith("www."): host=host[4:]
    if not host or "." not in host or host.endswith((".local",".internal")):
        return None
    try: ip=ipaddress.ip_address(host)
    except ValueError: ip=None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+",host): return None
    return host

def _safe_url(raw):
    try: u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception: return None
    if u.scheme not in {"http","https"} or not u.hostname: return None
    if not _norm_host(u.hostname): return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path or "/",u.query,""))

def _tokens(text):
    out=[]
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()):
        t=raw.strip("._+-")
        if len(t)<4 or t in _STOP or t in _GENERIC: continue
        if t not in out: out.append(t)
    return out

def _fetch(url,timeout=20,max_bytes=1_500_000):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.4"})
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes)
        final=r.geturl()
        ctype=str(r.headers.get("Content-Type") or "")
        status=int(getattr(r,"status",200))
    return raw,final,ctype,status

def verify(objective,candidate,provenance,authority_identity,timeout=20,fetch=None):
    objective=" ".join(str(objective or "").strip().split())
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    authority_identity=dict(authority_identity or {})
    base={
      "schema":SCHEMA,
      "first_party_source_status":"UNVERIFIED",
      "objective_relevance_status":"UNVERIFIED",
      "primary_source_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"status":"UNVERIFIED","reason":"OBJECTIVE_REQUIRED"}
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base,"status":"UNVERIFIED","reason":"LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}
    if authority_identity.get("status")!="AUTHORITY_IDENTITY_VERIFIED":
        return {**base,"status":"UNVERIFIED","reason":"QUALIFIED_AUTHORITY_IDENTITY_REQUIRED"}
    matched=_norm_host(authority_identity.get("matched_domain"))
    final_url=_safe_url(provenance.get("final_url") or candidate.get("url"))
    final_host=_norm_host(provenance.get("final_host") or final_url)
    if not matched or not final_url or final_host!=matched:
        return {
          **base,"status":"UNVERIFIED","reason":"PROVENANCE_HOST_NOT_EXACT_BOUND_AUTHORITY_DOMAIN",
          "bound_domain":matched,"provenance_host":final_host,
        }

    fetch=fetch or _fetch
    try:
        raw,observed_url,ctype,http_status=fetch(final_url,timeout)
    except Exception as exc:
        return {
          **base,"status":"UNVERIFIED","reason":"FRESH_SOURCE_FETCH_FAILED",
          "error_class":type(exc).__name__,
        }
    observed_safe=_safe_url(observed_url)
    observed_host=_norm_host(observed_safe)
    if not observed_safe or observed_host!=matched:
        return {
          **base,"status":"UNVERIFIED","reason":"FRESH_SOURCE_REDIRECT_OUTSIDE_BOUND_AUTHORITY_DOMAIN",
          "bound_domain":matched,"fresh_host":observed_host,
        }

    text=raw.decode("utf-8","replace")
    parser=_Visible()
    if "html" in ctype.lower() or "<html" in text[:1000].lower():
        try: parser.feed(text)
        except Exception: pass
        visible=html.unescape(" ".join(parser.parts))
        title=" ".join(parser.title)
    else:
        visible=text
        title=""
    blob_words=set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",(title+" "+visible).lower()))
    url_words=set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",observed_safe.lower()))
    salient=_tokens(objective)
    matched_body=[t for t in salient if t in blob_words]
    matched_title_or_url=[t for t in salient if t in set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",title.lower()))|url_words]
    long_matches=[t for t in matched_body if len(t)>=7 or any(ch.isdigit() for ch in t)]
    required=2 if len(salient)<=8 else 3
    relevance=bool(
        len(matched_body)>=required
        and (
          bool(matched_title_or_url)
          or len(long_matches)>=2
        )
    )
    if not relevance:
        return {
          **base,
          "status":"FIRST_PARTY_SOURCE_VERIFIED__OBJECTIVE_RELEVANCE_UNRESOLVED",
          "first_party_source_status":"VERIFIED",
          "reason":"INSUFFICIENT_FRESH_OBJECTIVE_TERM_COVERAGE",
          "bound_domain":matched,"fresh_url":observed_safe,"http_status":http_status,
          "objective_tokens":salient,"matched_body_tokens":matched_body,
          "matched_title_or_url_tokens":matched_title_or_url,
        }
    return {
      **base,
      "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
      "first_party_source_status":"VERIFIED",
      "objective_relevance_status":"VERIFIED",
      "verification_method":"EXACT_ROR_DOMAIN_PLUS_FRESH_PAGE_OBJECTIVE_TERM_COVERAGE",
      "bound_domain":matched,
      "fresh_url":observed_safe,
      "http_status":http_status,
      "content_type":ctype,
      "page_title":" ".join(title.split()) or None,
      "objective_tokens":salient,
      "matched_body_tokens":matched_body,
      "matched_title_or_url_tokens":matched_title_or_url,
      "scope_note":"Verifies first-party hosting by the independently bound organization and bounded lexical objective relevance only. Original/primary research status, factual correctness, evidence sufficiency, and claim endorsement remain unverified.",
    }
