#!/usr/bin/env python3
"""General exact-match retrieval synthesizer extending V1 with a bounded fallback.

The fallback broadens question-form coverage, not correctness authority. It uses
only deterministic search/fetch/extraction and never reads gold or calls a model.
"""
from __future__ import annotations
import hashlib
from collections import Counter,defaultdict
from typing import Any,Callable,Mapping
from canonical.runtime import hle_exact_retrieval_extract_v1 as v1
SCHEMA='PROJECT_BRAIN_HLE_EXACT_RETRIEVAL_EXTRACT_V2'

def propose(*,task_id:str,question:str,has_nonempty_image_payload:bool=False,
            search_fn:Callable[...,Mapping[str,Any]]|None=None,
            fetch_fn:Callable[...,Mapping[str,Any]]|None=None,
            search_limit:int=12,max_fetches:int=10)->dict[str,Any]:
    kind=v1.classify(question)
    if kind is not None:
        out=v1.propose(task_id=task_id,question=question,
            has_nonempty_image_payload=has_nonempty_image_payload,
            search_fn=search_fn,fetch_fn=fetch_fn,
            search_limit=search_limit,max_fetches=max_fetches)
        out['schema']=SCHEMA;out['fallback_general_form']=False
        return out
    if has_nonempty_image_payload:
        return {'schema':SCHEMA,'status':'FAIL_CLOSED__IMAGE_SEMANTICS_UNSUPPORTED',
                'candidate_answer':None,'candidate_answer_authority':False,
                'external_model_calls':0,'model_dependency_count':0,'gold_accessed':False,
                'fallback_general_form':True,'terminal_authority':False}
    if search_fn is None or fetch_fn is None:
        from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
        search_fn=search_fn or tools.search_web;fetch_fn=fetch_fn or tools.fetch_web
    query=v1._query(question)
    try: sr=search_fn(query,limit=search_limit)
    except Exception as exc: sr={'status':'FAILED','results':[],'error':type(exc).__name__}
    urls=[];hosts=set()
    for row in sr.get('results') or []:
        if not isinstance(row,Mapping):continue
        u=str(row.get('url') or '');h=v1._host(u)
        if not u or u in urls:continue
        if h and h not in hosts:urls.append(u);hosts.add(h)
        if len(urls)>=max_fetches:break
    if len(urls)<max_fetches:
        for row in sr.get('results') or []:
            if not isinstance(row,Mapping):continue
            u=str(row.get('url') or '')
            if u and u not in urls:urls.append(u)
            if len(urls)>=max_fetches:break
    support=Counter();host_support=defaultdict(set)
    for u in urls:
        try:fr=fetch_fn(u,max_bytes=600000)
        except Exception:continue
        if fr.get('status')!='PASS':continue
        host=v1._host(str(fr.get('final_url') or fr.get('url') or u))
        text=v1._plain(str(fr.get('body_excerpt') or ''))
        for w in v1._windows(text):
            ss=v1._sentence_score(question,w)
            if ss<0.75:continue
            for cand in v1._extract('GENERAL',w):
                if cand.casefold() in v1._canon(question).casefold():continue
                val=ss*(1.0+min(2.0,len(cand)/40.0))
                support[cand]+=val
                if host:host_support[cand].add(host)
    if not support:
        return {'schema':SCHEMA,'status':'NO_CANDIDATE','candidate_answer':None,
                'candidate_answer_authority':False,'fallback_general_form':True,
                'query_sha256':hashlib.sha256(query.encode()).hexdigest(),
                'external_model_calls':0,'model_dependency_count':0,'gold_accessed':False,
                'terminal_authority':False}
    ranked=sorted(support,key=lambda c:(-(support[c]+1.5*min(len(host_support[c]),3)),c.casefold(),c))
    chosen=ranked[0];second=ranked[1] if len(ranked)>1 else None
    score=support[chosen]+1.5*min(len(host_support[chosen]),3)
    second_score=(support[second]+1.5*min(len(host_support[second]),3)) if second else 0.0
    return {'schema':SCHEMA,'status':'CANDIDATE_GENERATED','task_id':task_id,
            'question_sha256':hashlib.sha256(question.encode()).hexdigest(),
            'question_kind':'GENERAL','fallback_general_form':True,
            'candidate_answer':chosen,'candidate_answer_authority':False,
            'candidate_score':score,'runner_up_margin':score-second_score,
            'independent_support_host_count':len(host_support[chosen]),
            'external_model_calls':0,'model_dependency_count':0,'gold_accessed':False,
            'incremental_spend_usd':0,'terminal_authority':False,
            'hard_nonclaim':'GENERAL_RETRIEVAL_FALLBACK_BROADENS_PROPOSAL_COVERAGE_NOT_CORRECTNESS_AUTHORITY'}
