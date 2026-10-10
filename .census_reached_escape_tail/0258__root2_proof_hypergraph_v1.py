from __future__ import annotations
import hashlib, itertools
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_ROOT2_PROOF_HYPERGRAPH_V1"

class Root2OptimizerError(ValueError):
    pass

def _f(x:Any,name:str)->Fraction:
    if isinstance(x,bool):
        raise Root2OptimizerError(name.upper()+"_INVALID")
    try:
        return x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise Root2OptimizerError(name.upper()+"_INVALID") from exc

def git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def verify_inventory_binding(path:Path,expected_blob_sha:str)->dict[str,Any]:
    got=git_blob_sha(path)
    ok=got==str(expected_blob_sha)
    return {"schema":SCHEMA,"status":"PASS" if ok else "FAIL_CLOSED","expected":str(expected_blob_sha),"observed":got,"bound":ok}

def binary_prefix_decision(*,successes:int,observed:int,total:int,threshold:Any)->dict[str,Any]:
    if any(isinstance(x,bool) or not isinstance(x,int) for x in (successes,observed,total)):
        raise Root2OptimizerError("COUNTS_MUST_BE_INTEGERS")
    if total<=0 or observed<0 or successes<0 or observed>total or successes>observed:
        raise Root2OptimizerError("COUNT_INVARIANT_VIOLATION")
    t=_f(threshold,"threshold")
    if t<0 or t>1:
        raise Root2OptimizerError("THRESHOLD_OUT_OF_RANGE")
    req=(total*t.numerator + t.denominator-1)//t.denominator
    rem=total-observed
    if successes>=req:
        state="GUARANTEED_PASS"
    elif successes+rem<req:
        state="GUARANTEED_FAIL"
    else:
        state="CONTINUE"
    return {"schema":SCHEMA,"status":state,"required_successes":req,"successes":successes,"observed":observed,"remaining":rem,"total":total}

def bounded_metric_decision(*,lower:Any,upper:Any,target:Any)->dict[str,Any]:
    lo=_f(lower,"lower"); hi=_f(upper,"upper"); tgt=_f(target,"target")
    if lo>hi:
        raise Root2OptimizerError("LOWER_GT_UPPER")
    if lo>=tgt:
        state="GUARANTEED_PASS"
    elif hi<tgt:
        state="GUARANTEED_FAIL"
    else:
        state="CONTINUE"
    return {"schema":SCHEMA,"status":state,"lower":str(lo),"upper":str(hi),"target":str(tgt)}

def _action(raw:Mapping[str,Any], open_predicates:set[str], weights:Mapping[str,Any])->dict[str,Any] | None:
    aid=str(raw.get("id") or "").strip()
    if not aid:
        raise Root2OptimizerError("ACTION_ID_REQUIRED")
    if raw.get("safe") is not True:
        return None
    if _f(raw.get("incremental_spend_usd",0),"incremental_spend_usd") != 0:
        return None
    closes={str(x).strip() for x in raw.get("closes",[]) if str(x).strip()} & open_predicates
    if not closes:
        return None
    p_lo=_f(raw.get("p_close_low",0),"p_close_low")
    p_hi=_f(raw.get("p_close_high",1),"p_close_high")
    if p_lo<0 or p_hi>1 or p_lo>p_hi:
        raise Root2OptimizerError("PROBABILITY_INTERVAL_INVALID:"+aid)
    info_lo=_f(raw.get("information_gain_low",0),"information_gain_low")
    time_hi=_f(raw.get("time_high",0),"time_high")
    risk_hi=_f(raw.get("risk_high",0),"risk_high")
    corr_hi=_f(raw.get("correlation_high",0),"correlation_high")
    if min(info_lo,time_hi,risk_hi,corr_hi)<0 or corr_hi>1:
        raise Root2OptimizerError("ACTION_DIMENSION_INVALID:"+aid)
    den=time_hi+risk_hi
    if den<=0:
        raise Root2OptimizerError("ACTION_COST_NONPOSITIVE:"+aid)
    close_value=sum(_f(weights.get(p,1),"weight") for p in closes)
    diversity=max(Fraction(0),Fraction(1)-corr_hi)
    robust=((p_lo*close_value)+info_lo)*diversity/den
    return {
        "id":aid,
        "closes":sorted(closes),
        "source_class":str(raw.get("source_class") or "UNSPECIFIED"),
        "route_class":str(raw.get("route_class") or "UNSPECIFIED"),
        "p_close_low":str(p_lo),
        "p_close_high":str(p_hi),
        "robust_value_density":str(robust),
        "guaranteed":bool(raw.get("guaranteed") is True and p_lo==1),
        "time_high":str(time_hi),
        "risk_high":str(risk_hi),
        "incremental_spend_usd":"0",
    }

def rank_actions(actions:Sequence[Mapping[str,Any]],*,open_predicates:Iterable[Any],weights:Mapping[str,Any]|None=None)->list[dict[str,Any]]:
    opens={str(x).strip() for x in open_predicates if str(x).strip()}
    w=weights or {}
    seen=set(); rows=[]
    for raw in actions:
        aid=str(raw.get("id") or "").strip()
        if aid in seen:
            raise Root2OptimizerError("DUPLICATE_ACTION_ID:"+aid)
        seen.add(aid)
        x=_action(raw,opens,w)
        if x is not None and Fraction(x["robust_value_density"])>0:
            rows.append(x)
    rows.sort(key=lambda x:(-Fraction(x["robust_value_density"]),-len(x["closes"]),x["id"]))
    return rows

def minimum_guaranteed_cover(actions:Sequence[Mapping[str,Any]],*,open_predicates:Iterable[Any])->dict[str,Any]:
    opens={str(x).strip() for x in open_predicates if str(x).strip()}
    rows=rank_actions(actions,open_predicates=opens)
    guaranteed=[x for x in rows if x["guaranteed"]]
    universe=set().union(*(set(x["closes"]) for x in guaranteed)) if guaranteed else set()
    if not opens.issubset(universe):
        return {"schema":SCHEMA,"status":"NO_GUARANTEED_FULL_COVER","selected":[],"uncovered":sorted(opens-universe)}
    if len(guaranteed)>24:
        raise Root2OptimizerError("GUARANTEED_ACTION_SET_TOO_LARGE_FOR_EXACT_COVER")
    best=None
    for k in range(1,len(guaranteed)+1):
        for combo in itertools.combinations(guaranteed,k):
            covered=set().union(*(set(x["closes"]) for x in combo))
            if opens.issubset(covered):
                cost=sum(Fraction(x["time_high"])+Fraction(x["risk_high"]) for x in combo)
                key=(k,cost,tuple(x["id"] for x in combo))
                if best is None or key<best[0]:
                    best=(key,combo)
        if best is not None:
            break
    combo=best[1]
    return {"schema":SCHEMA,"status":"GUARANTEED_FULL_COVER","selected":[x["id"] for x in combo],"action_count":len(combo),"worst_case_time_plus_risk":str(best[0][1]),"uncovered":[]}

def robust_frontier(actions:Sequence[Mapping[str,Any]],*,open_predicates:Iterable[Any],weights:Mapping[str,Any]|None=None,max_actions:int=8,max_same_source_class:int=2)->dict[str,Any]:
    if isinstance(max_actions,bool) or max_actions<1 or isinstance(max_same_source_class,bool) or max_same_source_class<1:
        raise Root2OptimizerError("PORTFOLIO_LIMIT_INVALID")
    opens={str(x).strip() for x in open_predicates if str(x).strip()}
    ranked=rank_actions(actions,open_predicates=opens,weights=weights)
    selected=[]; counts={}; covered=set()
    for x in ranked:
        sc=x["source_class"]
        if counts.get(sc,0)>=max_same_source_class:
            continue
        marginal=set(x["closes"])-covered
        if not marginal:
            continue
        selected.append(x)
        counts[sc]=counts.get(sc,0)+1
        covered|=set(x["closes"])
        if len(selected)>=max_actions or opens.issubset(covered):
            break
    return {
        "schema":SCHEMA,
        "status":"PORTFOLIO_COMPILED",
        "selected_action_ids":[x["id"] for x in selected],
        "covered_predicates":sorted(covered),
        "uncovered_predicates":sorted(opens-covered),
        "new_reality_authority":False,
        "promotion_authority":False,
    }
