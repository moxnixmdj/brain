#!/usr/bin/env python3
"""Deterministic model-independent lexical objective relevance ranking.

Uses a compact BM25 implementation over candidate title/snippet text. The
capability proves only lexical relevance ranking to the stated objective.
It does not prove semantic entailment, factual correctness, primary-source
status, authority, or evidence sufficiency.
"""
from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import re

SCHEMA="PROJECT_BRAIN_OBJECTIVE_RELEVANCE_BM25_V1"
WORD_RE=re.compile(r"[a-z0-9]+")
GENERIC={
    "a","an","and","are","as","at","be","by","for","from","how","in","is","it",
    "of","on","or","that","the","this","to","was","were","what","when","where",
    "which","who","why","with","whether","determine","find","compare","using",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(value):
    return [x for x in WORD_RE.findall(_canon(value).lower()) if len(x)>1 and x not in GENERIC]


def _focus(objective):
    path=pathlib.Path(__file__).resolve().with_name("research_query_focus.py")
    spec=importlib.util.spec_from_file_location("project_brain_research_query_focus_relevance",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RESEARCH_QUERY_FOCUS_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result=module.focus(objective)
    if result.get("status")!="FOCUSED":
        return None
    return result

def _candidate_text(candidate):
    c=dict(candidate or {})
    title=_canon(c.get("title"))
    snippet=_canon(c.get("snippet"))
    record_title=_canon(c.get("record_title"))
    # Repeating titles is a standard field-weight approximation while keeping
    # one simple BM25 corpus and no learned parameters.
    return " ".join(x for x in (title,title,record_title,snippet) if x)

def _minimum_matched_terms(query_token_count):
    """Scale lexical admission with objective complexity, without score tuning.

    A one-term objective must match that term. Longer objectives require a
    sublinear number of distinct focused-query terms: ceil(sqrt(N)). This
    rejects incidental one/two-token overlap on broad objectives while
    avoiding a task- or provider-specific BM25 score cutoff.
    """
    n=max(1,int(query_token_count))
    return min(n,max(1,int(math.ceil(math.sqrt(n)))))

def _bm25_scores(query_tokens, docs, k1=1.5, b=0.75):
    n=len(docs)
    if n==0:
        return []
    lengths=[len(x) for x in docs]
    avgdl=(sum(lengths)/n) if n else 0.0
    if avgdl<=0:
        return [0.0]*n
    dfs={}
    for doc in docs:
        for term in set(doc):
            dfs[term]=dfs.get(term,0)+1
    q=list(dict.fromkeys(query_tokens))
    out=[]
    for doc,dl in zip(docs,lengths):
        tf={}
        for term in doc:
            tf[term]=tf.get(term,0)+1
        score=0.0
        contributions={}
        for term in q:
            f=tf.get(term,0)
            if not f:
                continue
            df=dfs.get(term,0)
            # Robertson/Sparck Jones-style positive IDF variant.
            idf=math.log(1.0+(n-df+0.5)/(df+0.5))
            denom=f+k1*(1.0-b+b*dl/avgdl)
            part=idf*(f*(k1+1.0)/denom)
            score+=part
            contributions[term]=part
        out.append((score,contributions))
    return out

def rank(objective,candidates,limit=None):
    objective=_canon(objective)
    base={
        "schema":SCHEMA,
        "objective":objective or None,
        "relevance_claim_scope":"LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY",
        "semantic_entailment_status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"OBJECTIVE_REQUIRED","ranked_candidates":[]}
    if not isinstance(candidates,list) or not candidates:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"CANDIDATES_REQUIRED","ranked_candidates":[]}
    focus=_focus(objective)
    if not focus:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"RESEARCH_QUERY_FOCUS_UNRESOLVED","ranked_candidates":[]}
    q=_tokens(focus.get("query"))
    if not q:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"NO_DISCRIMINATIVE_OBJECTIVE_TOKENS","ranked_candidates":[]}

    docs=[_tokens(_candidate_text(c)) for c in candidates]
    scored=_bm25_scores(q,docs)
    required_matches=_minimum_matched_terms(len(q))
    rows=[]
    for index,(candidate,(score,parts)) in enumerate(zip(candidates,scored)):
        matched=sorted(parts)
        admitted=score>0 and len(matched)>=required_matches
        rows.append({
            "original_index":index,
            "candidate":candidate,
            "lexical_relevance_score":round(float(score),12),
            "matched_terms":matched,
            "matched_term_count":len(matched),
            "query_token_count":len(q),
            "query_term_coverage":round((len(matched)/len(q)) if q else 0.0,12),
            "minimum_matched_terms_for_admission":required_matches,
            "lexical_admission_status":(
                "ADMITTED" if admitted
                else "REJECTED_INSUFFICIENT_QUERY_TERM_COVERAGE"
                if score>0
                else "REJECTED_NO_LEXICAL_OBJECTIVE_EVIDENCE"
            ),
            "term_contributions":{k:round(float(v),12) for k,v in sorted(parts.items())},
        })
    rows.sort(key=lambda x:(-x["lexical_relevance_score"],x["original_index"]))
    positive=[x for x in rows if x["lexical_relevance_score"]>0]
    admitted=[x for x in rows if x["lexical_admission_status"]=="ADMITTED"]
    if not positive:
        return {
            **base,
            "status":"RELEVANCE_UNRESOLVED",
            "reason":"NO_LEXICAL_OBJECTIVE_EVIDENCE",
            "verification_method":"DETERMINISTIC_BM25_WITH_QUERY_COMPLEXITY_SCALED_TERM_COVERAGE_ADMISSION",
            "query_tokens":q,
            "minimum_matched_terms_for_admission":required_matches,
            "ranked_candidates":rows,
            "output_verified":True,
        }
    if not admitted:
        return {
            **base,
            "status":"RELEVANCE_UNRESOLVED",
            "reason":"INSUFFICIENT_QUERY_TERM_COVERAGE",
            "verification_method":"DETERMINISTIC_BM25_WITH_QUERY_COMPLEXITY_SCALED_TERM_COVERAGE_ADMISSION",
            "query_tokens":q,
            "query_focus":focus,
            "candidate_count":len(candidates),
            "positive_relevance_count":len(positive),
            "admitted_candidate_count":0,
            "minimum_matched_terms_for_admission":required_matches,
            "ranked_candidates":rows,
            "output_verified":True,
        }
    if limit is not None:
        rows=rows[:max(1,min(int(limit),len(rows)))]
    return {
        **base,
        "status":"LEXICAL_RELEVANCE_RANKED",
        "verification_method":"DETERMINISTIC_BM25_WITH_QUERY_COMPLEXITY_SCALED_TERM_COVERAGE_ADMISSION",
        "query_tokens":q,
        "query_focus":focus,
        "candidate_count":len(candidates),
        "positive_relevance_count":len(positive),
        "admitted_candidate_count":len(admitted),
        "minimum_matched_terms_for_admission":required_matches,
        "ranked_candidates":rows,
        "top_candidate_original_index":admitted[0]["original_index"],
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
        raise ValueError("RELEVANCE_INPUT_MISSING")
    data=json.loads(inp.read_text(encoding="utf-8"))
    objective=_canon(data.get("objective") or args.get("objective"))
    candidates=data.get("candidates")
    if candidates is None and isinstance(data.get("discovery"),dict):
        candidates=data["discovery"].get("candidates")
    result=rank(objective,candidates or [],limit=args.get("limit"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="LEXICAL_RELEVANCE_RANKED"
    return result
