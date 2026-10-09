"""Finite-candidate constructive search over a supplied total Boolean checker."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CODING_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1"
POLICY_ID="BRAIN_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "policy_id":POLICY_ID,"solution_found":False,"terminal_authority":False,
         "terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def solve(candidates:Sequence[Mapping[str,Any]],
          checker:Callable[[Mapping[str,Any]],bool],
          *,max_checks:int)->dict[str,Any]:
    if isinstance(candidates,(str,bytes)) or not isinstance(candidates,Sequence):
        return _fail("CANDIDATES_NOT_SEQUENCE")
    rows=list(candidates)
    if not rows: return _fail("CANDIDATE_SET_EMPTY")
    if isinstance(max_checks,bool) or not isinstance(max_checks,int) or max_checks<0:
        return _fail("MAX_CHECKS_INVALID")
    if max_checks<len(rows):
        return _fail("CHECK_BUDGET_INSUFFICIENT_FOR_EXHAUSTIVE_ENUMERATION",
                     candidate_count=len(rows),max_checks=max_checks)
    if not callable(checker): return _fail("CHECKER_NOT_CALLABLE")
    seen=set(); normalized=[]
    for i,raw in enumerate(rows):
        if not isinstance(raw,Mapping): return _fail("CANDIDATE_NOT_OBJECT",index=i)
        cid=raw.get("candidate_id")
        if not isinstance(cid,str) or not cid: return _fail("CANDIDATE_ID_INVALID",index=i)
        if cid in seen: return _fail("CANDIDATE_ID_DUPLICATE",candidate_id=cid)
        seen.add(cid); normalized.append(deepcopy(dict(raw)))
    calls=0
    for i,candidate in enumerate(normalized):
        try: verdict=checker(deepcopy(candidate))
        except Exception as exc:
            return _fail("CHECKER_EXCEPTION",candidate_id=candidate["candidate_id"],
                         check_calls=calls+1,error_type=type(exc).__name__)
        calls+=1
        if type(verdict) is not bool:
            return _fail("CHECKER_NONBOOLEAN_RESULT",
                         candidate_id=candidate["candidate_id"],check_calls=calls)
        if verdict:
            return {"schema":SCHEMA,"pass":True,
                    "status":"PASS__FIRST_EXACT_CHECKER_ACCEPTED_CANDIDATE_RETURNED",
                    "policy_id":POLICY_ID,"solution_found":True,
                    "selected_candidate_id":candidate["candidate_id"],
                    "selected_candidate_index":i,"selected_candidate":candidate,
                    "check_calls":calls,"candidate_count":len(normalized),
                    "max_checks":max_checks,"terminal_authority":False,
                    "acceptance_credit_delta":0,"terminal_credit_delta":0}
    return _fail("NO_ACCEPTED_CANDIDATE",candidate_count=len(normalized),
                 check_calls=calls,max_checks=max_checks)
