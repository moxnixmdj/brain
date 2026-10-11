#!/usr/bin/env python3
"""Answer-blind Wikipedia retrieval without the MediaWiki search API.

Bing web search discovers en.wikipedia.org/wiki article URLs; ordinary page
fetch supplies bounded evidence text. This avoids the burst-rate-limited
MediaWiki search API observed in HLE diagnostics. No model or gold is used.
"""
from __future__ import annotations
import html,re,urllib.parse
from typing import Any,Callable,Mapping

SCHEMA="PROJECT_BRAIN_HLE_WIKIPEDIA_BING_TRANSPORT_V1"
_TAG=re.compile(r"<[^>]+>")
_WS=re.compile(r"\s+")

def _canon(v:Any)->str:
    return _WS.sub(" ",html.unescape(str(v or ""))).strip()

def _is_wikipedia_article(url:str)->bool:
    try:u=urllib.parse.urlsplit(str(url or ""))
    except Exception:return False
    host=(u.hostname or "").lower().strip(".")
    if host!="en.wikipedia.org" or not u.path.startswith("/wiki/"):return False
    title=urllib.parse.unquote(u.path[len("/wiki/"):]).split("/",1)[0]
    return bool(title and ":" not in title)

def _text_from_html(text:str)->str:
    x=re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<noscript\b.*?</noscript>"," ",str(text or ""))
    return _canon(_TAG.sub(" ",x))

def retrieve(*,query:str,limit:int=4,timeout:float=20.0,
             search_fn:Callable[...,Mapping[str,Any]]|None=None,
             fetch_fn:Callable[...,Mapping[str,Any]]|None=None)->dict[str,Any]:
    q=_canon(query)
    if not q:raise ValueError("QUERY_REQUIRED")
    limit=max(1,min(int(limit),8))
    if search_fn is None or fetch_fn is None:
        from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
        search_fn=search_fn or tools.search_web
        fetch_fn=fetch_fn or tools.fetch_web
    search_query=f"site:en.wikipedia.org/wiki {q}"
    try:
        found=search_fn(search_query,limit=max(8,limit*2),timeout=timeout)
    except Exception as exc:
        return {
          "schema":SCHEMA,"status":"SEARCH_FAILED_RETRYABLE","query":q,
          "search_query":search_query,"pages":[],"page_count":0,
          "search_error_class":type(exc).__name__,"retryable":True,
          "gold_accessed":False,"external_model_calls":0,
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
            fetched=fetch_fn(url,timeout=timeout,max_bytes=1000000)
            if not isinstance(fetched,Mapping):raise ValueError("FETCH_RESULT_MAPPING_REQUIRED")
            status=_canon(fetched.get("status"))
            if status!="PASS":raise RuntimeError("FETCH_STATUS_"+status)
            text=_text_from_html(fetched.get("body_excerpt") or "")
            pages.append({"rank":rank,"url":url,"status":"PASS","text":text,"text_length":len(text)})
        except Exception as exc:
            failed+=1
            pages.append({"rank":rank,"url":url,"status":"FAILED_RETRYABLE","text":"","text_length":0,
                          "error_class":type(exc).__name__,"retryable":True})
    passed=sum(x["status"]=="PASS" for x in pages)
    if passed:status="PAGES_FETCHED"
    elif urls:status="PAGE_FETCH_FAILED_RETRYABLE"
    else:status="NO_WIKIPEDIA_CANDIDATES_YET"
    return {
      "schema":SCHEMA,"status":status,"query":q,"search_query":search_query,
      "candidate_url_count":len(urls),"page_count":len(pages),
      "successful_page_count":passed,"failed_retryable_page_count":failed,
      "pages":pages,"search_attempts":found.get("attempts") or [],
      "retryable":bool(urls and not passed),"gold_accessed":False,
      "external_model_calls":0,"external_reasoning_model_calls":0,
      "model_dependency_count":0,"answer_authority":False,
      "correctness_authority":False,"nonexistence_claim_authorized":False,
      "incremental_spend_usd":0,
      "hard_rules":[
        "VISIBLE_QUERY_ONLY","NO_MEDIAWIKI_SEARCH_API","WIKIPEDIA_ARTICLE_HOST_ONLY",
        "FAILED_FETCH_IS_RETRYABLE","EMPTY_SEARCH_IS_NOT_NONEXISTENCE",
        "NO_GOLD_ACCESS","NO_EXTERNAL_MODEL_COGNITION",
        "ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY"
      ],
    }

if __name__=="__main__":
    def s(q,**k):return {"results":[{"url":"https://en.wikipedia.org/wiki/Example"}],"attempts":[]}
    def f(u,**k):return {"status":"PASS","body_excerpt":"<p>Example article.</p>"}
    x=retrieve(query="example",search_fn=s,fetch_fn=f)
    assert x["status"]=="PAGES_FETCHED" and x["gold_accessed"] is False
    print("SELF_TEST_PASS")
