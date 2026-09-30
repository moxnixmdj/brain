#!/usr/bin/env python3
"""Hard-zero, model-independent web source candidate discovery.

Discovery is deliberately separate from authority verification. This module returns
provenance-rich candidate URLs from independent public search surfaces; callers
must verify source authority/content before using evidence for a decision.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from typing import Iterable

UA = "ProjectBrain-SourceDiscovery/1.0 (+model-independent; hard-zero)"
MAX_BODY = 1_500_000

STOP = {
    "a","an","the","and","or","but","if","then","than","that","this","these","those","to","of","in","on","at","by","for","from","with","without","as","is","are","was","were","be","been","being","it","its","into","through","during","while","under","over","near","about","around","between",
    "determine","whether","find","cite","use","using","provide","produce","perform","include","including","derive","explain","compare","assess","evaluate","verify","independently","independent","authoritative","primary","source","sources","evidence","method","methods","result","results","limitations","provenance","decision","quality","real","executable","experiment","research","objective","goal","task",
}
NOISY_HOSTS = {
    "reddit.com","www.reddit.com","medium.com","www.medium.com","quora.com","www.quora.com",
    "youtube.com","www.youtube.com","facebook.com","www.facebook.com","x.com","twitter.com",
    "stackoverflow.com","www.stackoverflow.com","stackexchange.com","www.stackexchange.com",
    "pinterest.com","www.pinterest.com","tiktok.com","www.tiktok.com",
}
DOC_HINTS = ("/docs", "/documentation", "/reference", "/manual", "/spec", "/standard", "/api", "/guide")


def _words(text: str) -> list[str]:
    out=[]
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_.+/#:-]*|\d+(?:\.\d+)?(?:°[CF])?", text or ""):
        t=token.strip(".,;:!?()[]{}<>\"'").lower()
        if len(t) < 2 or t in STOP:
            continue
        if t not in out:
            out.append(t)
    return out


def semantic_query(goal: str, max_terms: int = 18) -> str:
    """Reduce instruction-heavy broad goals to stable content-bearing query terms."""
    words=_words(goal)
    if not words:
        raise ValueError("SOURCE_DISCOVERY_EMPTY_SEMANTIC_QUERY")
    # Preserve order so names/technical phrases remain adjacent; cap query size.
    return " ".join(words[:max_terms])


def query_variants(goal: str) -> list[str]:
    base=semantic_query(goal)
    variants=[
        base,
        base + " official documentation",
        base + " specification standard",
        base + " technical reference",
    ]
    out=[]
    for q in variants:
        q=" ".join(q.split())
        if q and q not in out:
            out.append(q)
    return out


def _request(url: str, timeout: float = 15.0) -> bytes:
    req=urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status=getattr(resp, "status", 200)
        if status != 200:
            raise RuntimeError(f"HTTP_STATUS_{status}")
        body=resp.read(MAX_BODY + 1)
    if len(body) > MAX_BODY:
        raise RuntimeError("SOURCE_DISCOVERY_RESPONSE_TOO_LARGE")
    return body


def _norm_url(raw: str) -> str | None:
    if not raw:
        return None
    raw=html.unescape(raw).strip()
    try:
        p=urllib.parse.urlsplit(raw)
    except Exception:
        return None
    # DDG result redirects carry the target in uddg=.
    if p.hostname and p.hostname.endswith("duckduckgo.com"):
        qs=urllib.parse.parse_qs(p.query)
        target=(qs.get("uddg") or [None])[0]
        if target:
            return _norm_url(target)
    if p.scheme not in {"http","https"} or not p.hostname:
        return None
    host=p.hostname.lower().rstrip(".")
    port=f":{p.port}" if p.port and not ((p.scheme=="https" and p.port==443) or (p.scheme=="http" and p.port==80)) else ""
    path=p.path or "/"
    # Drop tracking fragments/query parameters for identity; preserve semantically meaningful query.
    pairs=[]
    for k,v in urllib.parse.parse_qsl(p.query, keep_blank_values=True):
        kl=k.lower()
        if kl.startswith("utm_") or kl in {"gclid","fbclid","mc_cid","mc_eid"}:
            continue
        pairs.append((k,v))
    query=urllib.parse.urlencode(pairs, doseq=True)
    return urllib.parse.urlunsplit((p.scheme.lower(), host+port, path, query, ""))


@dataclass(frozen=True)
class Hit:
    provider: str
    query: str
    rank: int
    url: str
    title: str
    snippet: str


def parse_bing_rss(raw: bytes, query: str) -> list[Hit]:
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RuntimeError("BING_RSS_INVALID_XML") from exc
    out=[]
    for i,item in enumerate(root.findall(".//item")):
        title=(item.findtext("title") or "").strip()
        link=_norm_url((item.findtext("link") or "").strip())
        desc=re.sub(r"\s+", " ", html.unescape(item.findtext("description") or "")).strip()
        if link and title:
            out.append(Hit("BING_RSS", query, i+1, link, title[:500], desc[:1200]))
    return out


def search_bing_rss(query: str, timeout: float = 15.0) -> list[Hit]:
    params=urllib.parse.urlencode({"q":query,"format":"rss","mkt":"en-US","setlang":"en-US"})
    raw=_request("https://www.bing.com/search?"+params, timeout)
    return parse_bing_rss(raw, query)


class _DDGParser(HTMLParser):
    def __init__(self, query: str):
        super().__init__(convert_charrefs=True)
        self.query=query; self._href=None; self._buf=[]; self.hits=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a": return
        d=dict(attrs); href=d.get("href","")
        cls=d.get("class","")
        rel=d.get("rel","")
        if "result-link" in cls or "result__a" in cls or "nofollow" in rel:
            self._href=href; self._buf=[]
    def handle_data(self, data):
        if self._href is not None: self._buf.append(data)
    def handle_endtag(self, tag):
        if tag.lower()=="a" and self._href is not None:
            u=_norm_url(self._href); title=" ".join("".join(self._buf).split())
            if u and title and "duckduckgo.com" not in urllib.parse.urlsplit(u).netloc:
                self.hits.append(Hit("DDG_LITE", self.query, len(self.hits)+1, u, title[:500], ""))
            self._href=None; self._buf=[]


def parse_ddg_html(raw: bytes, query: str) -> list[Hit]:
    parser=_DDGParser(query)
    parser.feed(raw.decode("utf-8","replace"))
    # Deduplicate redirect variants while keeping rank.
    seen=set(); out=[]
    for h in parser.hits:
        if h.url in seen: continue
        seen.add(h.url); out.append(h)
    return out


def search_ddg_lite(query: str, timeout: float = 15.0) -> list[Hit]:
    url="https://lite.duckduckgo.com/lite/?"+urllib.parse.urlencode({"q":query,"kl":"us-en"})
    raw=_request(url, timeout)
    return parse_ddg_html(raw, query)


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def _authority_signal(url: str) -> float:
    """Ranking signal only. This never certifies authority."""
    h=_host(url); p=urllib.parse.urlsplit(url).path.lower()
    score=0.0
    if h.endswith(".gov"): score += 28
    if h.endswith(".edu"): score += 12
    if h.endswith(".int"): score += 16
    if h.startswith(("docs.","developer.","developers.","reference.")): score += 8
    if any(x in p for x in DOC_HINTS): score += 7
    if h in NOISY_HOSTS or any(h.endswith("."+n) for n in NOISY_HOSTS): score -= 35
    return score


def aggregate(goal: str, hits: Iterable[Hit], limit: int = 12) -> list[dict]:
    terms=set(_words(goal))
    records={}
    for hit in hits:
        u=_norm_url(hit.url)
        if not u: continue
        h=_host(u)
        key=u
        rec=records.setdefault(key,{"url":u,"host":h,"title":hit.title,"snippet":hit.snippet,"observations":[],"providers":set(),"queries":set()})
        rec["observations"].append({"provider":hit.provider,"query":hit.query,"rank":hit.rank})
        rec["providers"].add(hit.provider); rec["queries"].add(hit.query)
        if len(hit.snippet)>len(rec["snippet"]): rec["snippet"]=hit.snippet
        if len(hit.title)>len(rec["title"]): rec["title"]=hit.title
    ranked=[]
    for rec in records.values():
        rank_score=sum(30.0/max(1,o["rank"]) for o in rec["observations"])
        provider_bonus=18.0*max(0,len(rec["providers"])-1)
        query_bonus=4.0*max(0,len(rec["queries"])-1)
        text=(rec["host"]+" "+rec["title"]+" "+rec["snippet"]).lower()
        overlap=sum(1 for t in terms if t in text)
        score=rank_score+provider_bonus+query_bonus+2.0*overlap+_authority_signal(rec["url"])
        ranked.append({
            "url":rec["url"],"host":rec["host"],"title":rec["title"],"snippet":rec["snippet"],
            "discovery_score":round(score,3),"authority_signal_only":round(_authority_signal(rec["url"]),3),
            "provider_count":len(rec["providers"]),"query_variant_count":len(rec["queries"]),
            "observations":sorted(rec["observations"],key=lambda x:(x["provider"],x["query"],x["rank"])),
            "authority_verified":False,
        })
    ranked.sort(key=lambda x:(-x["discovery_score"],x["host"],x["url"]))
    # Diversity: cap at 2 URLs/host so one site cannot monopolize the frontier.
    out=[]; per_host={}
    for rec in ranked:
        if per_host.get(rec["host"],0)>=2: continue
        out.append(rec); per_host[rec["host"]]=per_host.get(rec["host"],0)+1
        if len(out)>=limit: break
    return out


def discover(goal: str, *, timeout: float = 15.0, max_variants: int = 3, limit: int = 12) -> dict:
    variants=query_variants(goal)[:max_variants]
    hits=[]; attempts=[]
    providers=(search_bing_rss, search_ddg_lite)
    for query in variants:
        for fn in providers:
            started=time.monotonic()
            provider_name=getattr(fn, "__name__", type(fn).__name__)
            try:
                found=fn(query, timeout=timeout)
                hits.extend(found)
                attempts.append({"provider":provider_name,"query":query,"ok":True,"result_count":len(found),"wall_ms":round((time.monotonic()-started)*1000,1)})
            except Exception as exc:
                attempts.append({"provider":provider_name,"query":query,"ok":False,"error":type(exc).__name__+":"+str(exc),"wall_ms":round((time.monotonic()-started)*1000,1)})
    candidates=aggregate(goal,hits,limit=limit)
    if not candidates:
        raise RuntimeError("NO_SOURCE_DISCOVERY_CANDIDATES:"+json.dumps(attempts,sort_keys=True)[:3000])
    return {
        "schema":"PROJECT_BRAIN_MODEL_INDEPENDENT_SOURCE_DISCOVERY_V1",
        "status":"CANDIDATES_DISCOVERED_AUTHORITY_UNVERIFIED",
        "goal":goal,
        "semantic_query":semantic_query(goal),
        "query_variants":variants,
        "attempts":attempts,
        "candidate_count":len(candidates),
        "candidates":candidates,
        "incremental_spend_usd":0,
        "model_dependency_count":0,
        "authority_claim":False,
        "next_gate":"INDEPENDENT_SOURCE_AUTHORITY_AND_CONTENT_VERIFICATION",
    }


if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("goal"); ap.add_argument("--limit",type=int,default=12)
    args=ap.parse_args()
    print(json.dumps(discover(args.goal,limit=args.limit),indent=2,sort_keys=True))
