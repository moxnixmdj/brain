#!/usr/bin/env python3
from __future__ import annotations

import json, re, urllib.parse
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_HLE_TOOLS_POLICY_KERNEL_V1"
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_POLICY=ROOT/"canonical/governance/HLE_TOOLS_OFFICIAL_BLOCKLIST_20261003.json"
MAX_SEARCH_RESULTS=20
MAX_FETCH_CHARS=60000

class HLEPolicyBlocked(RuntimeError):
    def __init__(self, code:str, *, rule_type:str|None=None, rule:str|None=None):
        self.code=code; self.rule_type=rule_type; self.rule=rule
        super().__init__(code + (f":{rule_type}:{rule}" if rule_type or rule else ""))

def load_policy(path:Path|str=DEFAULT_POLICY)->dict[str,Any]:
    x=json.loads(Path(path).read_text(encoding="utf-8"))
    required={"domains","url_prefixes","serp_url_patterns","url_patterns",
              "patterns_case_sensitive","answer_title_patterns","answer_title_allow_hosts"}
    if not isinstance(x,dict) or not required.issubset(x):
        raise ValueError("HLE_BLOCKLIST_SCHEMA_INVALID")
    for k in required:
        if not isinstance(x[k],list) or any(not isinstance(v,str) for v in x[k]):
            raise ValueError("HLE_BLOCKLIST_FIELD_INVALID:"+k)
    return x

def _host(raw:str)->str:
    try: return (urllib.parse.urlsplit(str(raw or "")).hostname or "").lower().strip(".")
    except Exception: return ""

def _domain_matches(host:str, blocked:str)->bool:
    b=blocked.lower().strip(".")
    return bool(host and b and (host==b or host.endswith("."+b)))

def _url_surface(raw:str)->str:
    s=str(raw or "").strip()
    try:
        u=urllib.parse.urlsplit(s)
        if u.scheme:
            s=urllib.parse.urlunsplit(("",u.netloc,u.path,u.query,u.fragment)).lstrip("/")
    except Exception:
        pass
    s=re.sub(r"^www\.","",s,flags=re.I)
    return s

def _decoded_variants(raw:str, rounds:int=4)->list[str]:
    out=[]; cur=str(raw or "")
    for _ in range(max(1,rounds)):
        if cur not in out: out.append(cur)
        nxt=urllib.parse.unquote(cur)
        if nxt==cur: break
        cur=nxt
    return out

def _regex_hit(patterns:Iterable[str], text:str, flags:int=0)->str|None:
    for p in patterns:
        try:
            if re.search(p,text,flags): return p
        except re.error as exc:
            raise ValueError("INVALID_BLOCKLIST_REGEX:"+p) from exc
    return None

def _url_rule(url:str, policy:Mapping[str,Any])->tuple[str,str]|None:
    for variant in _decoded_variants(url):
        h=_host(variant)
        for d in policy["domains"]:
            if _domain_matches(h,d): return ("domains",d)
        surface=_url_surface(variant)
        low=surface.lower()
        for p in policy["url_prefixes"]:
            if low.startswith(_url_surface(p).lower()): return ("url_prefixes",p)
        hit=_regex_hit(policy["serp_url_patterns"],surface,re.I)
        if hit: return ("serp_url_patterns",hit)
        hit=_regex_hit(policy["url_patterns"],variant,re.I)
        if hit: return ("url_patterns",hit)
        hit=_regex_hit(policy["patterns_case_sensitive"],variant,0)
        if hit: return ("patterns_case_sensitive",hit)
    return None

def _text_rule(text:str, policy:Mapping[str,Any])->tuple[str,str]|None:
    hit=_regex_hit(policy["url_patterns"],str(text or ""),re.I)
    if hit: return ("url_patterns",hit)
    hit=_regex_hit(policy["patterns_case_sensitive"],str(text or ""),0)
    if hit: return ("patterns_case_sensitive",hit)
    return None

def _title_variants(title:str)->list[str]:
    # Public docs require checking titles after stripping trailing site names but
    # do not publish the exact stripper. Generate conservative common variants.
    raw=" ".join(str(title or "").split())
    out=[raw]
    for sep in (" | "," - "," — "," – "," · "," :: "):
        if sep in raw:
            parts=raw.split(sep)
            for n in range(len(parts)-1,0,-1):
                v=sep.join(parts[:n]).strip()
                if v and v not in out: out.append(v)
    return out

def _answer_title_rule(title:str,host:str,policy:Mapping[str,Any])->tuple[str,str]|None:
    if any(_domain_matches(host,x) for x in policy["answer_title_allow_hosts"]):
        return None
    for v in _title_variants(title):
        hit=_regex_hit(policy["answer_title_patterns"],v,re.I)
        if hit: return ("answer_title_patterns",hit)
    return None

def _site_domains(query:str)->list[str]:
    vals=[]
    for m in re.finditer(r"(?i)(?:^|\s)site:([^\s]+)",str(query or "")):
        raw=m.group(1).strip().strip('"\'()[]{}<>')
        h=raw.lower().strip(".")
        if h.startswith("www."): h=h[4:]
        if h: vals.append(h)
    return vals

def _tokens(text:str)->list[str]:
    return re.findall(r"\w+",str(text or "").casefold(),flags=re.UNICODE)

def _contains_long_verbatim(query:str,question:str,threshold_words:int)->bool:
    if isinstance(threshold_words,bool) or threshold_words<1:
        raise ValueError("VERBATIM_THRESHOLD_INVALID")
    q=_tokens(query); src=_tokens(question)
    if len(q)<threshold_words or len(src)<threshold_words: return False
    spans={tuple(src[i:i+threshold_words]) for i in range(len(src)-threshold_words+1)}
    return any(tuple(q[i:i+threshold_words]) in spans for i in range(len(q)-threshold_words+1))

def check_search_query(query:str, *, question:str, verbatim_threshold_words:int|None,
                       policy:Mapping[str,Any]|None=None)->dict[str,Any]:
    p=dict(policy or load_policy())
    q=" ".join(str(query or "").split())
    if not q: raise HLEPolicyBlocked("SEARCH_QUERY_REQUIRED")
    text_hit=_text_rule(q,p)
    if text_hit: raise HLEPolicyBlocked("BLOCKED_SEARCH_QUERY",rule_type=text_hit[0],rule=text_hit[1])
    for d in _site_domains(q):
        for blocked in p["domains"]:
            if _domain_matches(d,blocked):
                raise HLEPolicyBlocked("BLOCKED_SITE_DOMAIN",rule_type="domains",rule=blocked)
    if verbatim_threshold_words is None:
        raise HLEPolicyBlocked("UNPUBLISHED_VERBATIM_THRESHOLD_UNBOUND")
    if _contains_long_verbatim(q,question,verbatim_threshold_words):
        raise HLEPolicyBlocked("LONG_VERBATIM_QUESTION_SPAN")
    return {"schema":SCHEMA,"status":"PASS","query":q}

def filter_search_results(query:str, results:Sequence[Mapping[str,Any]], *,
                          question:str, verbatim_threshold_words:int|None,
                          policy:Mapping[str,Any]|None=None)->dict[str,Any]:
    p=dict(policy or load_policy())
    check_search_query(query,question=question,verbatim_threshold_words=verbatim_threshold_words,policy=p)
    if not isinstance(results,Sequence) or isinstance(results,(str,bytes)):
        raise ValueError("SEARCH_RESULTS_SEQUENCE_REQUIRED")
    kept=[]; blocked=[]
    for row in list(results)[:MAX_SEARCH_RESULTS]:
        if not isinstance(row,Mapping):
            blocked.append({"reason":"RESULT_MAPPING_REQUIRED"}); continue
        url=str(row.get("url") or ""); title=str(row.get("title") or ""); snippet=str(row.get("snippet") or "")
        reason=_url_rule(url,p)
        if reason is None:
            reason=_text_rule(title,p) or _text_rule(snippet,p)
        if reason is None:
            reason=_answer_title_rule(title,_host(url),p)
        if reason is not None:
            blocked.append({"url":url,"rule_type":reason[0],"rule":reason[1]}); continue
        kept.append({"url":url,"title":title,"snippet":snippet})
    return {
        "schema":SCHEMA,"status":"PASS","results":kept,"returned_count":len(kept),
        "pre_filter_count":min(len(results),MAX_SEARCH_RESULTS),"blocked":blocked,
        "max_results_before_filtering":MAX_SEARCH_RESULTS,
    }

def check_fetch_url(url:str, *, policy:Mapping[str,Any]|None=None)->dict[str,Any]:
    p=dict(policy or load_policy())
    if not str(url or "").strip(): raise HLEPolicyBlocked("FETCH_URL_REQUIRED")
    reason=_url_rule(str(url),p)
    if reason: raise HLEPolicyBlocked("BLOCKED_FETCH_URL",rule_type=reason[0],rule=reason[1])
    return {"schema":SCHEMA,"status":"PASS","url":str(url)}

def filter_fetch_result(url:str, *, title:str, markdown:str, cached:bool=False,
                        policy:Mapping[str,Any]|None=None)->dict[str,Any]:
    p=dict(policy or load_policy())
    check_fetch_url(url,policy=p)
    for surface,name in ((str(title or ""),"title"),(str(markdown or ""),"markdown")):
        reason=_text_rule(surface,p)
        if reason:
            raise HLEPolicyBlocked("BLOCKED_FETCH_"+name.upper(),rule_type=reason[0],rule=reason[1])
    text=str(markdown or "")
    truncated=len(text)>MAX_FETCH_CHARS
    if truncated:
        marker="\n\n[TRUNCATED]"
        text=text[:MAX_FETCH_CHARS-len(marker)]+marker
    return {
        "schema":SCHEMA,"status":"PASS","url":str(url),"title":str(title or ""),
        "markdown":text,"truncated":truncated,"cached":bool(cached),
        "max_chars":MAX_FETCH_CHARS,
    }

def policy_preflight(*, verbatim_threshold_words:int|None)->dict[str,Any]:
    p=load_policy()
    unresolved=[]
    if verbatim_threshold_words is None:
        unresolved.append("OFFICIAL_LONG_VERBATIM_SPAN_THRESHOLD")
    unresolved.append("OFFICIAL_TRAILING_SITE_NAME_STRIPPER_EXACT_ALGORITHM")
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED__UNPUBLISHED_PARAMETERS_OPEN" if unresolved else "PASS",
        "published_rule_fields_bound":7,
        "search_limit":MAX_SEARCH_RESULTS,
        "fetch_limit_chars":MAX_FETCH_CHARS,
        "unresolved_exact_harness_parameters":unresolved,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
