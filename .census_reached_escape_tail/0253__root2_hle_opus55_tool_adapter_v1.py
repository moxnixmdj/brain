#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT=Path(__file__).resolve().parents[2]
POLICY_PATH=ROOT/"canonical/governance/HLE_OPUS55_TOOL_POLICY_V1.json"
SCHEMA="PROJECT_BRAIN_ROOT2_HLE_OPUS55_TOOL_ADAPTER_V1"
USER_AGENT="ProjectBrain-HLE-Opus55/1.0"

class HLEToolBlocked(RuntimeError):
    pass

def load_policy(path:Path=POLICY_PATH)->dict[str,Any]:
    x=json.loads(path.read_text(encoding="utf-8"))
    if x.get("schema")!="PROJECT_BRAIN_HLE_OPUS55_TOOL_POLICY_V1":
        raise HLEToolBlocked("POLICY_SCHEMA_INVALID")
    pats=x.get("blocklist_patterns")
    if not isinstance(pats,list) or not pats or any(not isinstance(p,str) or not p.strip() for p in pats):
        raise HLEToolBlocked("BLOCKLIST_INVALID")
    return x

def normalize_block_value(value:str)->str:
    return str(value or "").replace("/","").lower()

def block_match(url:str, policy:Mapping[str,Any])->str|None:
    normalized=normalize_block_value(url)
    for raw in policy.get("blocklist_patterns") or []:
        pat=normalize_block_value(str(raw))
        if pat and pat in normalized:
            return str(raw)
    return None

def assert_url_allowed(url:str, policy:Mapping[str,Any])->None:
    parsed=urllib.parse.urlparse(str(url or ""))
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise HLEToolBlocked("URL_INVALID")
    hit=block_match(url,policy)
    if hit is not None:
        raise HLEToolBlocked("HLE_CONTAMINATION_BLOCKLIST:"+hit)

def _default_get(url:str, *, timeout:float=20.0, max_bytes:int=1500000)->dict[str,Any]:
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        raw=resp.read(max_bytes)
        return {
            "status":int(resp.status),
            "final_url":str(resp.geturl()),
            "headers":dict(resp.headers.items()),
            "body":raw,
        }

def _normalize_result_href(engine:str, href:str)->str|None:
    raw=str(href or "").replace("&amp;","&").strip()
    if not raw:
        return None
    if raw.startswith("//"):
        raw="https:"+raw
    if raw.startswith("/"):
        if engine=="google" and raw.startswith("/url?"):
            q=urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("q") or []
            raw=q[0] if q else ""
        elif engine=="duckduckgo":
            absolute=urllib.parse.urljoin("https://html.duckduckgo.com/",raw)
            q=urllib.parse.parse_qs(urllib.parse.urlparse(absolute).query).get("uddg") or []
            raw=urllib.parse.unquote(q[0]) if q else ""
        else:
            return None
    try:
        parsed=urllib.parse.urlparse(raw)
    except Exception:
        return None
    host=(parsed.hostname or "").lower()
    if host.endswith("duckduckgo.com"):
        q=urllib.parse.parse_qs(parsed.query).get("uddg") or []
        if q:
            raw=urllib.parse.unquote(q[0])
    elif host.endswith("google.com"):
        q=urllib.parse.parse_qs(parsed.query).get("q") or []
        if q and str(q[0]).startswith(("http://","https://")):
            raw=q[0]
    parsed=urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        return None
    return raw

def search_web(
    query:str,
    *,
    limit:int=10,
    timeout:float=20.0,
    policy:Mapping[str,Any]|None=None,
    fetcher:Callable[...,Mapping[str,Any]]=_default_get,
)->dict[str,Any]:
    policy=dict(policy or load_policy())
    q=" ".join(str(query or "").split())
    if not q:
        raise HLEToolBlocked("QUERY_REQUIRED")
    if limit<1 or limit>25:
        raise HLEToolBlocked("LIMIT_INVALID")
    engines=[
        ("bing_rss","https://www.bing.com/search?"+urllib.parse.urlencode({"q":q,"format":"rss","count":str(max(20,limit))})),
        ("bing","https://www.bing.com/search?"+urllib.parse.urlencode({"q":q,"count":str(max(20,limit))})),
        ("duckduckgo","https://html.duckduckgo.com/html/?"+urllib.parse.urlencode({"q":q})),
        ("google","https://www.google.com/search?"+urllib.parse.urlencode({"q":q,"num":str(max(20,limit))})),
    ]
    href_re=re.compile(r'''href=["']([^"'<>\s]+)["']''',re.IGNORECASE)
    results=[]
    attempts=[]
    seen=set()
    blocked=[]
    for engine,url in engines:
        try:
            resp=fetcher(url,timeout=timeout,max_bytes=1500000)
            body=resp.get("body") or b""
            if isinstance(body,str):
                text=body
            else:
                text=bytes(body).decode("utf-8","replace")
        except Exception as exc:
            attempts.append({"engine":engine,"status":"FAILED","error":type(exc).__name__})
            continue
        raw_hrefs=[]
        if engine=="bing_rss":
            raw_hrefs.extend(re.findall(r"<item>.*?<link>\s*(https?://[^<\s]+)\s*</link>.*?</item>",text,re.I|re.S))
        else:
            raw_hrefs.extend(href_re.findall(text))
        accepted=0
        rejected=0
        for raw in raw_hrefs:
            href=_normalize_result_href(engine,raw)
            if not href or href in seen:
                continue
            seen.add(href)
            host=(urllib.parse.urlparse(href).hostname or "").lower()
            if host in {"bing.com","www.bing.com","duckduckgo.com","html.duckduckgo.com","google.com","www.google.com"}:
                continue
            hit=block_match(href,policy)
            if hit is not None:
                blocked.append({"url":href,"pattern":hit,"engine":engine})
                rejected+=1
                continue
            results.append({"url":href,"engine":engine})
            accepted+=1
            if len(results)>=limit:
                break
        attempts.append({"engine":engine,"status":"OK","accepted":accepted,"blocked":rejected})
        if len(results)>=limit:
            break
    return {
        "schema":SCHEMA,
        "tool":"web_search",
        "status":"PASS" if results else "NO_RESULTS",
        "query":q,
        "results":results[:limit],
        "attempts":attempts,
        "blocked_result_count":len(blocked),
        "blocked_results":blocked[:25],
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
    }

def fetch_web(
    url:str,
    *,
    timeout:float=20.0,
    max_bytes:int=1000000,
    policy:Mapping[str,Any]|None=None,
    fetcher:Callable[...,Mapping[str,Any]]=_default_get,
)->dict[str,Any]:
    policy=dict(policy or load_policy())
    assert_url_allowed(url,policy)
    resp=fetcher(url,timeout=timeout,max_bytes=max_bytes)
    status=int(resp.get("status") or 0)
    final_url=str(resp.get("final_url") or url)
    assert_url_allowed(final_url,policy)
    body=resp.get("body") or b""
    raw=body.encode("utf-8") if isinstance(body,str) else bytes(body)
    return {
        "schema":SCHEMA,
        "tool":"web_fetch",
        "status":"PASS" if 200<=status<400 else "HTTP_STATUS_"+str(status),
        "url":str(url),
        "final_url":final_url,
        "http_status":status,
        "body_sha256":hashlib.sha256(raw).hexdigest(),
        "body_excerpt":raw[:12000].decode("utf-8","replace"),
        "incremental_spend_usd":0,
    }

SAFE_IMPORT_ROOTS={
    "math","cmath","statistics","fractions","decimal","itertools","functools",
    "collections","heapq","bisect","re","json","datetime","time","random",
}

def _validate_code(source:str)->None:
    if len(source)>40000:
        raise HLEToolBlocked("CODE_TOO_LARGE")
    tree=ast.parse(source,mode="exec")
    forbidden_names={"open","exec","eval","compile","__import__","input","breakpoint"}
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else [str(node.module or "")]
            for name in names:
                root=name.split(".",1)[0]
                if root not in SAFE_IMPORT_ROOTS:
                    raise HLEToolBlocked("CODE_IMPORT_FORBIDDEN:"+root)
        if isinstance(node,ast.Name) and node.id in forbidden_names:
            raise HLEToolBlocked("CODE_NAME_FORBIDDEN:"+node.id)
        if isinstance(node,ast.Attribute) and str(node.attr).startswith("__"):
            raise HLEToolBlocked("CODE_DUNDER_ATTRIBUTE_FORBIDDEN")

def execute_code(source:str, *, timeout:float=10.0)->dict[str,Any]:
    src=str(source or "")
    _validate_code(src)
    if timeout<=0 or timeout>30:
        raise HLEToolBlocked("CODE_TIMEOUT_INVALID")
    with tempfile.TemporaryDirectory(prefix="brain-hle-code-") as td:
        p=subprocess.run(
            [sys.executable,"-I","-S","-c",src],
            cwd=td,
            text=True,
            capture_output=True,
            timeout=timeout,
            env={"PYTHONIOENCODING":"utf-8"},
        )
    return {
        "schema":SCHEMA,
        "tool":"code_execution",
        "status":"PASS" if p.returncode==0 else "NONZERO",
        "returncode":p.returncode,
        "stdout":p.stdout[-12000:],
        "stderr":p.stderr[-12000:],
        "source_sha256":hashlib.sha256(src.encode("utf-8")).hexdigest(),
        "network_policy":"NETWORK_RELATED_IMPORTS_FORBIDDEN__NOT_AN_OS_LEVEL_SANDBOX_CLAIM",
        "incremental_spend_usd":0,
    }

def invoke(tool:str,args:Mapping[str,Any])->dict[str,Any]:
    name=str(tool or "")
    if name=="web_search":
        return search_web(str(args.get("query") or ""),limit=int(args.get("limit") or 10))
    if name=="web_fetch":
        return fetch_web(str(args.get("url") or ""),max_bytes=int(args.get("max_bytes") or 1000000))
    if name=="code_execution":
        return execute_code(str(args.get("code") or ""),timeout=float(args.get("timeout_s") or 10))
    raise HLEToolBlocked("UNKNOWN_TOOL:"+name)

def tool_contract()->dict[str,Any]:
    policy=load_policy()
    return {
        "schema":SCHEMA,
        "status":"READY",
        "tools":["web_search","web_fetch","programmatic_tool_calling","code_execution"],
        "programmatic_tool_calling":"invoke(tool,args)",
        "blocklist_pattern_count":len(policy["blocklist_patterns"]),
        "blocklist_semantics":"LOWERCASE_AND_REMOVE_FORWARD_SLASHES__SUBSTRING_BLOCK",
        "context_compaction":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
