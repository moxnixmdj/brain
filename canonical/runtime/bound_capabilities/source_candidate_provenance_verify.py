#!/usr/bin/env python3
"""Fail-closed source candidate provenance verification.

Verifies bibliographic identity for DOI candidates through Crossref, or live
retrievability/final URL identity for ordinary web candidates. This module
never upgrades provenance identity into factual authority, primary-source
status, relevance, or evidence sufficiency.
"""
from __future__ import annotations
import html
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_SOURCE_CANDIDATE_PROVENANCE_VERIFICATION_V1"
UA="ProjectBrain-ProvenanceVerifier/1.0 (+zero-cost model-independent research)"

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

def _doi(candidate):
    doi=_canon((candidate or {}).get("doi"))
    if doi:
        return doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    url=_safe_url((candidate or {}).get("url"))
    if not url:
        return ""
    u=urllib.parse.urlsplit(url)
    if (u.hostname or "").lower() in {"doi.org","dx.doi.org"}:
        return urllib.parse.unquote(u.path.lstrip("/"))
    return ""

def _fetch(url,timeout,accept="*/*"):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read(1_000_000)
        return body,str(r.headers.get("Content-Type") or ""),int(getattr(r,"status",200)),r.geturl()

class _Title(HTMLParser):
    def __init__(self):
        super().__init__(); self.on=False; self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="title": self.on=True
    def handle_data(self,data):
        if self.on: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="title": self.on=False

def materialize_retrieval(candidate,bibliographic_verification,timeout=15):
    candidate=dict(candidate or {})
    verification=dict(bibliographic_verification or {})
    base={
        "schema":SCHEMA,
        "authority_status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if verification.get("status")!="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
        return {**base,"status":"UNVERIFIED","reason":"BIBLIOGRAPHIC_PROVENANCE_REQUIRED"}
    url=_safe_url(candidate.get("url"))
    verified_url=_safe_url(verification.get("candidate_url"))
    if not url or url!=verified_url:
        return {**base,"status":"UNVERIFIED","reason":"BIBLIOGRAPHIC_CANDIDATE_IDENTITY_MISMATCH"}
    timeout=max(2,min(int(timeout),30))
    try:
        body,ctype,status,final=_fetch(url,timeout,"text/html,application/xhtml+xml,text/plain,*/*;q=0.4")
        final=_safe_url(final)
        if not final:
            raise ValueError("UNSAFE_FINAL_URL")
        title=None
        if "html" in ctype.lower():
            p=_Title(); p.feed(body.decode("utf-8","replace"))
            title=_canon(html.unescape("".join(p.parts))) or None
        return {
            **base,
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "verification_method":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION",
            "candidate_url":url,
            "final_url":final,
            "final_host":(urllib.parse.urlsplit(final).hostname or "").lower(),
            "http_status":status,
            "content_type":ctype,
            "page_title":title,
            "doi":verification.get("doi"),
            "record_title":verification.get("record_title"),
            "bibliographic_provenance_status":"VERIFIED",
            "bibliographic_verification_method":verification.get("verification_method"),
            "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
        }
    except Exception as exc:
        return {
            **base,
            "status":"UNVERIFIED",
            "reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED",
            "error_class":type(exc).__name__,
            "error":str(exc)[:500],
            "candidate_url":url,
            "doi":verification.get("doi"),
            "record_title":verification.get("record_title"),
            "bibliographic_provenance_status":"VERIFIED",
        }

def verify(candidate,timeout=15):
    candidate=dict(candidate or {})
    url=_safe_url(candidate.get("url"))
    if not url:
        return {
            "schema":SCHEMA,"status":"UNVERIFIED","reason":"SAFE_HTTP_URL_REQUIRED",
            "authority_status":"UNVERIFIED","primary_source_status":"UNVERIFIED",
            "model_dependency_count":0,"incremental_spend_usd":0,
        }
    timeout=max(2,min(int(timeout),30))
    doi=_doi(candidate)
    if doi:
        endpoint="https://api.crossref.org/works/"+urllib.parse.quote(doi,safe="")
        try:
            body,ctype,status,final=_fetch(endpoint,timeout,"application/json")
            data=json.loads(body.decode("utf-8","replace"))
            msg=(data or {}).get("message") or {}
            observed=_canon(msg.get("DOI"))
            if observed.lower()!=doi.lower():
                raise ValueError("CROSSREF_DOI_IDENTITY_MISMATCH")
            titles=msg.get("title") or []
            return {
                "schema":SCHEMA,
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "verification_method":"CROSSREF_DOI_RECORD",
                "candidate_url":url,
                "doi":observed,
                "record_title":_canon(titles[0] if titles else "") or None,
                "publisher":_canon(msg.get("publisher")) or None,
                "work_type":msg.get("type"),
                "record_url":_safe_url(msg.get("URL")),
                "verification_endpoint":"https://api.crossref.org/works/{doi}",
                "http_status":status,
                "content_type":ctype,
                "authority_status":"PROVENANCE_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
                "primary_source_status":"UNVERIFIED",
                "evidence_sufficiency_status":"UNVERIFIED",
                "model_dependency_count":0,
                "incremental_spend_usd":0,
            }
        except Exception as exc:
            return {
                "schema":SCHEMA,"status":"UNVERIFIED",
                "reason":"BIBLIOGRAPHIC_PROVENANCE_VERIFICATION_FAILED",
                "error_class":type(exc).__name__,"error":str(exc)[:500],
                "candidate_url":url,"doi":doi,
                "authority_status":"UNVERIFIED","primary_source_status":"UNVERIFIED",
                "model_dependency_count":0,"incremental_spend_usd":0,
            }
    try:
        body,ctype,status,final=_fetch(url,timeout,"text/html,application/xhtml+xml,*/*;q=0.5")
        final=_safe_url(final)
        if not final:
            raise ValueError("UNSAFE_FINAL_URL")
        title=None
        if "html" in ctype.lower():
            p=_Title(); p.feed(body.decode("utf-8","replace"))
            title=_canon(html.unescape("".join(p.parts))) or None
        return {
            "schema":SCHEMA,
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "verification_method":"LIVE_HTTP_RETRIEVAL",
            "candidate_url":url,
            "final_url":final,
            "final_host":(urllib.parse.urlsplit(final).hostname or "").lower(),
            "http_status":status,
            "content_type":ctype,
            "page_title":title,
            "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
            "primary_source_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"UNVERIFIED",
            "reason":"LIVE_RETRIEVAL_FAILED",
            "error_class":type(exc).__name__,"error":str(exc)[:500],
            "candidate_url":url,
            "authority_status":"UNVERIFIED","primary_source_status":"UNVERIFIED",
            "model_dependency_count":0,"incremental_spend_usd":0,
        }
