"""Receipt-bound probe outcome models for Universal Learning V5."""
from __future__ import annotations
import hashlib, json
from fractions import Fraction
from typing import Any, Mapping, Sequence

from canonical.runtime import open_world_hypothesis_guard_v4 as v4

SCHEMA="PROJECT_BRAIN_VERIFIED_PROBE_MODEL_V5"
class VerifiedProbeModelError(ValueError): pass

def _f(x:Any,name:str)->Fraction:
    if isinstance(x,bool): raise VerifiedProbeModelError(name.upper()+"_INVALID")
    try: out=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc: raise VerifiedProbeModelError(name.upper()+"_INVALID") from exc
    if out<0: raise VerifiedProbeModelError(name.upper()+"_NEGATIVE")
    return out

def outcome_digest(*,action_id:str,outcomes:Mapping[str,Any])->str:
    aid=str(action_id or "").strip()
    if not aid: raise VerifiedProbeModelError("ACTION_ID_REQUIRED")
    rows=sorted((str(k),str(v)) for k,v in outcomes.items())
    body=json.dumps({"action_id":aid,"outcomes":rows},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def admit(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],probe:Mapping[str,Any])->dict[str,Any]:
    env=str(environment_id or "").strip(); goal=str(goal_id or "").strip()
    aid=str(probe.get("id") or "").strip()
    if not env or not goal or not aid: raise VerifiedProbeModelError("ENVIRONMENT_GOAL_ACTION_REQUIRED")
    outcomes=probe.get("outcome_by_hypothesis")
    if not isinstance(outcomes,Mapping): raise VerifiedProbeModelError("OUTCOME_MAP_REQUIRED")
    live_ids={str(h.get("id") or "").strip() for h in hypotheses if h.get("plausible") is True}
    if not live_ids or "" in live_ids: raise VerifiedProbeModelError("LIVE_HYPOTHESIS_SET_INVALID")
    if live_ids-set(map(str,outcomes.keys())): raise VerifiedProbeModelError("OUTCOME_MAP_INCOMPLETE")

    safety=probe.get("safety_receipt")
    if not isinstance(safety,Mapping): raise VerifiedProbeModelError("SAFETY_RECEIPT_REQUIRED")
    if safety.get("independent_verified") is not True or safety.get("exact_byte_bound") is not True or safety.get("conclusion")!="success":
        raise VerifiedProbeModelError("SAFETY_RECEIPT_INVALID")
    if safety.get("safe_under_all_admissible_worlds") is not True:
        raise VerifiedProbeModelError("OPEN_WORLD_SAFETY_NOT_PROVED")
    if str(safety.get("environment_id") or "").strip()!=env or str(safety.get("goal_id") or "").strip()!=goal or str(safety.get("action_id") or "").strip()!=aid:
        raise VerifiedProbeModelError("SAFETY_RECEIPT_SCOPE_MISMATCH")
    srid=str(safety.get("receipt_id") or "").strip()
    if not srid: raise VerifiedProbeModelError("SAFETY_RECEIPT_ID_REQUIRED")

    model=probe.get("outcome_model_receipt")
    if not isinstance(model,Mapping): raise VerifiedProbeModelError("OUTCOME_MODEL_RECEIPT_REQUIRED")
    if model.get("independent_verified") is not True or model.get("exact_byte_bound") is not True or model.get("conclusion")!="success":
        raise VerifiedProbeModelError("OUTCOME_MODEL_RECEIPT_INVALID")
    if model.get("decision_relevant_outcome_partition_complete") is not True:
        raise VerifiedProbeModelError("OUTCOME_PARTITION_COMPLETENESS_NOT_PROVED")
    if str(model.get("environment_id") or "").strip()!=env or str(model.get("goal_id") or "").strip()!=goal or str(model.get("action_id") or "").strip()!=aid:
        raise VerifiedProbeModelError("OUTCOME_MODEL_SCOPE_MISMATCH")
    hd=v4.hypothesis_digest(hypotheses)
    if model.get("hypothesis_space_sha256")!=hd:
        raise VerifiedProbeModelError("OUTCOME_MODEL_HYPOTHESIS_DIGEST_MISMATCH")
    od=outcome_digest(action_id=aid,outcomes=outcomes)
    if model.get("outcome_map_sha256")!=od:
        raise VerifiedProbeModelError("OUTCOME_MODEL_MAP_DIGEST_MISMATCH")
    mrid=str(model.get("receipt_id") or "").strip()
    if not mrid: raise VerifiedProbeModelError("OUTCOME_MODEL_RECEIPT_ID_REQUIRED")

    t=_f(probe.get("time",0),"time"); c=_f(probe.get("cost",0),"cost"); r=_f(probe.get("risk",0),"risk")
    total=t+c+r
    if total<=0: raise VerifiedProbeModelError("PROBE_TOTAL_COST_MUST_BE_POSITIVE")
    return {
        "id":aid,
        "outcome_by_hypothesis":{str(k):str(v) for k,v in outcomes.items()},
        "total_cost":total,
        "safety_receipt":srid,
        "outcome_model_receipt":mrid,
        "hypothesis_space_sha256":hd,
        "outcome_map_sha256":od,
        "verified":True,
    }
