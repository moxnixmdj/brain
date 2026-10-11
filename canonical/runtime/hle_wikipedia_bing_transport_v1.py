#!/usr/bin/env python3
"""Answer-blind Wikipedia retrieval without the MediaWiki search API.

Bing RSS discovers en.wikipedia.org/wiki article URLs; ordinary article-page
fetch supplies bounded evidence text. This avoids the burst-rate-limited
MediaWiki search API observed in HLE diagnostics. No model or gold is used.
"""
from __future__ import annotations
import html,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from typing import Any,Callable,Mapping

SCHEMA="PROJECT_BRAIN_HLE_WIKIPEDIA_BING_TRANSPORT_V1"
UA="ProjectBrain-HLE-WikipediaBing/1.0"
_TAG=re.compile(r"<[^>]+>")
_WS=re.compile(r"\s+")
_NAMESPACE_PREFIXES={
 "category","file","help","special","portal","template","talk","user","wikipedia",
 "draft","module","mediawiki","book","education program","timedtext","topic"
}

def _canon(v:Any)->str:
    return _WS.sub(" ",html.unescape(str(v or ""))).strip()

def _is_wikipedia_article(url:str)->bool:
    try:u=urllib.parse.urlsplit(str(url or ""))
    except Exception:return False
    host=(u.hostname or "").lower().strip(".")
    if host!="en.wikipedia.org" or not u.path.startswith("/wiki/"):return False
    title=urllib.parse.unquote(u.path[len("/wiki/"):]).split("/",1)[0]
    if not title:return False
    if ":" in title and title.split(":",1)[0].replace("_"," ").casefold() in _NAMESPACE_PREFIXES:return False
    return True

def _text_from_html(text:str)->str:
    x=re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<noscript\b.*?</noscript>"," ",str(text or ""))
    return _canon(_TAG.sub(" ",x))

def _http_get(url:str,*,timeout:float,max_bytes:int)->dict[str,Any]:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/rss+xml;q=0.9,*/*;q=0.1"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        raw=resp.read(max_bytes)
        return {"status":int(getattr(resp,"status",200)),"final_url":str(resp.geturl()),"body":raw}

def _bing_search(query:str,*,limit:int,timeout:float,fetcher:Callable[...,Mapping[str,Any]]=_http_get)->dict[str,Any]:
    from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
    policy=tools.load_policy()
    endpoint="https://www.bing.com/search?"+urllib.parse.urlencode({"q":f"site:en.wikipedia.org/wiki {query}","format":"rss","count":str(max(10,limit*2))})
    resp=fetcher(endpoint,timeout=timeout,max_bytes=1500000)
    status=int(resp.get("status") or 0)
    raw=resp.get("body") or b""
    text=raw.decode("utf-8","replace") if not isinstance(raw,str) else raw
    root=ET.fromstring(text)
    out=[];seen=set()
    for item in root.findall(".//item"):
        url=_canon(item.findtext("link"))
        if not url or url in seen or not _is_wikipedia_article(url):continue
        if tools.block_match(url,policy) is not None:continue
        seen.add(url)
        out.append({"url":url,"title":_canon(item.findtext("title")),"snippet":_canon(item.findtext("description")),"engine":"BING_RSS"})
        if len(out)>=limit:break
    return {"status":"PASS" if 200<=status<400 else "HTTP_STATUS_"+str(status),"results":out,
            "attempts":[{"engine":"bing_rss","status":"OK" if 200<=status<400 else "HTTP_"+str(status),"accepted":len(out)}]}

def _fetch_page(url:str,*,timeout:float,fetcher:Callable[...,Mapping[str,Any]]=_http_get)->dict[str,Any]:
    from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
    policy=tools.load_policy()
    tools.assert_url_allowed(url,policy)
    resp=fetcher(url,timeout=timeout,max_bytes=1000000)
    status=int(resp.get("status") or 0)
    final_url=str(resp.get("final_url") or url)
    tools.assert_url_allowed(final_url,policy)
    raw=resp.get("body") or b""
    body=raw.decode("utf-8","replace") if not isinstance(raw,str) else raw
    return {"status":"PASS" if 200<=status<400 else "HTTP_STATUS_"+str(status),"final_url":final_url,"body":body}

def retrieve(*,query:str,limit:int=4,timeout:float=20.0,
             search_fn:Callable[...,Mapping[str,Any]]|None=None,
             page_fetch_fn:Callable[...,Mapping[str,Any]]|None=None)->dict[str,Any]:
    q=_canon(query)
    if not q:raise ValueError("QUERY_REQUIRED")
    limit=max(1,min(int(limit),8))
    search_fn=search_fn or _bing_search
    page_fetch_fn=page_fetch_fn or _fetch_page
    try:
        found=search_fn(q,limit=max(4,limit*2),timeout=timeout)
    except Exception as exc:
        return {
          "schema":SCHEMA,"status":"SEARCH_FAILED_RETRYABLE","query":q,
          "pages":[],"page_count":0,"search_error_class":type(exc).__name__,
          "retryable":True,"gold_accessed":False,"external_model_calls":0,
          "external_reasoning_model_calls":0,"model_dependency_count":0,
          "answer_authority":False,"correctness_authority":False,
          "nonexistence_claim_authorized":False,"incremental_spend_usd":0,
        }
    if not isinstance(found,Mapping):raise ValueError("SEARCH_RESULT_MAPPING_REQUIRED")
    raw=found.get("results") or []
    if not isinstance(raw,list):raise ValueError("SEARCH_RESULTS_LIST_REQUIRED")
    urls=[];seen=set()
    for row in raw:
        if not isinstance(row,Mapping):continue
        url=_canon(row.get("url"))
        if not url or url in seen or not _is_wikipedia_article(url):continue
        seen.add(url);urls.append(url)
        if len(urls)>=limit:break
    pages=[];failed=0
    for rank,url in enumerate(urls,1):
        try:
            fetched=page_fetch_fn(url,timeout=timeout)
            if not isinstance(fetched,Mapping):raise ValueError("FETCH_RESULT_MAPPING_REQUIRED")
            status=_canon(fetched.get("status"))
            if status!="PASS":raise RuntimeError("FETCH_STATUS_"+status)
            text=_text_from_html(fetched.get("body") or "")
            pages.append({"rank":rank,"url":url,"final_url":_canon(fetched.get("final_url") or url),
                          "status":"PASS","text":text,"text_length":len(text)})
        except Exception as exc:
            failed+=1
            pages.append({"rank":rank,"url":url,"status":"FAILED_RETRYABLE","text":"","text_length":0,
                          "error_class":type(exc).__name__,"retryable":True})
    passed=sum(x["status"]=="PASS" for x in pages)
    if passed:status="PAGES_FETCHED"
    elif urls:status="PAGE_FETCH_FAILED_RETRYABLE"
    else:status="NO_WIKIPEDIA_CANDIDATES_YET"
    return {
      "schema":SCHEMA,"status":status,"query":q,
      "candidate_url_count":len(urls),"page_count":len(pages),
      "successful_page_count":passed,"failed_retryable_page_count":failed,
      "pages":pages,"search_attempts":found.get("attempts") or [],
      "retryable":bool(urls and not passed),"gold_accessed":False,
      "external_model_calls":0,"external_reasoning_model_calls":0,
      "model_dependency_count":0,"answer_authority":False,
      "correctness_authority":False,"nonexistence_claim_authorized":False,
      "incremental_spend_usd":0,
      "hard_rules":[
        "VISIBLE_QUERY_ONLY","NO_MEDIAWIKI_SEARCH_API","BING_RSS_DISCOVERY_ONLY",
        "WIKIPEDIA_ARTICLE_HOST_ONLY","FULL_BOUNDED_PAGE_BODY_BEFORE_TEXT_EXTRACTION",
        "FAILED_FETCH_IS_RETRYABLE","EMPTY_SEARCH_IS_NOT_NONEXISTENCE",
        "NO_GOLD_ACCESS","NO_EXTERNAL_MODEL_COGNITION",
        "ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY"
      ],
    }

if __name__=="__main__":
    def s(q,**k):return {"results":[{"url":"https://en.wikipedia.org/wiki/Example"}],"attempts":[{"engine":"bing_rss","status":"OK"}]}
    def f(u,**k):return {"status":"PASS","final_url":u,"body":"<p>Example article.</p>"}
    x=retrieve(query="example",search_fn=s,page_fetch_fn=f)
    assert x["status"]=="PAGES_FETCHED" and x["gold_accessed"] is False
    print("SELF_TEST_PASS")
