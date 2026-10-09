"""Robust finite-candidate constructive search across a complete interpretation set."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CODING_ROBUST_FINITE_MULTI_INTERPRETATION_SOLVER_V1"
POLICY_ID="BRAIN_ROBUST_FINITE_MULTI_INTERPRETATION_SOLVER_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "policy_id":POLICY_ID,"solution_found":False,"terminal_authority":False,
         "acceptance_credit_delta":0,"terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def solve(candidates:Sequence[Mapping[str,Any]],
          interpretations:Sequence[Mapping[str,Any]],
          checker:Callable[[Mapping[str,Any],Mapping[str,Any]],bool],
          *,max_checks:int)->dict[str,Any]:
    if isinstance(candidates,(str,bytes)) or not isinstance(candidates,Sequence):
        return _fail("CANDIDATES_NOT_SEQUENCE")
    if isinstance(interpretations,(str,bytes)) or not isinstance(interpretations,Sequence):
        return _fail("INTERPRETATIONS_NOT_SEQUENCE")
    rows=list(candidates)
    worlds=list(interpretations)
    if not rows: return _fail("CANDIDATE_SET_EMPTY")
    if not worlds: return _fail("INTERPRETATION_SET_EMPTY")
    if isinstance(max_checks,bool) or not isinstance(max_checks,int) or max_checks<0:
        return _fail("MAX_CHECKS_INVALID")
    required=len(rows)*len(worlds)
    if max_checks<required:
        return _fail("CHECK_BUDGET_INSUFFICIENT_FOR_WORST_CASE",
                     candidate_count=len(rows),interpretation_count=len(worlds),
                     required_checks=required,max_checks=max_checks)
    if not callable(checker): return _fail("CHECKER_NOT_CALLABLE")

    candidate_ids=set()
    normalized=[]
    for i,raw in enumerate(rows):
        if not isinstance(raw,Mapping): return _fail("CANDIDATE_NOT_OBJECT",index=i)
        cid=raw.get("candidate_id")
        if not isinstance(cid,str) or not cid:
            return _fail("CANDIDATE_ID_INVALID",index=i)
        if cid in candidate_ids:
            return _fail("CANDIDATE_ID_DUPLICATE",candidate_id=cid)
        candidate_ids.add(cid)
        normalized.append(deepcopy(dict(raw)))

    interpretation_ids=set()
    normalized_worlds=[]
    for i,raw in enumerate(worlds):
        if not isinstance(raw,Mapping): return _fail("INTERPRETATION_NOT_OBJECT",index=i)
        iid=raw.get("interpretation_id")
        if not isinstance(iid,str) or not iid:
            return _fail("INTERPRETATION_ID_INVALID",index=i)
        if iid in interpretation_ids:
            return _fail("INTERPRETATION_ID_DUPLICATE",interpretation_id=iid)
        interpretation_ids.add(iid)
        normalized_worlds.append(deepcopy(dict(raw)))

    calls=0
    for ci,candidate in enumerate(normalized):
        robust=True
        checked_worlds=[]
        for interpretation in normalized_worlds:
            try:
                verdict=checker(deepcopy(candidate),deepcopy(interpretation))
            except Exception as exc:
                return _fail("CHECKER_EXCEPTION",candidate_id=candidate["candidate_id"],
                             interpretation_id=interpretation["interpretation_id"],
                             check_calls=calls+1,error_type=type(exc).__name__)
            calls+=1
            if type(verdict) is not bool:
                return _fail("CHECKER_NONBOOLEAN_RESULT",
                             candidate_id=candidate["candidate_id"],
                             interpretation_id=interpretation["interpretation_id"],
                             check_calls=calls)
            checked_worlds.append(interpretation["interpretation_id"])
            if not verdict:
                robust=False
                break
        if robust:
            return {"schema":SCHEMA,"pass":True,
                    "status":"PASS__FIRST_CANDIDATE_ACCEPTED_UNDER_ALL_SURVIVING_INTERPRETATIONS",
                    "policy_id":POLICY_ID,"solution_found":True,
                    "selected_candidate_id":candidate["candidate_id"],
                    "selected_candidate_index":ci,"selected_candidate":candidate,
                    "interpretation_count":len(normalized_worlds),
                    "checked_interpretation_ids":checked_worlds,
                    "check_calls":calls,"worst_case_check_bound":required,
                    "max_checks":max_checks,"terminal_authority":False,
                    "acceptance_credit_delta":0,"terminal_credit_delta":0}
    return _fail("NO_ROBUST_ACCEPTED_CANDIDATE",
                 candidate_count=len(normalized),
                 interpretation_count=len(normalized_worlds),
                 check_calls=calls,max_checks=max_checks)
