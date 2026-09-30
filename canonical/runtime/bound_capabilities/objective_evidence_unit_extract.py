#!/usr/bin/env python3
"""Fail-closed extraction of objective-grounded evidence units from a verified relevant first-party page.

Proves only:
- a fresh retrieval stayed on the exact independently-bound organization domain;
- bounded visible text units were extracted from that fresh page;
- each returned unit contains deterministic lexical anchors from the objective;
- every returned normalized unit is bound to the fresh page by hashes and offsets.

Does NOT prove:
- that a unit supports or contradicts any claim;
- semantic entailment, factual correctness, causal direction, evidence quality,
  evidence sufficiency, source independence, or parent-task completion.
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

SCHEMA="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V1"
UA="ProjectBrain-EvidenceUnitExtraction/1.0"
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
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local or
        ip.is_reserved or ip.is_unspecified
    ):
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

class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.stack=[]
        self.blocks=[]
    def handle_starttag(self,tag,attrs):
        low=tag.lower()
        if low in _SUPPRESS:
            self.suppress+=1
        if self.suppress:
            return
        if low in _BLOCK_TAGS:
            self.stack.append([low,[]])
    def handle_endtag(self,tag):
        low=tag.lower()
        if low in _SUPPRESS:
            if self.suppress: self.suppress-=1
            return
        if self.suppress:
            return
        if low in _BLOCK_TAGS and self.stack:
            # Close the nearest matching active block. Nested block text is also
            # retained in its parent; exact-text dedupe later removes duplicates.
            idx=None
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==low:
                    idx=i; break
            if idx is None:
                return
            tag_name,parts=self.stack.pop(idx)
            text=_canon(" ".join(parts))
            if text:
                self.blocks.append((tag_name,text))
    def handle_data(self,data):
        if self.suppress or not self.stack:
            return
        text=_canon(data)
        if not text:
            return
        for item in self.stack:
            item[1].append(text)

def _split_long(text,max_chars=850):
    text=_canon(text)
    if len(text)<=max_chars:
        return [text] if text else []
    sentences=[
        _canon(x) for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text) if _canon(x)
    ]
    if len(sentences)<=1:
        return [text[i:i+max_chars].strip() for i in range(0,len(text),max_chars) if text[i:i+max_chars].strip()]
    out=[]; buf=""
    for sentence in sentences:
        candidate=(buf+" "+sentence).strip() if buf else sentence
        if buf and len(candidate)>max_chars:
            out.append(buf); buf=sentence
        else:
            buf=candidate
    if buf: out.append(buf)
    return out

def _extract_blocks(raw,content_type):
    text=raw.decode("utf-8","replace")
    parser=_Blocks()
    if "html" in str(content_type or "").lower() or "<html" in text[:2000].lower():
        try: parser.feed(text)
        except Exception: pass
        rows=parser.blocks
    else:
        rows=[("text",x) for x in re.split(r"\n\s*\n",text)]
    out=[]; seen=set()
    for tag,value in rows:
        for unit in _split_long(html.unescape(value)):
            unit=_canon(unit)
            if len(unit)<24: continue
            key=unit.lower()
            if key in seen: continue
            seen.add(key)
            out.append((tag,unit))
    return out

def _fetch(url,timeout=20,max_bytes=2_000_000):
    req=urllib.request.Request(
        url,
        headers={
          "User-Agent":UA,
          "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes)
        final=r.geturl()
        ctype=str(r.headers.get("Content-Type") or "")
        status=int(getattr(r,"status",200))
    return raw,final,ctype,status

def extract(objective,candidate,provenance,authority_identity,relevance,timeout=20,max_units=8,fetch=None):
    objective=_canon(objective)
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    authority_identity=dict(authority_identity or {})
    relevance=dict(relevance or {})
    base={
      "schema":SCHEMA,
      "objective":objective or None,
      "status":"UNVERIFIED",
      "evidence_extraction_status":"UNVERIFIED",
      "claim_relation_status":"UNVERIFIED",
      "semantic_entailment_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "source_independence_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "evidence_units":[],
    }
    if not objective:
        return {**base,"reason":"OBJECTIVE_REQUIRED"}
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base,"reason":"LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}
    if authority_identity.get("status")!="AUTHORITY_IDENTITY_VERIFIED":
        return {**base,"reason":"QUALIFIED_AUTHORITY_IDENTITY_REQUIRED"}
    if not (
        relevance.get("status")=="FIRST_PARTY_RELEVANT_SOURCE_VERIFIED"
        and relevance.get("objective_relevance_status")=="VERIFIED"
    ):
        return {**base,"reason":"VERIFIED_OBJECTIVE_RELEVANCE_REQUIRED"}

    bound=_norm_host(authority_identity.get("matched_domain"))
    source_url=_safe_url(relevance.get("fresh_url") or provenance.get("final_url") or candidate.get("url"))
    source_host=_norm_host(source_url)
    if not bound or not source_url or source_host!=bound:
        return {
          **base,"reason":"RELEVANT_SOURCE_NOT_EXACT_BOUND_DOMAIN",
          "bound_domain":bound,"source_host":source_host,
        }

    fetch=fetch or _fetch
    try:
        raw,final_url,ctype,http_status=fetch(source_url,timeout)
    except Exception as exc:
        return {
          **base,"reason":"FRESH_EVIDENCE_FETCH_FAILED",
          "error_class":type(exc).__name__,
        }
    final_safe=_safe_url(final_url)
    final_host=_norm_host(final_safe)
    if not final_safe or final_host!=bound:
        return {
          **base,"reason":"FRESH_EVIDENCE_REDIRECT_OUTSIDE_BOUND_DOMAIN",
          "bound_domain":bound,"fresh_host":final_host,
        }

    blocks=_extract_blocks(raw,ctype)
    anchors=_tokens(objective)
    if len(anchors)<2:
        return {
          **base,"reason":"INSUFFICIENT_DISCRIMINATIVE_OBJECTIVE_TOKENS",
          "objective_tokens":anchors,
        }

    visible="\n".join(text for _,text in blocks)
    rows=[]
    cursor=0
    for block_index,(tag,text) in enumerate(blocks):
        start=visible.find(text,cursor)
        if start<0: start=visible.find(text)
        if start<0: continue
        end=start+len(text)
        cursor=end
        words=set(_tokens(text))
        matched=[t for t in anchors if t in words]
        if len(matched)<2:
            continue
        coverage=len(matched)/len(anchors)
        title_like=tag in {"h1","h2","h3","h4","h5","h6"}
        score=(len(matched)*10)+(coverage*10)+(2 if title_like else 0)
        rows.append({
          "_score":score,
          "block_index":block_index,
          "block_tag":tag,
          "text":text,
          "text_sha256":_sha(text),
          "matched_objective_tokens":matched,
          "objective_token_coverage":round(coverage,6),
          "visible_text_start":start,
          "visible_text_end":end,
        })
    rows.sort(key=lambda x:(-x["_score"],x["block_index"]))
    rows=rows[:max(1,min(int(max_units or 8),12))]
    for row in rows:
        row.pop("_score",None)

    if not rows:
        return {
          **base,
          "reason":"NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS",
          "objective_tokens":anchors,
          "source_url":final_safe,
          "http_status":http_status,
          "content_type":ctype,
          "page_raw_sha256":_sha(raw),
          "visible_text_sha256":_sha(visible),
          "visible_block_count":len(blocks),
        }

    return {
      **base,
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "evidence_extraction_status":"VERIFIED",
      "verification_method":"FRESH_EXACT_BOUND_DOMAIN_VISIBLE_BLOCK_EXTRACTION_WITH_OBJECTIVE_TOKEN_BINDING",
      "source_url":final_safe,
      "bound_domain":bound,
      "http_status":http_status,
      "content_type":ctype,
      "page_raw_sha256":_sha(raw),
      "visible_text_sha256":_sha(visible),
      "visible_text_length":len(visible),
      "visible_block_count":len(blocks),
      "objective_tokens":anchors,
      "evidence_unit_count":len(rows),
      "evidence_units":rows,
      "scope_note":"Evidence units are verbatim normalized visible-text blocks grounded only by deterministic objective-token overlap. Support/contradiction, entailment, correctness, sufficiency, quality, and independence remain unverified.",
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
        data.get("authority_identity"),
        data.get("relevance"),
        timeout=args.get("timeout",20),
        max_units=args.get("max_units",8),
    )
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
    return result
