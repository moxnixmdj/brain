#!/usr/bin/env python3
"""Extract provenance-bound objective-anchored evidence from a fresh source page.

The extractor preserves the existing PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_
EXTRACTION_V1 artifact contract while deleting organization authority as a
universal admission gate.

Verified scope:
- qualified live retrieval provenance is required;
- one fresh fetch must remain on the same normalized provenance host;
- the exact fresh bytes must pass strict bounded lexical objective relevance;
- emitted records are normalized verbatim passages from those same bytes with
  deterministic text/page hashes, source URL, objective anchors, and numeric
  literals.

Not verified: publisher authority, original/primary-source status, claim support,
semantic entailment, factual correctness, causality, evidence quality or
sufficiency, source independence, or parent completion.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"
UA="ProjectBrain-RelevantEvidenceExtract/2.0"
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
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.title=[]
        self.skip=0
        self.in_title=False
    def handle_starttag(self,tag,attrs):
        low=tag.lower()
        if low in {"script","style","noscript","svg","nav","footer","header","form"}:
            self.skip+=1
        if low=="title" and not self.skip:
            self.in_title=True
    def handle_endtag(self,tag):
        low=tag.lower()
        if low=="title":
            self.in_title=False
        if low in {"script","style","noscript","svg","nav","footer","header","form"} and self.skip:
            self.skip-=1
    def handle_data(self,data):
        if self.skip:
            return
        text=_canon(data)
        if not text:
            return
        self.parts.append(text)
        if self.in_title:
            self.title.append(text)

def _canon(text):
    return " ".join(str(text or "").split())

def _norm_host(raw):
    text=str(raw or "").strip()
    if not text:
        return None
    try:
        host=(urllib.parse.urlsplit(text).hostname or "") if "://" in text else text
    except Exception:
        return None
    host=host.lower().strip(".")
    if host.startswith("www."):
        host=host[4:]
    if not host or "." not in host or host.endswith((".local",".internal")):
        return None
    try:
        ip=ipaddress.ip_address(host)
    except ValueError:
        ip=None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_unspecified
    ):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+",host):
        return None
    return host

def _safe_url(raw):
    try:
        u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in {"http","https"} or not u.hostname or not _norm_host(u.hostname):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path or "/",u.query,""))

def _objective_tokens(text):
    out=[]
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()):
        t=raw.strip("._+-")
        if len(t)<4 or t in _STOP or t in _GENERIC:
            continue
        if t not in out:
            out.append(t)
    return out

def _wordset(text):
    return set(re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()))

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
                if len(chunk)>=35:
                    out.append(chunk)
    return out

def _numbers(text):
    vals=re.findall(
      r"(?<![A-Za-z0-9])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?(?:\s*%|\s*[A-Za-zµμ°/][A-Za-z0-9µμ°/^*.-]{0,15})?",
      str(text or "")
    )
    out=[]
    for value in vals:
        value=_canon(value)
        if value and value not in out:
            out.append(value)
    return out[:24]

def _fetch(url,timeout=20,max_bytes=1_500_000):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":UA,
            "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes+1)
        final=r.geturl()
        ctype=str(r.headers.get("Content-Type") or "")
        status=int(getattr(r,"status",200))
    if len(raw)>max_bytes:
        raise ValueError("SOURCE_BODY_EXCEEDS_MAX_BYTES")
    return raw,final,ctype,status

def _visible(raw,ctype):
    decoded=raw.decode("utf-8","replace")
    if "html" in str(ctype).lower() or "<html" in decoded[:1000].lower():
        parser=_Visible()
        try:
            parser.feed(decoded)
            parser.close()
        except Exception:
            pass
        return html.unescape(" ".join(parser.parts)),_canon(" ".join(parser.title))
    if "text/plain" in str(ctype).lower() or (not ctype and "<" not in decoded[:1000]):
        return decoded,""
    return None,None

def extract(objective,candidate,provenance,authority_identity=None,timeout=20,fetch=None,max_passages=10):
    objective=_canon(objective)
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    base={
      "schema":SCHEMA,
      "claim_scope":"VERBATIM_OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATES_FROM_THE_SAME_FRESH_PAGE_BYTES",
      "authority_identity_status":"OPTIONAL_NOT_REQUIRED",
      "primary_source_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "claim_support_status":"UNVERIFIED",
      "evidence_quality_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "semantic_entailment_status":"UNVERIFIED",
      "causality_status":"UNVERIFIED",
      "source_independence_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "evidence_records":[],
    }
    if not objective:
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"OBJECTIVE_REQUIRED"}
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}

    source_url=_safe_url(
        provenance.get("final_url")
        or candidate.get("final_url")
        or candidate.get("url")
    )
    provenance_host=_norm_host(provenance.get("final_host") or source_url)
    source_host=_norm_host(source_url)
    if not source_url or not provenance_host or source_host!=provenance_host:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"PROVENANCE_SOURCE_URL_HOST_MISMATCH",
          "provenance_host":provenance_host,"source_host":source_host,
        }

    fetch=fetch or _fetch
    try:
        raw,observed_url,ctype,http_status=fetch(source_url,timeout)
    except Exception as exc:
        return {
          **base,"status":"EXTRACTION_BLOCKED","reason":"FRESH_SOURCE_FETCH_FAILED",
          "error_class":type(exc).__name__,
        }
    try:
        raw=bytes(raw)
    except Exception:
        return {**base,"status":"EXTRACTION_BLOCKED","reason":"FRESH_SOURCE_BYTES_INVALID"}

    observed_safe=_safe_url(observed_url)
    observed_host=_norm_host(observed_safe)
    if not observed_safe or observed_host!=provenance_host:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"FRESH_SOURCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",
          "provenance_host":provenance_host,"fresh_host":observed_host,
        }

    visible,title=_visible(raw,ctype)
    if visible is None:
        return {
          **base,"status":"EXTRACTION_BLOCKED","reason":"UNSUPPORTED_CONTENT_TYPE",
          "fresh_url":observed_safe,"content_type":ctype,
          "page_sha256":hashlib.sha256(raw).hexdigest(),
        }
    visible=_canon(visible)
    if not visible:
        return {
          **base,"status":"EXTRACTION_BLOCKED","reason":"NO_VISIBLE_SOURCE_TEXT",
          "fresh_url":observed_safe,"page_sha256":hashlib.sha256(raw).hexdigest(),
        }

    objective_tokens=_objective_tokens(objective)
    if len(objective_tokens)<2:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"INSUFFICIENT_DISCRIMINATIVE_OBJECTIVE_TOKENS",
          "objective_tokens":objective_tokens,
        }

    page_words=_wordset(title+" "+visible)
    title_or_url_words=_wordset(title+" "+observed_safe)
    matched=[t for t in objective_tokens if t in page_words]
    matched_title_or_url=[t for t in objective_tokens if t in title_or_url_words]
    long_matches=[t for t in matched if len(t)>=7 or any(ch.isdigit() for ch in t)]
    required=max(2,(len(objective_tokens)+1)//2)
    coverage=len(matched)/len(objective_tokens)
    relevance=bool(
        len(matched)>=required
        and coverage>=0.5
        and (bool(matched_title_or_url) or len(long_matches)>=2)
    )
    rel={
      "status":"PROVENANCE_RELEVANT_SOURCE_VERIFIED" if relevance else "UNVERIFIED",
      "objective_relevance_status":"VERIFIED" if relevance else "UNVERIFIED",
      "verification_method":"FRESH_SAME_PROVENANCE_HOST_PLUS_STRICT_BOUNDED_LEXICAL_OBJECTIVE_COVERAGE",
      "provenance_host":provenance_host,
      "fresh_url":observed_safe,
      "page_title":title or None,
      "objective_tokens":objective_tokens,
      "matched_body_tokens":matched,
      "matched_title_or_url_tokens":matched_title_or_url,
      "matched_token_coverage":round(coverage,6),
      "required_match_count":required,
      "authority_identity_required":False,
      "primary_source_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
    }
    base["relevance_verification"]=rel
    if not relevance:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"VERIFIED_RELEVANT_SOURCE_REQUIRED",
          "fresh_url":observed_safe,
          "page_sha256":hashlib.sha256(raw).hexdigest(),
          "visible_text_sha256":hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        }

    rows=[]
    for ordinal,passage in enumerate(_sentences(visible)):
        wordset=_wordset(passage)
        unit_matches=[t for t in objective_tokens if t in wordset]
        if not unit_matches:
            continue
        nums=_numbers(passage)
        start=visible.find(passage)
        rows.append({
          "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
          "ordinal":ordinal,
          "text":passage,
          "text_sha256":hashlib.sha256(passage.encode("utf-8")).hexdigest(),
          "matched_objective_tokens":unit_matches,
          "matched_objective_token_count":len(unit_matches),
          "objective_token_coverage":round(len(unit_matches)/len(objective_tokens),6),
          "numeric_literals":nums,
          "numeric_literal_count":len(nums),
          "source_url":observed_safe,
          "visible_text_start":start if start>=0 else None,
          "visible_text_end":(start+len(passage)) if start>=0 else None,
        })
    rows.sort(key=lambda x:(-x["matched_objective_token_count"],-x["numeric_literal_count"],x["ordinal"]))
    rows=rows[:max(1,min(int(max_passages),20))]
    if not rows:
        return {
          **base,"status":"EXTRACTION_BLOCKED",
          "reason":"NO_OBJECTIVE_ANCHORED_PASSAGES_AFTER_VERIFIED_RELEVANCE",
          "fresh_url":observed_safe,
          "page_sha256":hashlib.sha256(raw).hexdigest(),
          "visible_text_sha256":hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        }

    return {
      **base,
      "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
      "fresh_url":observed_safe,
      "provenance_host":provenance_host,
      "http_status":http_status,
      "content_type":ctype,
      "page_sha256":hashlib.sha256(raw).hexdigest(),
      "visible_text_sha256":hashlib.sha256(visible.encode("utf-8")).hexdigest(),
      "evidence_record_count":len(rows),
      "evidence_records":rows,
      "output_verified":True,
    }
