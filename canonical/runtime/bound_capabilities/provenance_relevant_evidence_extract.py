#!/usr/bin/env python3
"""Fail-closed provenance-bound relevance verification and evidence-unit extraction.

This capability proves only that:
1) a fresh retrieval remains on the same host already established by qualified
   live retrieval provenance;
2) the fresh page has strict bounded lexical relevance to the objective; and
3) returned evidence units are normalized visible-text blocks from those exact
   fresh bytes, with deterministic hashes and offsets.

Organization authority is optional metadata and is NOT an admission gate.
Support/contradiction, semantic entailment, factual correctness, causal
direction, evidence quality/sufficiency, source independence, and parent
completion remain unverified.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import pathlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_PROVENANCE_RELEVANT_EVIDENCE_EXTRACTION_V1"
UA="ProjectBrain-ProvenanceRelevantEvidence/1.0"
_BLOCK_TAGS={"h1","h2","h3","h4","h5","h6","p","li","dt","dd","blockquote","td","th"}
_SUPPRESS={"script","style","noscript","svg","nav","footer","header","form"}
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

def _canon(value):
    return " ".join(str(value or "").split())

def _sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

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
    if u.scheme not in {"http","https"} or not u.hostname:
        return None
    if not _norm_host(u.hostname):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path or "/",u.query,""))

def _tokens(text):
    out=[]
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()):
        t=raw.strip("._+-")
        if len(t)<4 or t in _STOP or t in _GENERIC:
            continue
        if t not in out:
            out.append(t)
    return out

class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.stack=[]
        self.blocks=[]
        self.title=[]
        self.in_title=False
    def handle_starttag(self,tag,attrs):
        low=tag.lower()
        if low in _SUPPRESS:
            self.suppress+=1
        if low=="title" and not self.suppress:
            self.in_title=True
        if self.suppress:
            return
        if low in _BLOCK_TAGS:
            self.stack.append([low,[]])
    def handle_endtag(self,tag):
        low=tag.lower()
        if low=="title":
            self.in_title=False
        if low in _SUPPRESS:
            if self.suppress:
                self.suppress-=1
            return
        if self.suppress:
            return
        if low in _BLOCK_TAGS and self.stack:
            idx=None
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==low:
                    idx=i
                    break
            if idx is None:
                return
            tag_name,parts=self.stack.pop(idx)
            text=_canon(" ".join(parts))
            if text:
                self.blocks.append((tag_name,text))
    def handle_data(self,data):
        if self.suppress:
            return
        text=_canon(data)
        if not text:
            return
        if self.in_title:
            self.title.append(text)
        for item in self.stack:
            item[1].append(text)

def _split_long(text,max_chars=850):
    text=_canon(text)
    if not text:
        return []
    if len(text)<=max_chars:
        return [text]
    sentences=[
        _canon(x) for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text)
        if _canon(x)
    ]
    if len(sentences)<=1:
        return [
            text[i:i+max_chars].strip()
            for i in range(0,len(text),max_chars)
            if text[i:i+max_chars].strip()
        ]
    out=[]
    buf=""
    for sentence in sentences:
        candidate=(buf+" "+sentence).strip() if buf else sentence
        if buf and len(candidate)>max_chars:
            out.append(buf)
            buf=sentence
        else:
            buf=candidate
    if buf:
        out.append(buf)
    return out

def _extract_blocks(raw,content_type):
    ctype=str(content_type or "").lower()
    decoded=raw.decode("utf-8","replace")
    if "html" in ctype or "<html" in decoded[:2000].lower():
        parser=_Blocks()
        try:
            parser.feed(decoded)
            parser.close()
        except Exception:
            pass
        rows=parser.blocks
        title=_canon(" ".join(parser.title))
    elif "text/plain" in ctype or (not ctype and "<" not in decoded[:1000]):
        rows=[("text",x) for x in re.split(r"\n\s*\n",decoded)]
        title=""
    else:
        return [],"","UNSUPPORTED_CONTENT_TYPE"

    out=[]
    seen=set()
    for tag,value in rows:
        for unit in _split_long(html.unescape(value)):
            unit=_canon(unit)
            if len(unit)<24:
                continue
            key=unit.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((tag,unit))
    return out,title,None

def _fetch(url,timeout=20,max_bytes=2_000_000):
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

def extract(objective,candidate,provenance,timeout=20,max_units=8,fetch=None):
    objective=_canon(objective)
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    base={
      "schema":SCHEMA,
      "objective":objective or None,
      "status":"UNVERIFIED",
      "retrieval_provenance_status":"UNVERIFIED",
      "objective_relevance_status":"UNVERIFIED",
      "evidence_extraction_status":"UNVERIFIED",
      "claim_relation_status":"UNVERIFIED",
      "semantic_entailment_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "causal_direction_status":"UNVERIFIED",
      "evidence_quality_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "source_independence_status":"UNVERIFIED",
      "authority_identity_status":"OPTIONAL_NOT_REQUIRED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "evidence_units":[],
    }
    if not objective:
        return {**base,"reason":"OBJECTIVE_REQUIRED"}
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base,"reason":"LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}

    source_url=_safe_url(
        provenance.get("final_url")
        or candidate.get("final_url")
        or candidate.get("url")
    )
    provenance_host=_norm_host(provenance.get("final_host") or source_url)
    source_host=_norm_host(source_url)
    if not source_url or not provenance_host or source_host!=provenance_host:
        return {
          **base,
          "reason":"PROVENANCE_SOURCE_URL_HOST_MISMATCH",
          "provenance_host":provenance_host,
          "source_host":source_host,
        }

    fetch=fetch or _fetch
    try:
        raw,final_url,ctype,http_status=fetch(source_url,timeout)
    except Exception as exc:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT",
          "reason":"FRESH_SOURCE_FETCH_FAILED",
          "error_class":type(exc).__name__,
          "error_message":str(exc)[:240],
        }

    try:
        raw=bytes(raw)
    except Exception:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT",
          "reason":"FRESH_SOURCE_BYTES_INVALID",
        }
    final_safe=_safe_url(final_url)
    fresh_host=_norm_host(final_safe)
    if not final_safe or fresh_host!=provenance_host:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT",
          "reason":"FRESH_SOURCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",
          "provenance_host":provenance_host,
          "fresh_host":fresh_host,
        }

    blocks,title,parse_error=_extract_blocks(raw,ctype)
    if parse_error:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
          "reason":parse_error,
          "source_url":final_safe,
          "content_type":ctype,
          "page_raw_sha256":_sha(raw),
        }
    if not blocks:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
          "reason":"NO_VISIBLE_TEXT_BLOCKS",
          "source_url":final_safe,
          "content_type":ctype,
          "page_raw_sha256":_sha(raw),
        }

    anchors=_tokens(objective)
    if len(anchors)<2:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
          "reason":"INSUFFICIENT_DISCRIMINATIVE_OBJECTIVE_TOKENS",
          "objective_tokens":anchors,
        }

    visible="\n".join(text for _,text in blocks)
    page_words=set(_tokens((title+" "+visible).strip()))
    url_words=set(_tokens(final_safe))
    title_words=set(_tokens(title))
    page_matches=[t for t in anchors if t in page_words]
    title_or_url_matches=[t for t in anchors if t in title_words or t in url_words]
    long_matches=[t for t in page_matches if len(t)>=7 or any(ch.isdigit() for ch in t)]
    required=max(2,(len(anchors)+1)//2)
    coverage=len(page_matches)/len(anchors)
    relevant=bool(
        len(page_matches)>=required
        and coverage>=0.5
        and (bool(title_or_url_matches) or len(long_matches)>=2)
    )
    relevance_receipt={
      "status":"PROVENANCE_RELEVANT_SOURCE_VERIFIED" if relevant else "UNVERIFIED",
      "verification_method":"FRESH_SAME_PROVENANCE_HOST_PLUS_STRICT_BOUNDED_LEXICAL_OBJECTIVE_COVERAGE",
      "source_url":final_safe,
      "provenance_host":provenance_host,
      "page_title":title or None,
      "objective_tokens":anchors,
      "matched_page_tokens":page_matches,
      "matched_title_or_url_tokens":title_or_url_matches,
      "matched_token_coverage":round(coverage,6),
      "required_match_count":required,
      "authority_identity_required":False,
      "primary_source_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
    }
    if not relevant:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
          "reason":"FRESH_PAGE_OBJECTIVE_RELEVANCE_UNVERIFIED",
          "source_url":final_safe,
          "http_status":http_status,
          "content_type":ctype,
          "page_raw_sha256":_sha(raw),
          "visible_text_sha256":_sha(visible),
          "visible_block_count":len(blocks),
          "relevance_verification":relevance_receipt,
        }

    min_unit_matches=1 if len(anchors)==2 else 2
    rows=[]
    cursor=0
    for block_index,(tag,text) in enumerate(blocks):
        start=visible.find(text,cursor)
        if start<0:
            start=visible.find(text)
        if start<0:
            continue
        end=start+len(text)
        cursor=end
        words=set(_tokens(text))
        matched=[t for t in anchors if t in words]
        if len(matched)<min_unit_matches:
            continue
        unit_coverage=len(matched)/len(anchors)
        title_like=tag in {"h1","h2","h3","h4","h5","h6"}
        score=(len(matched)*10)+(unit_coverage*10)+(2 if title_like else 0)
        rows.append({
          "_score":score,
          "block_index":block_index,
          "block_tag":tag,
          "text":text,
          "text_sha256":_sha(text),
          "matched_objective_tokens":matched,
          "matched_objective_token_count":len(matched),
          "objective_token_coverage":round(unit_coverage,6),
          "visible_text_start":start,
          "visible_text_end":end,
          "source_url":final_safe,
        })
    rows.sort(key=lambda x:(-x["_score"],x["block_index"]))
    rows=rows[:max(1,min(int(max_units or 8),12))]
    for row in rows:
        row.pop("_score",None)

    if not rows:
        return {
          **base,
          "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
          "objective_relevance_status":"VERIFIED",
          "reason":"NO_OBJECTIVE_GROUNDED_VISIBLE_TEXT_UNITS",
          "source_url":final_safe,
          "http_status":http_status,
          "content_type":ctype,
          "page_raw_sha256":_sha(raw),
          "visible_text_sha256":_sha(visible),
          "visible_block_count":len(blocks),
          "relevance_verification":relevance_receipt,
        }

    return {
      **base,
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "retrieval_provenance_status":"VERIFIED_INPUT_AND_FRESH_SAME_HOST",
      "objective_relevance_status":"VERIFIED",
      "evidence_extraction_status":"VERIFIED",
      "verification_method":"FRESH_SAME_PROVENANCE_HOST_RELEVANCE_PLUS_VISIBLE_BLOCK_HASH_OFFSETS",
      "claim_scope":"NORMALIZED_VISIBLE_TEXT_UNITS_WITH_OBJECTIVE_LEXICAL_BINDING_AND_HASHED_PROVENANCE_ONLY",
      "source_url":final_safe,
      "provenance_host":provenance_host,
      "http_status":http_status,
      "content_type":ctype,
      "page_raw_sha256":_sha(raw),
      "visible_text_sha256":_sha(visible),
      "visible_text_length":len(visible),
      "visible_block_count":len(blocks),
      "relevance_verification":relevance_receipt,
      "evidence_unit_count":len(rows),
      "evidence_units":rows,
      "scope_note":"Units are normalized visible source text selected by deterministic lexical objective overlap. Relation, entailment, correctness, causality, quality, sufficiency, authority, independence, and parent completion remain unverified.",
      "output_verified":True,
    }

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    args=dict(args or {})
    inp=_safe_path(root,args.get("input_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise ValueError("EVIDENCE_EXTRACTION_INPUT_MISSING")
    data=json.loads(inp.read_text(encoding="utf-8"))
    result=extract(
        data.get("objective"),
        data.get("candidate"),
        data.get("provenance"),
        timeout=args.get("timeout",20),
        max_units=args.get("max_units",8),
    )
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
    return result
