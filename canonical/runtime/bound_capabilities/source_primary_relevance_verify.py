#!/usr/bin/env python3
"""Fail-closed model-independent primary-publication + objective-relevance verifier.

This verifier proves only a narrow source property:
1) the live document is served from the exact active ROR-bound organization
   domain already verified by source_authority_binding_ror; and
2) decision-relevant objective anchors are strongly present in the live
   document metadata/title surface.

It does NOT prove factual correctness, evidence sufficiency, experimental
validity, or that every statement in the document is firsthand evidence.
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_SOURCE_PRIMARY_RELEVANCE_VERIFICATION_V1"
UA="ProjectBrain-PrimaryRelevanceVerifier/1.0"

_STOP={
    "about","after","against","also","among","and","are","assess","assessment",
    "before","between","can","claim","compare","determine","does","evidence",
    "evaluate","experimental","find","for","from","identify","investigate","into",
    "more","published","research","source","than","that","the","their","these",
    "this","through","using","whether","with","would","yield",
}
_GENERIC={
    "authoritative","decision","document","primary","provenance","relevant",
    "relevance","technical","verified","verify",
}

def _canon(x):
    return " ".join(str(x or "").strip().split())

def _safe_url(raw):
    try:
        u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in ("http","https") or not u.netloc:
        return None
    host=(u.hostname or "").lower().strip(".")
    if not host or host in {"localhost","127.0.0.1","::1"} or host.endswith((".local",".internal")):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))

def _host(raw):
    url=_safe_url(raw)
    return (urllib.parse.urlsplit(url).hostname or "").lower().strip(".") if url else None

def _terms(text):
    raw=re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*",_canon(text).lower())
    out=[]
    for token in raw:
        if token in _STOP or token in _GENERIC:
            continue
        if len(token)<3 and not token.isdigit():
            continue
        if token not in out:
            out.append(token)
    return out

class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title=[]
        self.h1=[]
        self._in_title=False
        self._in_h1=False
        self.meta={}
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        a={str(k).lower():str(v or "") for k,v in attrs}
        if tag=="title":
            self._in_title=True
        elif tag=="h1":
            self._in_h1=True
        elif tag=="meta":
            key=(a.get("name") or a.get("property") or "").lower()
            val=_canon(html.unescape(a.get("content") or ""))
            if key and val and key not in self.meta:
                self.meta[key]=val
    def handle_data(self,data):
        if self._in_title:
            self.title.append(data)
        if self._in_h1:
            self.h1.append(data)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag=="title":
            self._in_title=False
        elif tag=="h1":
            self._in_h1=False

def _fetch(url,timeout):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":UA,
            "Accept":"text/html,application/xhtml+xml,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        body=r.read(1_500_000)
        return body,str(r.headers.get("Content-Type") or ""),int(getattr(r,"status",200)),r.geturl()

def _document_surface(body,ctype):
    if "html" not in str(ctype).lower():
        return {"title":"","h1":"","description":"","surface":""}
    p=_MetaParser()
    p.feed(body.decode("utf-8","replace"))
    title=_canon(html.unescape("".join(p.title)))
    h1=_canon(html.unescape(" ".join(p.h1)))
    desc=_canon(
        p.meta.get("description")
        or p.meta.get("og:description")
        or p.meta.get("twitter:description")
        or ""
    )
    citation_title=_canon(p.meta.get("citation_title") or p.meta.get("dc.title") or "")
    surface=_canon(" ".join(x for x in (title,citation_title,h1,desc) if x))
    return {
        "title":title or citation_title,
        "h1":h1,
        "description":desc,
        "surface":surface,
    }

def _relevance(objective,surface):
    anchors=_terms(objective)
    observed=set(_terms(surface))
    matched=[x for x in anchors if x in observed]
    if not anchors:
        return {
            "status":"UNVERIFIED",
            "reason":"NO_OBJECTIVE_ANCHORS",
            "objective_anchor_count":0,
            "matched_anchor_count":0,
            "coverage":0.0,
            "matched_anchors":[],
        }
    required_count=1 if len(anchors)==1 else 2
    required_coverage=1.0 if len(anchors)<=2 else 0.5
    coverage=len(matched)/len(anchors)
    verified=len(matched)>=required_count and coverage>=required_coverage
    return {
        "status":"OBJECTIVE_RELEVANCE_VERIFIED" if verified else "UNVERIFIED",
        "reason":None if verified else "INSUFFICIENT_EXACT_OBJECTIVE_ANCHOR_COVERAGE",
        "objective_anchor_count":len(anchors),
        "matched_anchor_count":len(matched),
        "coverage":round(coverage,6),
        "matched_anchors":matched,
        "required_count":required_count,
        "required_coverage":required_coverage,
        "method":"EXACT_NORMALIZED_OBJECTIVE_ANCHOR_COVERAGE_ON_LIVE_DOCUMENT_METADATA",
    }

def verify(objective,candidate,provenance,authority_identity,timeout=15):
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    authority_identity=dict(authority_identity or {})
    base={
        "schema":SCHEMA,
        "status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "relevance_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "primary_source_claim_scope":"EXACT_ROR_BOUND_ORGANIZATION_HOSTED_DOCUMENT_PUBLICATION_PROVENANCE_ONLY",
        "relevance_claim_scope":"EXACT_OBJECTIVE_ANCHOR_COVERAGE_ON_LIVE_DOCUMENT_METADATA_ONLY",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base,"reason":"RETRIEVAL_PROVENANCE_REQUIRED"}
    if authority_identity.get("status")!="AUTHORITY_IDENTITY_VERIFIED":
        return {**base,"reason":"ROR_AUTHORITY_IDENTITY_REQUIRED"}

    final_url=_safe_url(provenance.get("final_url") or candidate.get("final_url") or candidate.get("url"))
    matched_domain=str(authority_identity.get("matched_domain") or "").lower().strip(".")
    if not final_url or not matched_domain:
        return {**base,"reason":"SAFE_FINAL_URL_AND_MATCHED_DOMAIN_REQUIRED"}
    if _host(final_url)!=matched_domain:
        return {
            **base,
            "reason":"FINAL_HOST_DOES_NOT_EQUAL_VERIFIED_ROR_DOMAIN",
            "final_host":_host(final_url),
            "matched_domain":matched_domain,
        }

    try:
        body,ctype,http_status,retrieved_url=_fetch(final_url,timeout)
    except Exception as exc:
        return {
            **base,
            "reason":"LIVE_PRIMARY_RELEVANCE_RETRIEVAL_FAILED",
            "error_class":type(exc).__name__,
        }

    retrieved_url=_safe_url(retrieved_url)
    retrieved_host=_host(retrieved_url)
    if not retrieved_url or retrieved_host!=matched_domain:
        return {
            **base,
            "reason":"LIVE_RETRIEVAL_LEFT_VERIFIED_ROR_DOMAIN",
            "retrieved_host":retrieved_host,
            "matched_domain":matched_domain,
        }

    surface=_document_surface(body,ctype)
    if not surface["surface"]:
        return {
            **base,
            "reason":"NO_LIVE_DOCUMENT_METADATA_SURFACE",
            "retrieved_url":retrieved_url,
            "http_status":http_status,
            "content_type":ctype,
        }

    relevance=_relevance(objective,surface["surface"])
    primary={
        "status":"PRIMARY_SOURCE_VERIFIED",
        "method":"LIVE_EXACT_ROR_DOMAIN_DOCUMENT_RETRIEVAL",
        "matched_domain":matched_domain,
        "organization_name":authority_identity.get("organization_name"),
        "retrieved_url":retrieved_url,
        "http_status":http_status,
        "content_type":ctype,
        "document_title":surface["title"] or None,
        "document_h1":surface["h1"] or None,
        "document_description":surface["description"] or None,
    }

    if relevance["status"]!="OBJECTIVE_RELEVANCE_VERIFIED":
        return {
            **base,
            "status":"PRIMARY_SOURCE_VERIFIED_RELEVANCE_UNRESOLVED",
            "primary_source_status":"VERIFIED",
            "primary_source":primary,
            "relevance":relevance,
        }

    return {
        **base,
        "status":"PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFIED",
        "primary_source_status":"VERIFIED",
        "relevance_status":"VERIFIED",
        "primary_source":primary,
        "relevance":relevance,
        "output_verified":True,
    }
