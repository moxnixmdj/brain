#!/usr/bin/env python3
"""Answer-key-blind registry pseudo-relevance feedback.

Extracts high-signal terms from already observed registry candidates and turns
them into bounded follow-up queries. It never sees the holdout target identity.
"""
from __future__ import annotations
import math,re,unicodedata
from collections import Counter,defaultdict
from typing import Any,Mapping,Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_REGISTRY_FEEDBACK_V1"
WORD=re.compile(r"[^\W_]+(?:[-/.@][^\W_]+)*",re.UNICODE)
GENERIC={"http","https","client","server","library","package","framework","node","rust",
         "python","javascript","async","browser","object","mapping","processing","structured",
         "diagnostics","instrumentation","promise","redis","concurrency","background","job"}

def canon(x:Any)->str:
 return " ".join(unicodedata.normalize("NFKC",str(x or "")).strip().split())

def tokens(x:Any)->list[str]:
 out=[]
 for raw in WORD.findall(canon(x)):
  t=raw.casefold().strip("-/.@")
  if len(t)>=3:out.append(t)
 return out

def candidate_strings(row:Mapping[str,Any])->list[str]:
 out=[]
 for k in ("name","id","description","repository","homepage","keywords","title","snippet"):
  v=row.get(k)
  if isinstance(v,str):out.append(v)
  elif isinstance(v,(list,tuple)):out.extend(str(x) for x in v)
 pkg=row.get("package")
 if isinstance(pkg,Mapping):out.extend(candidate_strings(pkg))
 return out

def stem_variants(token:str)->set[str]:
 out={token}
 for sep in ("-","/","@"):
  if sep in token:
   for part in token.split(sep):
    if len(part)>=4:out.add(part)
 return out

def feedback_terms(query:str,candidates:Sequence[Mapping[str,Any]],*,limit:int=12)->list[dict[str,Any]]:
 qset=set(tokens(query));df=Counter();sources=defaultdict(set)
 for i,row in enumerate(candidates):
  seen=set()
  for s in candidate_strings(row):
   for tok in tokens(s):
    for v in stem_variants(tok):
     if len(v)>=4 and v not in qset and v not in GENERIC:seen.add(v)
  for v in seen:
   df[v]+=1;sources[v].add(i)
 n=max(1,len(candidates));ranked=[]
 for term,freq in df.items():
  rarity=math.log((n+1)/(freq+0.5))+1.0
  technical=1.35 if any(ch in term for ch in "-/.@") else 1.0
  score=rarity*technical*(1.0+0.15*len(sources[term]))
  ranked.append((score,term,freq))
 ranked.sort(key=lambda x:(-x[0],x[1]))
 return [{"term":t,"score":round(s,6),"candidate_document_frequency":f} for s,t,f in ranked[:limit]]

def feedback_queries(query:str,candidates:Sequence[Mapping[str,Any]],*,limit:int=8)->list[str]:
 terms=feedback_terms(query,candidates,limit=max(limit*2,12))
 out=[];seen=set()
 for row in terms:
  t=row["term"]
  for q in (t,f"{t} {query}"):
   q=canon(q)
   if q.casefold() not in seen:
    seen.add(q.casefold());out.append(q)
   if len(out)>=limit:return out
 return out

def compile_recovery(query:str,candidates:Sequence[Mapping[str,Any]],*,limit:int=8)->dict[str,Any]:
 qs=feedback_queries(query,candidates,limit=limit)
 return {"schema":SCHEMA,"status":"COMPILED_REGISTRY_PSEUDO_RELEVANCE_FEEDBACK",
  "queries":qs,"query_count":len(qs),"answer_key_identity_used":False,
  "candidate_authority":"CANDIDATE_ONLY","open_world_nonexistence_claim_authorized":False,
  "incremental_spend_usd":0,
  "hard_rules":["ONLY_OBSERVED_CANDIDATE_METADATA_MAY_GENERATE_FEEDBACK_TERMS",
                "ANSWER_KEY_IDENTITY_IS_FORBIDDEN",
                "FEEDBACK_QUERIES_REMAIN_CANDIDATE_GENERATORS_ONLY",
                "EMPTY_FEEDBACK_RESULT_REMAINS_UNKNOWN"]}
