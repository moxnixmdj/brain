#!/usr/bin/env python3
"""End-to-end frozen real-target hidden-witness retrieval arena.

Unlike mechanism-only torture tests, this arena has actual answer-key identities:
13 public repositories that Brain previously discovered during real residual work,
pinned at exact Git commits.  The retriever receives behavioral queries and
masked candidate surfaces, then must rank the true target.

This is deliberately a finite replay arena, not an open-world completeness
proof and not a substitute for live provider recall measurement.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RETRIEVAL_REAL_HIDDEN_WITNESS_ARENA_V1"
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

PROFILES = (
    "METADATA_ONLY",
    "NO_DESCRIPTION",
    "NO_IDENTITY",
    "STRUCTURAL_ONLY",
)

ROUTES = (
    "METADATA",
    "STRUCTURE",
    "HYBRID",
)

STOP = {
    "the","a","an","and","or","to","of","for","from","in","on","with","using",
    "into","main","repository","open","source","library","python","model","models",
}


def canon(x: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(x or "")).strip().split())


def tokens(x: Any) -> list[str]:
    out=[]
    prepared=re.sub(r"(?<=[a-z])(?=[A-Z])"," ",canon(x))
    prepared=re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])"," ",prepared)
    for raw in TOKEN.findall(prepared):
        t=raw.casefold()
        if len(t)<2 or t in STOP:
            continue
        if t not in out:
            out.append(t)
    return out


def _stem(token: str) -> str:
    t=token.casefold()
    for suffix in ("ization","isation","ational","ation","ingly","edly","izer","iser","ing","ers","er","ies","es","s"):
        if t.endswith(suffix) and len(t)-len(suffix)>=3:
            base=t[:-len(suffix)]
            if suffix=="ies":
                base += "y"
            return base
    return t


def features(x: Any) -> list[str]:
    out=[]
    for tok in tokens(x):
        for feat in (tok,"="+_stem(tok)):
            if feat not in out:
                out.append(feat)
        compact=re.sub(r"[^0-9a-z]+","",tok)
        if len(compact)>=3:
            for i in range(len(compact)-2):
                gram="~"+compact[i:i+3]
                if gram not in out:
                    out.append(gram)
    return out


def load_catalog(root: Path) -> dict[str, Any]:
    p=root/"canonical/governance/RETRIEVAL_REAL_HIDDEN_WITNESS_CATALOG_V1.json"
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("schema")!="PROJECT_BRAIN_RETRIEVAL_REAL_HIDDEN_WITNESS_CATALOG_V1":
        raise ValueError("CATALOG_SCHEMA_INVALID")
    rows=obj.get("targets")
    if not isinstance(rows,list) or len(rows)<10:
        raise ValueError("CATALOG_TOO_SMALL")
    ids=[str(x.get("id")) for x in rows if isinstance(x,Mapping)]
    if len(ids)!=len(set(ids)):
        raise ValueError("DUPLICATE_TARGET_ID")
    return obj


def load_content_fingerprints(root: Path) -> dict[str, Mapping[str, Any]]:
    p=root/"canonical/governance/RETRIEVAL_REAL_CONTENT_FINGERPRINTS_V1.json"
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("schema")!="PROJECT_BRAIN_RETRIEVAL_REAL_CONTENT_FINGERPRINTS_V1":
        raise ValueError("CONTENT_FINGERPRINT_SCHEMA_INVALID")
    rows=obj.get("fingerprints")
    if not isinstance(rows,dict):
        raise ValueError("CONTENT_FINGERPRINTS_MAPPING_REQUIRED")
    return rows


def load_tree_fingerprints(root: Path) -> dict[str, Mapping[str, Any]]:
    p=root/"canonical/governance/RETRIEVAL_REAL_TREE_FINGERPRINTS_V1.json"
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("schema")!="PROJECT_BRAIN_RETRIEVAL_REAL_TREE_FINGERPRINTS_V1":
        raise ValueError("TREE_FINGERPRINT_SCHEMA_INVALID")
    rows=obj.get("fingerprints")
    if not isinstance(rows,dict):
        raise ValueError("TREE_FINGERPRINTS_MAPPING_REQUIRED")
    return rows


def _identity_terms(row: Mapping[str, Any]) -> set[str]:
    repo=canon(row.get("repository"))
    name=repo.rsplit("/",1)[-1] if repo else ""
    parts=set(tokens(name.replace("-"," ").replace("_"," ")))
    compact=re.sub(r"[^0-9a-z]+","",name.casefold())
    if compact:
        parts.add(compact)
    return parts


def _redact_identity(text: str, row: Mapping[str, Any]) -> str:
    blocked=_identity_terms(row)
    kept=[]
    for raw in TOKEN.findall(canon(text)):
        t=raw.casefold()
        compact=re.sub(r"[^0-9a-z]+","",t)
        if t in blocked or compact in blocked:
            continue
        kept.append(raw)
    return " ".join(kept)


def surface_text(
    row: Mapping[str, Any], *, profile: str, route: str,
    tree_tokens: Sequence[str] | None=None,
    content_tokens: Sequence[str] | None=None,
) -> str:
    if profile not in PROFILES or route not in ROUTES:
        raise ValueError("ARENA_PROFILE_OR_ROUTE_INVALID")
    description=canon(row.get("description"))
    topics=" ".join(canon(x) for x in (row.get("topics") or []))
    paths=" ".join(canon(x) for x in (row.get("root_paths") or []))
    deep_tree=" ".join(canon(x) for x in (tree_tokens or []))
    deep_content=" ".join(canon(x) for x in (content_tokens or []))
    language=canon(row.get("language"))
    # Repository/id fields are never scored. NO_IDENTITY additionally redacts
    # project-name tokens that leak through descriptions/topics/path names.
    if profile=="METADATA_ONLY":
        paths=""
    elif profile=="NO_DESCRIPTION":
        description=""
    elif profile=="STRUCTURAL_ONLY":
        description=""; topics=""
    metadata=" ".join(x for x in (description,topics,language) if x)
    structure=" ".join(x for x in (paths,deep_tree,deep_content,language) if x)
    if profile=="NO_IDENTITY":
        metadata=_redact_identity(metadata,row)
        structure=_redact_identity(structure,row)
    if route=="METADATA":
        return metadata
    if route=="STRUCTURE":
        return structure
    return " ".join(x for x in (metadata,structure) if x)


def _idf(doc_tokens: Sequence[set[str]]) -> dict[str,float]:
    n=max(1,len(doc_tokens))
    df=Counter(tok for doc in doc_tokens for tok in doc)
    return {tok: math.log(1.0+(n-f+0.5)/(f+0.5)) for tok,f in df.items()}


def _score(query: str, doc: str, idf: Mapping[str,float]) -> float:
    q=features(query)
    d=features(doc)
    if not q or not d:
        return 0.0
    dc=Counter(d)
    score=0.0
    for feat in q:
        if feat in dc:
            # Whole lexical features carry full weight; stems and character
            # trigrams are generic fuzzy bridges with lower authority.
            weight=1.0
            if feat.startswith("="):
                weight=0.72
            elif feat.startswith("~"):
                weight=0.30
            score += weight*float(idf.get(feat,1.0))*(1.0+math.log1p(dc[feat]))
    qlex=tokens(query)
    cd=canon(doc).casefold()
    for size in (2,3):
        for i in range(max(0,len(qlex)-size+1)):
            phrase=" ".join(qlex[i:i+size])
            if phrase and phrase in cd:
                score += 0.35*size
    qwhole=[x for x in q if not x.startswith(("=","~"))]
    coverage=sum(1 for tok in qwhole if tok in dc)/len(qwhole) if qwhole else 0.0
    return score*(0.75+0.5*coverage)


def rank(
    catalog: Sequence[Mapping[str,Any]],
    query: str,
    *,
    profile: str,
    route: str,
    tree_fingerprints: Mapping[str,Mapping[str,Any]] | None=None,
    content_fingerprints: Mapping[str,Mapping[str,Any]] | None=None,
) -> list[dict[str,Any]]:
    tree_fingerprints=tree_fingerprints or {}
    content_fingerprints=content_fingerprints or {}
    docs=[
        surface_text(
            x,profile=profile,route=route,
            tree_tokens=(tree_fingerprints.get(str(x.get("id"))) or {}).get("tree_tokens") or [],
            content_tokens=(content_fingerprints.get(str(x.get("id"))) or {}).get("content_tokens") or [],
        )
        for x in catalog
    ]
    idf=_idf([set(features(x)) for x in docs])
    rows=[]
    for target,doc in zip(catalog,docs):
        rows.append({
            "id":target["id"],
            "score":_score(query,doc,idf),
        })
    rows.sort(key=lambda x:(-x["score"],str(x["id"])))
    return rows


def evaluate(root: Path) -> dict[str,Any]:
    catalog_obj=load_catalog(root)
    catalog=catalog_obj["targets"]
    tree_fingerprints=load_tree_fingerprints(root)
    content_fingerprints=load_content_fingerprints(root)
    for target in catalog:
        fp=tree_fingerprints.get(str(target.get("id")))
        if not isinstance(fp,Mapping):
            raise ValueError("TREE_FINGERPRINT_MISSING:"+str(target.get("id")))
        if fp.get("repository")!=target.get("repository") or fp.get("commit")!=target.get("commit"):
            raise ValueError("TREE_FINGERPRINT_TARGET_DRIFT:"+str(target.get("id")))
        if fp.get("truncated") is not False:
            raise ValueError("TREE_FINGERPRINT_TRUNCATED:"+str(target.get("id")))
    for target_id,cfp in content_fingerprints.items():
        target=next((x for x in catalog if str(x.get("id"))==str(target_id)),None)
        if not isinstance(target,Mapping):
            raise ValueError("CONTENT_FINGERPRINT_UNKNOWN_TARGET:"+str(target_id))
        tfp=tree_fingerprints[str(target_id)]
        if cfp.get("repository")!=target.get("repository") or cfp.get("commit")!=target.get("commit"):
            raise ValueError("CONTENT_FINGERPRINT_TARGET_DRIFT:"+str(target_id))
        if int(tfp.get("path_count") or 0)>8:
            raise ValueError("CONTENT_FINGERPRINT_SELECTION_RULE_VIOLATION:"+str(target_id))
    cases=[]
    route_hits={route:set() for route in ROUTES}
    route_top3={route:set() for route in ROUTES}
    latencies={route:[] for route in ROUTES}

    for profile in PROFILES:
        for target in catalog:
            queries=target.get("behavioral_queries") or []
            for qi,query in enumerate(queries):
                case_id=f"{profile}:{target['id']}:Q{qi}"
                route_results={}
                for route in ROUTES:
                    started=time.perf_counter_ns()
                    ranked=rank(
                        catalog,str(query),profile=profile,route=route,
                        tree_fingerprints=tree_fingerprints,
                        content_fingerprints=content_fingerprints,
                    )
                    elapsed=(time.perf_counter_ns()-started)/1_000_000.0
                    latencies[route].append(elapsed)
                    ids=[x["id"] for x in ranked]
                    expected=target["id"]
                    r1=bool(ids and ids[0]==expected)
                    r3=expected in ids[:3]
                    rank_pos=(ids.index(expected)+1) if expected in ids else None
                    route_results[route]={
                        "top1":r1,"top3":r3,"rank":rank_pos,
                        "top_candidates":ranked[:3],
                        "top_ids":[x["id"] for x in ranked[:5]],
                    }
                    if r1: route_hits[route].add(case_id)
                    if r3: route_top3[route].add(case_id)
                pooled={}
                for k in (1,3,5):
                    pool=set()
                    for route in ROUTES:
                        pool.update(route_results[route]["top_ids"][:k])
                    pooled[str(k)]={
                        "hit":target["id"] in pool,
                        "candidate_pool_size":len(pool),
                    }
                cases.append({
                    "case_id":case_id,
                    "profile":profile,
                    "target_id":target["id"],
                    "query":query,
                    "results":route_results,
                    "pooled":pooled,
                })

    n=len(cases)
    metrics={}
    for route in ROUTES:
        top1=len(route_hits[route])/n if n else 0.0
        top3=len(route_top3[route])/n if n else 0.0
        metrics[route]={
            "case_count":n,
            "top1_recall":top1,
            "top3_recall":top3,
            "mean_local_ranking_latency_ms":statistics.fmean(latencies[route]) if latencies[route] else 0.0,
            "p95_local_ranking_latency_ms":sorted(latencies[route])[max(0,math.ceil(0.95*len(latencies[route]))-1)] if latencies[route] else 0.0,
        }

    # Conditional marginal recovery. This is empirical on this arena, and does
    # not assume source independence.
    order=list(ROUTES)
    recovered=set()
    conditional=[]
    for route in order:
        misses_before={x["case_id"] for x in cases}-recovered
        new_hits=route_hits[route] & misses_before
        denom=len(misses_before)
        conditional.append({
            "route":route,
            "misses_before":denom,
            "new_top1_hits":len(new_hits),
            "conditional_top1_recovery":len(new_hits)/denom if denom else 0.0,
        })
        recovered |= route_hits[route]

    correlations=[]
    for i,a in enumerate(ROUTES):
        for b in ROUTES[i+1:]:
            union=route_hits[a]|route_hits[b]
            inter=route_hits[a]&route_hits[b]
            correlations.append({
                "route_a":a,"route_b":b,
                "top1_hit_jaccard":len(inter)/len(union) if union else 0.0,
                "a_unique_top1":len(route_hits[a]-route_hits[b]),
                "b_unique_top1":len(route_hits[b]-route_hits[a]),
            })

    pooled_metrics={}
    for k in (1,3,5):
        key=str(k)
        hits=sum(1 for x in cases if x["pooled"][key]["hit"])
        sizes=[x["pooled"][key]["candidate_pool_size"] for x in cases]
        pooled_metrics[key]={
            "case_count":n,
            "recall":hits/n if n else 0.0,
            "misses":n-hits,
            "mean_candidate_pool_size":statistics.fmean(sizes) if sizes else 0.0,
            "max_candidate_pool_size":max(sizes) if sizes else 0,
        }

    profile_metrics={}
    for profile in PROFILES:
        subset=[x for x in cases if x["profile"]==profile]
        m=len(subset)
        profile_metrics[profile]={}
        for route in ROUTES:
            t1=sum(1 for x in subset if x["results"][route]["top1"])
            t3=sum(1 for x in subset if x["results"][route]["top3"])
            profile_metrics[profile][route]={
                "case_count":m,
                "top1_recall":t1/m if m else 0.0,
                "top3_recall":t3/m if m else 0.0,
            }

    worst=sorted(
        (
            {
                "case_id":x["case_id"],
                "target_id":x["target_id"],
                "profile":x["profile"],
                "query":x["query"],
                "hybrid_rank":x["results"]["HYBRID"]["rank"],
                "hybrid_top_candidates":x["results"]["HYBRID"]["top_candidates"],
            }
            for x in cases
        ),
        key=lambda x:(-(x["hybrid_rank"] or 9999),x["case_id"]),
    )[:24]

    return {
        "schema":SCHEMA,
        "status":"MEASURED__FINITE_REAL_TARGET_REPLAY",
        "catalog_target_count":len(catalog),
        "query_independent_tree_fingerprint_count":len(tree_fingerprints),
        "bounded_full_content_fingerprint_count":len(content_fingerprints),
        "case_count":n,
        "profiles":list(PROFILES),
        "routes":list(ROUTES),
        "metrics":metrics,
        "profile_metrics":profile_metrics,
        "monotonic_pooled_candidate_metrics":pooled_metrics,
        "conditional_top1_recovery":conditional,
        "route_top1_correlation":correlations,
        "route_top1_hit_case_ids":{route:sorted(route_hits[route]) for route in ROUTES},
        "route_top3_hit_case_ids":{route:sorted(route_top3[route]) for route in ROUTES},
        "hybrid_top1_misses":n-len(route_hits["HYBRID"]),
        "hybrid_top3_misses":n-len(route_top3["HYBRID"]),
        "worst_hybrid_cases":worst,
        "open_world_completeness_claim":False,
        "external_provider_recall_measured":False,
        "candidate_identity_leakage_allowed":False,
        "hard_rules":[
            "REAL_PINNED_TARGET_IDENTITIES_ARE_ANSWER_KEY_ONLY",
            "NO_REPOSITORY_NAME_OR_TARGET_ID_IN_SCORED_CANDIDATE_TEXT",
            "ARENA_FAILURES_ARE_REPORTED_NOT_NORMALIZED_AWAY",
            "CONDITIONAL_RECOVERY_IS_EMPIRICAL_ON_THIS_ARENA_NOT_AN_INDEPENDENCE_ASSUMPTION",
            "LOCAL_RANKING_LATENCY_IS_NOT_NETWORK_PROVIDER_LATENCY",
            "MONOTONIC_POOL_RECALL_MEASURES_DISCOVERY_BEFORE_DOWNSTREAM_VERIFICATION",
            "FUZZY_STEM_AND_CHARACTER_NGRAM_MATCHING_IS_GENERIC_AND_NOT_TARGET_SPECIFIC",
            "NO_FINITE_ARENA_TO_OPEN_WORLD_COMPLETENESS_INFERENCE",
        ],
    }


def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=evaluate(root)
    print(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
