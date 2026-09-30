#!/usr/bin/env python3
"""Fail-closed model-independent source authority binding via Wikidata P856.

Scope is deliberately narrow: a candidate web host is authority-bound only when
an independent public registry entity declares an official website whose host
is the same site as the candidate host. This verifies source/entity identity,
not relevance, primary-evidence status, or evidence sufficiency.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request

SCHEMA="PROJECT_BRAIN_SOURCE_AUTHORITY_BINDING_WIKIDATA_V1"
UA="ProjectBrain-SourceAuthorityBinding/1.0 (+zero-cost model-independent research)"
_WIKIDATA_HOSTS={"www.wikidata.org","wikidata.org"}
_GENERIC_HOST_PARTS={"www","docs","doc","api","developer","developers","help","support","home","web"}
_GENERIC_TITLE_WORDS={
    "official","website","site","home","homepage","documentation","docs","page",
    "welcome","the","a","an","and","or","of","to","for","in","on","with","from","by",
}
_INFRASTRUCTURE_HOSTS={
    "doi.org","dx.doi.org","crossref.org","www.crossref.org","api.crossref.org",
    "bing.com","www.bing.com","duckduckgo.com","www.duckduckgo.com",
    "google.com","www.google.com",
}


def _canon(value):
    return " ".join(str(value or "").strip().split())


def _safe_url(raw):
    try:
        u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in ("http","https") or not u.netloc:
        return None
    host=(u.hostname or "").lower().strip(".")
    if (
        not host
        or host in {"localhost","127.0.0.1","::1"}
        or host.endswith((".local",".internal"))
    ):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))


def _same_site(left,right):
    a=(left or "").lower().strip(".")
    b=(right or "").lower().strip(".")
    return bool(a and b and (a==b or a.endswith("."+b) or b.endswith("."+a)))


def _fetch_json(url,timeout=20,max_bytes=2_500_000):
    safe=_safe_url(url)
    if safe is None:
        raise ValueError("UNSAFE_URL")
    host=(urllib.parse.urlsplit(safe).hostname or "").lower()
    if host not in _WIKIDATA_HOSTS:
        raise ValueError("NON_WIKIDATA_ENDPOINT_FORBIDDEN")
    req=urllib.request.Request(
        safe,headers={"User-Agent":UA,"Accept":"application/json"}
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes)
        final=_safe_url(r.geturl())
        if final is None:
            raise ValueError("UNSAFE_FINAL_URL")
        final_host=(urllib.parse.urlsplit(final).hostname or "").lower()
        if final_host not in _WIKIDATA_HOSTS:
            raise ValueError("WIKIDATA_REDIRECT_OUTSIDE_REGISTRY")
        return json.loads(raw.decode("utf-8","replace")),final,int(getattr(r,"status",200))


def _host_terms(host):
    out=[]
    for part in (host or "").lower().split("."):
        part=re.sub(r"[^a-z0-9+-]+"," ",part)
        for token in part.split():
            if len(token)>=3 and token not in _GENERIC_HOST_PARTS and token not in out:
                out.append(token)
    return out


def _title_terms(title):
    out=[]
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9.+#_-]{2,}",_canon(title)):
        low=token.lower().strip("._-")
        if len(low)>=3 and low not in _GENERIC_TITLE_WORDS and low not in out:
            out.append(low)
    return out


def _queries(candidate,host):
    queries=[]
    title=_canon(candidate.get("title"))
    publisher=_canon(candidate.get("publisher"))
    for phrase in (title,publisher):
        if phrase and phrase.casefold() not in {x.casefold() for x in queries}:
            queries.append(phrase[:180])
    host_terms=_host_terms(host)
    if host_terms:
        joined=" ".join(host_terms[:3])
        if joined.casefold() not in {x.casefold() for x in queries}:
            queries.append(joined)
    for token in _title_terms(title)+host_terms:
        if token.casefold() not in {x.casefold() for x in queries}:
            queries.append(token)
    return queries[:8]


def _entity_record(qid,timeout):
    endpoint="https://www.wikidata.org/wiki/Special:EntityData/"+qid+".json"
    data,final,status=_fetch_json(endpoint,timeout)
    entity=((data or {}).get("entities") or {}).get(qid) or {}
    official=[]
    for claim in ((entity.get("claims") or {}).get("P856") or []):
        try:
            value=claim["mainsnak"]["datavalue"]["value"]
        except Exception:
            continue
        safe=_safe_url(value)
        if safe:
            official.append(safe)
    label=_canon((((entity.get("labels") or {}).get("en") or {}).get("value")))
    description=_canon((((entity.get("descriptions") or {}).get("en") or {}).get("value")))
    return {
        "qid":qid,
        "label":label or None,
        "description":description or None,
        "official_urls":official,
        "registry_endpoint":final,
        "http_status":status,
    }


def bind_candidate(candidate,timeout=20):
    if not isinstance(candidate,dict):
        raise ValueError("CANDIDATE_OBJECT_REQUIRED")
    url=_safe_url(candidate.get("url"))
    if url is None:
        return {
            "schema":SCHEMA,"status":"AUTHORITY_UNRESOLVED",
            "reason":"SAFE_PUBLIC_HTTP_URL_REQUIRED",
            "authority_status":"UNVERIFIED",
            "primary_source_status":"UNVERIFIED",
            "relevance_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,"incremental_spend_usd":0,
        }
    host=(urllib.parse.urlsplit(url).hostname or "").lower()
    if host in _INFRASTRUCTURE_HOSTS:
        return {
            "schema":SCHEMA,"status":"AUTHORITY_UNRESOLVED",
            "reason":"RESOLVER_OR_SEARCH_INFRASTRUCTURE_HOST_NOT_SOURCE_ENTITY",
            "candidate_url":url,"candidate_host":host,
            "authority_status":"UNVERIFIED",
            "primary_source_status":"UNVERIFIED",
            "relevance_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,"incremental_spend_usd":0,
        }

    queries=_queries(candidate,host)
    observations=[]
    seen_qids=set()
    for query in queries:
        endpoint="https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({
            "action":"wbsearchentities",
            "search":query,
            "language":"en",
            "format":"json",
            "limit":8,
        })
        try:
            data,search_final,search_status=_fetch_json(endpoint,timeout)
        except Exception as exc:
            observations.append({
                "query":query,
                "error_class":type(exc).__name__,
                "error":str(exc)[:240],
            })
            continue
        for item in ((data or {}).get("search") or []):
            qid=_canon(item.get("id"))
            if not re.fullmatch(r"Q[1-9][0-9]*",qid) or qid in seen_qids:
                continue
            seen_qids.add(qid)
            try:
                record=_entity_record(qid,timeout)
            except Exception as exc:
                observations.append({
                    "query":query,"qid":qid,
                    "error_class":type(exc).__name__,
                    "error":str(exc)[:240],
                })
                continue
            for official_url in record["official_urls"]:
                official_host=(urllib.parse.urlsplit(official_url).hostname or "").lower()
                if _same_site(host,official_host):
                    return {
                        "schema":SCHEMA,
                        "status":"AUTHORITY_IDENTITY_VERIFIED",
                        "verification_method":"WIKIDATA_P856_OFFICIAL_WEBSITE_HOST_BINDING",
                        "candidate_url":url,
                        "candidate_host":host,
                        "entity_id":qid,
                        "entity_label":record["label"] or _canon(item.get("label")) or None,
                        "entity_description":record["description"],
                        "official_url":official_url,
                        "official_host":official_host,
                        "matched_query":query,
                        "registry_endpoint":record["registry_endpoint"],
                        "registry_property":"P856",
                        "authority_status":"VERIFIED",
                        "authority_claim_scope":"HOST_TO_DECLARED_OFFICIAL_WEBSITE_IDENTITY_ONLY",
                        "primary_source_status":"UNVERIFIED",
                        "relevance_status":"UNVERIFIED",
                        "evidence_sufficiency_status":"UNVERIFIED",
                        "model_dependency_count":0,
                        "incremental_spend_usd":0,
                    }
            observations.append({
                "query":query,
                "qid":qid,
                "entity_label":record["label"],
                "official_url_count":len(record["official_urls"]),
                "search_endpoint":search_final,
                "search_http_status":search_status,
            })

    return {
        "schema":SCHEMA,
        "status":"AUTHORITY_UNRESOLVED",
        "reason":"NO_INDEPENDENT_P856_HOST_BINDING",
        "candidate_url":url,
        "candidate_host":host,
        "queries":queries,
        "observations":observations[:32],
        "authority_status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "relevance_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }


def bind_discovery(discovery,timeout=20,max_candidates=12):
    if not isinstance(discovery,dict):
        raise ValueError("DISCOVERY_OBJECT_REQUIRED")
    candidates=discovery.get("candidates") or []
    if not isinstance(candidates,list):
        raise ValueError("CANDIDATES_LIST_REQUIRED")
    objective=_canon(discovery.get("objective") or discovery.get("query"))
    results=[]
    for candidate in candidates[:max(1,min(int(max_candidates),20))]:
        try:
            results.append(bind_candidate(candidate,timeout=timeout))
        except Exception as exc:
            results.append({
                "schema":SCHEMA,
                "status":"AUTHORITY_UNRESOLVED",
                "reason":type(exc).__name__+":"+str(exc)[:300],
                "authority_status":"UNVERIFIED",
                "primary_source_status":"UNVERIFIED",
                "relevance_status":"UNVERIFIED",
                "evidence_sufficiency_status":"UNVERIFIED",
                "model_dependency_count":0,
                "incremental_spend_usd":0,
            })
    verified=[x for x in results if x.get("status")=="AUTHORITY_IDENTITY_VERIFIED"]
    return {
        "schema":SCHEMA,
        "status":"AUTHORITY_BOUND_CANDIDATES_AVAILABLE" if verified else "AUTHORITY_UNRESOLVED",
        "objective":objective,
        "objective_sha256":hashlib.sha256(objective.encode("utf-8")).hexdigest() if objective else None,
        "input_candidate_count":len(candidates),
        "verified_candidate_count":len(verified),
        "verified_candidates":verified,
        "results":results,
        "authority_claim_scope":"HOST_TO_DECLARED_OFFICIAL_WEBSITE_IDENTITY_ONLY",
        "primary_source_verification":"NOT_PERFORMED",
        "relevance_verification":"NOT_PERFORMED",
        "evidence_sufficiency_verification":"NOT_PERFORMED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }


def run(args,root):
    args=dict(args or {})
    root=pathlib.Path(root).resolve()
    discovery_path=str(args.get("discovery_path") or "").strip()
    if not discovery_path:
        raise ValueError("DISCOVERY_PATH_REQUIRED")
    path=(root/discovery_path).resolve()
    if path==root or root not in path.parents or not path.is_file():
        raise ValueError("DISCOVERY_PATH_INVALID")
    discovery=json.loads(path.read_text(encoding="utf-8"))
    result=bind_discovery(
        discovery,
        timeout=int(args.get("timeout") or 20),
        max_candidates=int(args.get("max_candidates") or 12),
    )
    output_path=str(args.get("output_path") or "").strip()
    if output_path:
        out=(root/output_path).resolve()
        if out==root or root not in out.parents:
            raise ValueError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        result["output_path"]=str(out.relative_to(root)).replace("\\","/")
    result["output_verified"]=bool(
        result.get("status")=="AUTHORITY_BOUND_CANDIDATES_AVAILABLE"
        and int(result.get("verified_candidate_count") or 0)>0
        and (not output_path or bool(result.get("output_path")))
    )
    return result
