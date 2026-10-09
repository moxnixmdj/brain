"""Constructive coding repair over a finite complete defect universe with strict monotone progress."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CODING_MONOTONE_DEFECT_REPAIR_SOLVER_V1"
POLICY_ID="BRAIN_MONOTONE_DEFECT_REPAIR_SOLVER_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "policy_id":POLICY_ID,"solution_found":False,"terminal_authority":False,
         "acceptance_credit_delta":0,"terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def _normalize_verdict(raw:Any, universe:set[str])->tuple[bool,set[str],str|None]:
    if not isinstance(raw,Mapping):
        return False,set(),"VERIFIER_RESULT_NOT_OBJECT"
    passed=raw.get("pass")
    defects=raw.get("defects")
    if type(passed) is not bool:
        return False,set(),"VERIFIER_PASS_NOT_BOOLEAN"
    if not isinstance(defects,list) or any(not isinstance(x,str) or not x for x in defects):
        return False,set(),"VERIFIER_DEFECTS_INVALID"
    if len(set(defects))!=len(defects):
        return False,set(),"VERIFIER_DEFECTS_DUPLICATE"
    observed=set(defects)
    unknown=sorted(observed-universe)
    if unknown:
        return False,set(),"VERIFIER_DEFECT_OUTSIDE_DECLARED_UNIVERSE:"+",".join(unknown)
    if passed and observed:
        return False,set(),"PASS_WITH_NONEMPTY_DEFECT_SET"
    if (not passed) and not observed:
        return False,set(),"FAIL_WITH_EMPTY_DEFECT_SET"
    return passed,observed,None

def solve(initial_candidate:Mapping[str,Any],
          defect_ids:Sequence[str],
          verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]],
          repair:Callable[[Mapping[str,Any],str],Mapping[str,Any]],
          *,max_verifier_calls:int,max_repairs:int)->dict[str,Any]:
    if not isinstance(initial_candidate,Mapping):
        return _fail("INITIAL_CANDIDATE_NOT_OBJECT")
    if isinstance(defect_ids,(str,bytes)) or not isinstance(defect_ids,Sequence):
        return _fail("DEFECT_UNIVERSE_NOT_SEQUENCE")
    defects=list(defect_ids)
    if not defects or any(not isinstance(x,str) or not x for x in defects):
        return _fail("DEFECT_UNIVERSE_INVALID_OR_EMPTY")
    if len(set(defects))!=len(defects):
        return _fail("DEFECT_UNIVERSE_DUPLICATE")
    if not callable(verifier):
        return _fail("VERIFIER_NOT_CALLABLE")
    if not callable(repair):
        return _fail("REPAIR_NOT_CALLABLE")
    for name,value in (("MAX_VERIFIER_CALLS",max_verifier_calls),("MAX_REPAIRS",max_repairs)):
        if isinstance(value,bool) or not isinstance(value,int) or value<0:
            return _fail(name+"_INVALID")
    k=len(defects)
    if max_verifier_calls<k+1:
        return _fail("VERIFIER_BUDGET_INSUFFICIENT_FOR_WORST_CASE",
                     defect_count=k,required_verifier_calls=k+1,max_verifier_calls=max_verifier_calls)
    if max_repairs<k:
        return _fail("REPAIR_BUDGET_INSUFFICIENT_FOR_WORST_CASE",
                     defect_count=k,required_repairs=k,max_repairs=max_repairs)

    universe=set(defects)
    current=deepcopy(dict(initial_candidate))
    previous_defects:set[str]|None=None
    verifier_calls=0
    repair_calls=0
    trace=[]

    while verifier_calls<max_verifier_calls:
        try:
            raw=verifier(deepcopy(current))
        except Exception as exc:
            return _fail("VERIFIER_EXCEPTION",verifier_calls=verifier_calls+1,
                         repair_calls=repair_calls,error_type=type(exc).__name__)
        verifier_calls+=1
        passed,observed,error=_normalize_verdict(raw,universe)
        if error:
            return _fail(error,verifier_calls=verifier_calls,repair_calls=repair_calls)
        trace.append({"verifier_call":verifier_calls,"defects":sorted(observed),"pass":passed})

        if previous_defects is not None and not observed < previous_defects:
            return _fail("DEFECT_SET_DID_NOT_STRICTLY_DECREASE",
                         previous_defects=sorted(previous_defects),
                         observed_defects=sorted(observed),
                         verifier_calls=verifier_calls,repair_calls=repair_calls)

        if passed:
            return {"schema":SCHEMA,"pass":True,
                    "status":"PASS__FINITE_DEFECT_RANK_REACHED_ZERO",
                    "policy_id":POLICY_ID,"solution_found":True,
                    "selected_candidate":current,
                    "initial_defect_universe_size":k,
                    "verifier_calls":verifier_calls,"repair_calls":repair_calls,
                    "trace":trace,"terminal_authority":False,
                    "acceptance_credit_delta":0,"terminal_credit_delta":0}

        if repair_calls>=max_repairs:
            return _fail("REPAIR_BUDGET_EXHAUSTED",verifier_calls=verifier_calls,
                         repair_calls=repair_calls,defects=sorted(observed))
        selected=next(d for d in defects if d in observed)
        try:
            repaired=repair(deepcopy(current),selected)
        except Exception as exc:
            return _fail("REPAIR_EXCEPTION",selected_defect=selected,
                         verifier_calls=verifier_calls,repair_calls=repair_calls+1,
                         error_type=type(exc).__name__)
        if not isinstance(repaired,Mapping):
            return _fail("REPAIR_RESULT_NOT_OBJECT",selected_defect=selected,
                         verifier_calls=verifier_calls,repair_calls=repair_calls+1)
        current=deepcopy(dict(repaired))
        repair_calls+=1
        previous_defects=observed

    return _fail("VERIFIER_BUDGET_EXHAUSTED",verifier_calls=verifier_calls,
                 repair_calls=repair_calls)
