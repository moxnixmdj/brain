#!/usr/bin/env python3
"""Brain-owned deterministic retrieval extractor for HLE exact-match candidates.

No model calls. No gold access. The module emits fallible proposals only and
fails closed for multimodal tasks or unsupported question forms.
"""
from __future__ import annotations

import hashlib, html, re, unicodedata, urllib.parse
from collections import Counter, defaultdict
from typing import Any, Callable, Mapping

SCHEMA="PROJECT_BRAIN_HLE_EXACT_RETRIEVAL_EXTRACT_V1"
_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_TAG=re.compile(r"<[^>]+>")
_SCRIPT=re.compile(r"<(?:script|style)\b.*?</(?:script|style)>",re.I|re.S)
_YEAR=re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)")
_NUMBER=re.compile(r"(?<![A-Za-z0-9])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:e[-+]?\d+)?(?![A-Za-z0-9])",re.I)
_QUOTED=re.compile(r'["“‘\']([^"”’\']{2,120})["”’\']')
_CAPSPAN=re.compile(r"\b(?:[A-Z][\w'’.-]*(?:\s+|$)){1,6}")
_COPULA=re.compile(r"\b(?:is|are|was|were|called|named|known as|termed|designated)\s+([^.;:!?]{2,120})",re.I)
_STOP={
'a','an','and','are','as','at','be','been','being','but','by','can','could','did','do','does','for','from','had','has','have','how','if','in','into','is','it','may','might','must','of','on','or','should','that','the','their','then','there','these','this','those','to','was','were','what','when','where','which','who','whom','whose','why','will','with','would','answer','question','find','determine','identify','name','called','known','term','title','value','number','year'
}

def _canon(v:Any)->str:
    return " ".join(unicodedata.normalize('NFKC',str(v or '')).strip().split())

def _tokens(v:Any)->list[str]:
    out=[]
    for raw in _WORD.findall(_canon(v)):
        t=raw.casefold().strip('-/')
        if len(t)<2 or t in _STOP: continue
        if t not in out: out.append(t)
    return out

def _plain(raw:str)->str:
    x=_SCRIPT.sub(' ',str(raw or ''))
    x=_TAG.sub(' ',x)
    return _canon(html.unescape(x))

def _host(url:str)->str:
    try:return (urllib.parse.urlparse(url).hostname or '').lower()
    except:return ''

def _tail(q:str)->str:
    x=_canon(q)
    parts=[p.strip() for p in re.split(r'(?<=[.!?])\s+',x) if p.strip()]
    return parts[-1] if parts else x

def classify(question:str)->str|None:
    t=_tail(question)
    if re.search(r'\b(?:what|which)\s+year\b|\bin what year\b|\bwhen did\b|\bwhen was\b',t,re.I): return 'YEAR'
    if re.search(r'\bwho\b',t,re.I): return 'PERSON'
    if re.search(r'\b(?:name|term|title|author|inventor|discoverer|species|gene|protein|enzyme|theorem|called|known as)\b',t,re.I): return 'TERM'
    if re.search(r'\b(?:how many|how much|what (?:is|was) the (?:value|number|count|mass|length|distance|frequency|wavelength|energy|probability|ratio|percentage|percent))\b',t,re.I): return 'NUMBER'
    if re.search(r'^\s*(?:what|which)\b',t,re.I): return 'SHORT_TEXT'
    return None

def _query(question:str)->str:
    q=_canon(question)
    quoted=[x.strip() for x in _QUOTED.findall(q) if 2<=len(x.strip())<=100]
    toks=_tokens(q)
    informative=sorted(toks,key=lambda x:(-len(x),x))[:18]
    pieces=[]
    for x in quoted[:2]+informative:
        if x.casefold() not in {p.casefold() for p in pieces}: pieces.append(x)
    return ' '.join(pieces)[:700]

def _windows(text:str)->list[str]:
    rows=[x.strip() for x in re.split(r'(?<=[.!?;])\s+|\n+',text) if x.strip()]
    out=[]
    for i in range(min(len(rows),180)):
        out.append(' '.join(rows[max(0,i-1):min(len(rows),i+2)])[:1800])
    return out or [text[:1800]]

def _sentence_score(question:str,sentence:str)->float:
    qt=_tokens(question)
    st=set(_tokens(sentence))
    if not qt:return 0.0
    long=sorted(qt,key=lambda x:(-len(x),x))[:28]
    return 5.0*sum(1 for t in long if t in st)/len(long)

def _clean_candidate(x:str,kind:str)->str|None:
    x=_canon(x).strip(' ,;:.()[]{}')
    if not x or len(x)>120:return None
    if kind=='YEAR': return x if _YEAR.fullmatch(x) else None
    if kind=='NUMBER':
        if not _NUMBER.fullmatch(x):return None
        return x.replace(',','')
    if len(x.split())>12:return None
    if x.casefold() in _STOP:return None
    return x

def _extract(kind:str,sentence:str)->list[str]:
    c=[]
    if kind=='YEAR': c += _YEAR.findall(sentence)
    elif kind=='NUMBER': c += _NUMBER.findall(sentence)
    else:
        c += _QUOTED.findall(sentence)
        for m in _COPULA.finditer(sentence):
            frag=m.group(1)
            frag=re.split(r'\b(?:because|whereas|while|although|which|that)\b',frag,maxsplit=1,flags=re.I)[0]
            words=frag.split()[:10]
            if words:c.append(' '.join(words))
        c += [m.group(0).strip() for m in _CAPSPAN.finditer(sentence)]
    out=[]
    for x in c:
        y=_clean_candidate(str(x),kind)
        if y and y not in out:out.append(y)
    return out

def propose(*,task_id:str,question:str,has_nonempty_image_payload:bool=False,
            search_fn:Callable[...,Mapping[str,Any]]|None=None,
            fetch_fn:Callable[...,Mapping[str,Any]]|None=None,
            search_limit:int=12,max_fetches:int=10)->dict[str,Any]:
    if has_nonempty_image_payload:
        return {'schema':SCHEMA,'status':'FAIL_CLOSED__IMAGE_SEMANTICS_UNSUPPORTED','candidate_answer':None,'candidate_answer_authority':False,'external_model_calls':0,'gold_accessed':False}
    kind=classify(question)
    if kind is None:
        return {'schema':SCHEMA,'status':'FAIL_CLOSED__QUESTION_FORM_UNSUPPORTED','candidate_answer':None,'candidate_answer_authority':False,'external_model_calls':0,'gold_accessed':False}
    if search_fn is None or fetch_fn is None:
        from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
        search_fn=search_fn or tools.search_web
        fetch_fn=fetch_fn or tools.fetch_web
    query=_query(question)
    try: sr=search_fn(query,limit=search_limit)
    except Exception as exc: sr={'status':'FAILED','results':[],'error':type(exc).__name__}
    urls=[]; seen=set(); hosts=set()
    for row in sr.get('results') or []:
        if not isinstance(row,Mapping):continue
        u=str(row.get('url') or ''); h=_host(u)
        if not u or u in seen:continue
        seen.add(u)
        if h and h not in hosts:
            urls.append(u);hosts.add(h)
        if len(urls)>=max_fetches:break
    if len(urls)<max_fetches:
        for row in sr.get('results') or []:
            if not isinstance(row,Mapping):continue
            u=str(row.get('url') or '')
            if u and u not in urls: urls.append(u)
            if len(urls)>=max_fetches:break
    support=Counter(); host_support=defaultdict(set); evidence=[]
    for u in urls:
        try: fr=fetch_fn(u,max_bytes=600000)
        except Exception:continue
        if fr.get('status')!='PASS':continue
        final=str(fr.get('final_url') or fr.get('url') or u); host=_host(final)
        text=_plain(str(fr.get('body_excerpt') or ''))
        if not text:continue
        for w in _windows(text):
            ss=_sentence_score(question,w)
            if ss<0.75:continue
            for cand in _extract(kind,w):
                low=cand.casefold()
                qlow=_canon(question).casefold()
                if kind not in {'YEAR','NUMBER'} and low in qlow:continue
                boost=1.0+min(2.0,len(cand)/40.0)
                val=ss*boost
                support[cand]+=val
                if host:host_support[cand].add(host)
                if len(evidence)<80:
                    evidence.append({'candidate_sha256':hashlib.sha256(cand.encode()).hexdigest(),'host_sha256':hashlib.sha256(host.encode()).hexdigest() if host else None,'sentence_score':ss,'body_sha256':fr.get('body_sha256')})
    if not support:
        return {'schema':SCHEMA,'status':'NO_CANDIDATE','candidate_answer':None,'candidate_answer_authority':False,'question_kind':kind,'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'gold_accessed':False,'external_model_calls':0,'model_dependency_count':0,'terminal_authority':False}
    ranked=sorted(support,key=lambda c:(-(support[c]+1.5*min(len(host_support[c]),3)),c.casefold(),c))
    chosen=ranked[0]; second=ranked[1] if len(ranked)>1 else None
    score=support[chosen]+1.5*min(len(host_support[chosen]),3)
    second_score=(support[second]+1.5*min(len(host_support[second]),3)) if second else 0.0
    margin=score-second_score
    conf='HIGH' if len(host_support[chosen])>=2 and margin>=2 else 'MEDIUM' if margin>=0.75 else 'LOW'
    return {'schema':SCHEMA,'status':'CANDIDATE_GENERATED','task_id':task_id,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),'question_kind':kind,'candidate_answer':chosen,'candidate_answer_authority':False,'candidate_score':score,'runner_up_margin':margin,'independent_support_host_count':len(host_support[chosen]),'confidence_band':conf,'search_status':sr.get('status'),'search_result_count':len(sr.get('results') or []),'fetched_url_count':len(urls),'evidence_receipts':evidence,'gold_accessed':False,'external_model_calls':0,'model_dependency_count':0,'incremental_spend_usd':0,'terminal_authority':False,'hard_nonclaim':'DETERMINISTIC_RETRIEVAL_EXTRACTION_IS_A_FALLIBLE_PROPOSAL_GENERATOR_NOT_A_CORRECTNESS_PROOF'}
