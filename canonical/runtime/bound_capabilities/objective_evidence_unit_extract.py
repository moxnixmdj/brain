#!/usr/bin/env python3
"""Fail-closed extraction of objective-grounded evidence units from a verified relevant source.

Proves only:
- the input carries verified retrieval provenance and verified objective relevance;
- relevance and provenance identify the same source URL;
- a fresh retrieval remains on the provenance-verified host;
- bounded normalized visible-text units come from that fresh page;
- each returned unit contains deterministic lexical anchors from the objective;
- every returned unit is bound to the fresh page by hashes and offsets.

Authority/organization identity may exist upstream as metadata, but it is not an
admission prerequisite here.

Does NOT prove support/contradiction, semantic entailment, factual correctness,
causal direction, evidence quality, evidence sufficiency, source independence,
or parent-task completion.
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

SCHEMA="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2"
UA="ProjectBrain-EvidenceUnitExtraction/2.0"
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

def _receipt_sha(value):
    raw=json.dumps(value or {},sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return _sha(raw)

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
    if u.scheme not in {"http","https"} or not u.hostname:
        return None
    if not _norm_host(u.hostname):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path or "/",u.query,""))

def _tokens(text):
    out=[]
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{2,}",str(text or "").lower()):
        token=raw.strip("._+-")
        if len(token)<4 or token in _STOP or token in _GENERIC:
            continue
        if token not in out:
            out.append(token)
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
            if self.suppress:
                self.suppress-=1
            return
        if self.suppress or low not in _BLOCK_TAGS or not self.stack:
            return
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
        _canon(x)
        for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text)
        if _canon(x)
    ]
    if len(sentences)<=1:
        return [
            text[i:i+max_chars].strip()
            for i in range(0,len(text),max_chars)
            if text[i:i+max_chars].strip()
        ]
    out=[]; buf=""
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
    text=raw.decode("utf-8","replace")
    parser=_Blocks()
    if "html" in str(content_type or "").lower() or "<html" in text[:2000].lower():
        try:
            parser.feed(text)
        except Exception:
            pass
        rows=parser.blocks
    else:
        rows=[("text",x) for x in re.split(r"\n\s*\n",text)]
    out=[]; seen=set()
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
    return out

def _fetch(url,timeout=20,max_bytes=2_000_000):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":UA,
            "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as response:
        raw=response.read(max_bytes)
        final=response.geturl()
        ctype=str(response.headers.get("Content-Type") or "")
        status=int(getattr(response,"status",200))
    return raw,final,ctype,status

def extract(objective,candidate,provenance,relevance,timeout=20,max_units=8,fetch=None):
    objective=_canon(objective)
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
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
    if not (
        relevance.get("objective_relevance_status")=="VERIFIED"
        and relevance.get("status")=="FIRST_PARTY_RELEVANT_SOURCE_VERIFIED"
    ):
        return {**base,"reason":"QUALIFIED_OBJECTIVE_RELEVANCE_RECEIPT_REQUIRED"}

    provenance_url=_safe_url(provenance.get("final_url") or candidate.get("url"))
    relevance_url=_safe_url(relevance.get("fresh_url"))
    if not provenance_url or not relevance_url:
        return {
            **base,
            "reason":"QUALIFIED_SOURCE_URL_REQUIRED",
            "provenance_url":provenance_url,
            "relevance_url":relevance_url,
        }
    if provenance_url!=relevance_url:
        return {
            **base,
            "reason":"RELEVANCE_PROVENANCE_SOURCE_MISMATCH",
            "provenance_url":provenance_url,
            "relevance_url":relevance_url,
        }

    provenance_host=_norm_host(provenance.get("final_host") or provenance_url)
    if not provenance_host or _norm_host(provenance_url)!=provenance_host:
        return {
            **base,
            "reason":"PROVENANCE_FINAL_HOST_MISMATCH",
            "provenance_url":provenance_url,
            "provenance_host":provenance_host,
        }

    fetch=fetch or _fetch
    try:
        raw,final_url,ctype,http_status=fetch(provenance_url,timeout)
    except Exception as exc:
        return {
            **base,
            "reason":"FRESH_EVIDENCE_FETCH_FAILED",
            "error_class":type(exc).__name__,
        }

    final_safe=_safe_url(final_url)
    fresh_host=_norm_host(final_safe)
    if not final_safe or fresh_host!=provenance_host:
        return {
            **base,
            "reason":"FRESH_EVIDENCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",
            "provenance_host":provenance_host,
            "fresh_host":fresh_host,
        }

    blocks=_extract_blocks(raw,ctype)
    anchors=_tokens(objective)
    if len(anchors)<2:
        return {
            **base,
            "reason":"INSUFFICIENT_DISCRIMINATIVE_OBJECTIVE_TOKENS",
            "objective_tokens":anchors,
        }

    visible="\n".join(text for _,text in blocks)
    visible_tokens=set(_tokens(visible))
    page_matches=[token for token in anchors if token in visible_tokens]
    page_coverage=(len(page_matches)/len(anchors)) if anchors else 0.0
    required_page_matches=max(2,(len(anchors)+1)//2)
    if len(page_matches)<required_page_matches or page_coverage<0.5:
        return {
            **base,
            "reason":"FRESH_PAGE_OBJECTIVE_RELEVANCE_DRIFT",
            "objective_tokens":anchors,
            "fresh_page_matched_objective_tokens":page_matches,
            "fresh_page_objective_token_coverage":round(page_coverage,6),
            "required_page_match_count":required_page_matches,
            "source_url":final_safe,
            "http_status":http_status,
            "content_type":ctype,
            "page_raw_sha256":_sha(raw),
            "visible_text_sha256":_sha(visible),
            "visible_block_count":len(blocks),
            "provenance_receipt_sha256":_receipt_sha(provenance),
            "relevance_receipt_sha256":_receipt_sha(relevance),
        }

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
        matched=[token for token in anchors if token in words]
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

    rows.sort(key=lambda row:(-row["_score"],row["block_index"]))
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
            "provenance_receipt_sha256":_receipt_sha(provenance),
            "relevance_receipt_sha256":_receipt_sha(relevance),
        }

    return {
        **base,
        "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
        "evidence_extraction_status":"VERIFIED",
        "verification_method":"FRESH_SAME_SOURCE_VISIBLE_BLOCK_EXTRACTION_WITH_OBJECTIVE_TOKEN_BINDING",
        "source_url":final_safe,
        "provenance_host":provenance_host,
        "relevance_bound_domain_metadata":relevance.get("bound_domain"),
        "relevance_verification_method":relevance.get("verification_method"),
        "http_status":http_status,
        "content_type":ctype,
        "page_raw_sha256":_sha(raw),
        "visible_text_sha256":_sha(visible),
        "visible_text_length":len(visible),
        "visible_block_count":len(blocks),
        "objective_tokens":anchors,
        "fresh_page_matched_objective_tokens":page_matches,
        "fresh_page_objective_token_coverage":round(page_coverage,6),
        "required_page_match_count":required_page_matches,
        "provenance_receipt_sha256":_receipt_sha(provenance),
        "relevance_receipt_sha256":_receipt_sha(relevance),
        "evidence_unit_count":len(rows),
        "evidence_units":rows,
        "scope_note":"Evidence units are verbatim normalized visible-text blocks grounded only by deterministic objective-token overlap on a fresh retrieval of the same provenance/relevance source. Authority identity is optional metadata. Support/contradiction, entailment, correctness, sufficiency, quality, and independence remain unverified.",
        "output_verified":True,
    }

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    path=(root/str(raw or "")).resolve()
    if path==root or root not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path

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
        data.get("relevance"),
        timeout=args.get("timeout",20),
        max_units=args.get("max_units",8),
    )
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
    return result
