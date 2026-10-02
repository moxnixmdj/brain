"""Verifier-side blinded unknown-mechanism proof surface.

The operative Brain route receives only public case metadata and bounded oracle query
responses. The verifier alone receives the seed used to generate the hidden mechanism
and hidden evaluation points.

This module is a proof-surface primitive. It does not claim terminal capability.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import random
from typing import Any

KINDS=("AFFINE_MOD","XOR_ROT","PIECEWISE_AFFINE")
PRIME=257

@dataclass(frozen=True)
class HiddenCase:
    case_id:str
    kind:str
    params:tuple[int,...]
    query_budget:int
    eval_points:tuple[int,...]

def _derive_rng(seed:str, case_index:int)->random.Random:
    h=hashlib.sha256(f"{seed}:{case_index}".encode()).digest()
    return random.Random(int.from_bytes(h[:16],"big"))

def generate_hidden_case(seed:str, case_index:int, *, query_budget:int=8)->HiddenCase:
    if not isinstance(seed,str) or not seed:
        raise ValueError("non-empty verifier seed required")
    if not isinstance(case_index,int) or case_index<0:
        raise ValueError("case_index must be non-negative")
    if not isinstance(query_budget,int) or query_budget<1:
        raise ValueError("query_budget must be positive")
    rng=_derive_rng(seed,case_index)
    kind=KINDS[rng.randrange(len(KINDS))]
    if kind=="AFFINE_MOD":
        a=rng.randrange(1,PRIME); b=rng.randrange(PRIME)
        params=(a,b)
    elif kind=="XOR_ROT":
        k=rng.randrange(1,8); mask=rng.randrange(1,256)
        params=(k,mask)
    else:
        cut=rng.randrange(32,224)
        a1=rng.randrange(1,PRIME); b1=rng.randrange(PRIME)
        a2=rng.randrange(1,PRIME); b2=rng.randrange(PRIME)
        params=(cut,a1,b1,a2,b2)
    eval_points=tuple(rng.sample(range(0,256),16))
    cid=hashlib.sha256(f"{seed}:{case_index}:public".encode()).hexdigest()[:16]
    return HiddenCase(cid,kind,params,query_budget,eval_points)

def apply(case:HiddenCase,x:int)->int:
    if not isinstance(x,int) or not 0<=x<=255:
        raise ValueError("query x must be integer in [0,255]")
    if case.kind=="AFFINE_MOD":
        a,b=case.params; return (a*x+b)%PRIME
    if case.kind=="XOR_ROT":
        k,mask=case.params
        y=x^mask
        return ((y<<k)|(y>>(8-k)))&255
    if case.kind=="PIECEWISE_AFFINE":
        cut,a1,b1,a2,b2=case.params
        a,b=(a1,b1) if x<cut else (a2,b2)
        return (a*x+b)%PRIME
    raise ValueError("unsupported mechanism kind")

def public_case(case:HiddenCase)->dict[str,Any]:
    return {
        "case_id":case.case_id,
        "input_domain":[0,255],
        "output_domain":[0,256],
        "query_budget":case.query_budget,
        "allowed_action":"QUERY_INTEGER_X_AND_OBSERVE_INTEGER_Y",
        "required_final_output":"PREDICTIONS_FOR_VERIFIER_SUPPLIED_HIDDEN_EVAL_POINTS",
    }

def run_queries(case:HiddenCase,queries:list[int])->list[dict[str,int]]:
    if not isinstance(queries,list) or len(queries)>case.query_budget:
        raise ValueError("query budget exceeded or invalid query list")
    if len(set(queries))!=len(queries):
        raise ValueError("duplicate queries are inadmissible")
    return [{"x":x,"y":apply(case,x)} for x in queries]

def score_predictions(case:HiddenCase,predictions:dict[int,int])->dict[str,Any]:
    if not isinstance(predictions,dict):
        raise ValueError("predictions must be dict[int,int]")
    expected={x:apply(case,x) for x in case.eval_points}
    if set(predictions)!=set(expected):
        return {"status":"FAIL_CLOSED","reason":"EVAL_POINT_SET_MISMATCH","accuracy":0.0}
    correct=0
    for x,y in expected.items():
        py=predictions[x]
        if not isinstance(py,int):
            return {"status":"FAIL_CLOSED","reason":"NONINTEGER_PREDICTION","accuracy":0.0}
        correct += int(py==y)
    acc=correct/len(expected)
    return {
        "status":"SCORED",
        "accuracy":acc,
        "correct":correct,
        "total":len(expected),
        "exact_pass":correct==len(expected),
    }
