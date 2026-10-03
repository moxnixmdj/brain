"""Open-world hypothesis guard and robust discriminator for Learning V4."""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
import hashlib, json
from typing import Any, Mapping, Sequence

from canonical.runtime import decision_discriminator_v3 as v3

SCHEMA="PROJECT_BRAIN_OPEN_WORLD_HYPOTHESIS_GUARD_V4"

class OpenWorldHypothesisError(ValueError):
    pass

def _f(x:Any,name:str)->Fraction:
    if isinstance(x,bool):
        raise OpenWorldHypothesisError(name.upper()+"_INVALID")
    try:
        out=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise OpenWorldHypothesisError(name.upper()+"_INVALID") from exc
    if out<0:
        raise OpenWorldHypothesisError(name.upper()+"_NEGATIVE")
    return out

def hypothesis_digest(hypotheses:Sequence[Mapping[str,Any]])->str:
    rows=[]
    seen=set()
    for raw in hypotheses:
        hid=str(raw.get("id") or "").strip()
        if not hid or hid in seen:
            raise OpenWorldHypothesisError("HYPOTHESIS_ID_INVALID_OR_DUPLICATE")
        seen.add(hid)
        rows.append({
            "id":hid,
            "plausible":raw.get("plausible") is True,
            "best_action":str(raw.get("best_action") or "").strip(),
        })
    rows.sort(key=lambda x:x["id"])
    body=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def close_space(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],coverage_receipt:Mapping[str,Any]|None)->dict[str,Any]:
    digest=hypothesis_digest(hypotheses)
    if coverage_receipt is None:
        return {"closed":False,"hypothesis_space_sha256":digest,"receipt_id":None}
    r=coverage_receipt
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise OpenWorldHypothesisError("HYPOTHESIS_COVERAGE_RECEIPT_INVALID")
    if r.get("decision_relevant_exhaustive") is not True:
        raise OpenWorldHypothesisError("HYPOTHESIS_SPACE_EXHAUSTIVENESS_NOT_PROVED")
    if str(r.get("scope_relation") or "") not in {"EXACT","PROVEN_SUPERSET"}:
        raise OpenWorldHypothesisError("HYPOTHESIS_SCOPE_RELATION_NOT_ADMISSIBLE")
    if str(r.get("environment_id") or "").strip()!=str(environment_id or "").strip() or str(r.get("goal_id") or "").strip()!=str(goal_id or "").strip():
        raise OpenWorldHypothesisError("HYPOTHESIS_COVERAGE_SCOPE_MISMATCH")
    if r.get("hypothesis_space_sha256")!=digest:
        raise OpenWorldHypothesisError("HYPOTHESIS_COVERAGE_DIGEST_MISMATCH")
    rid=str(r.get("receipt_id") or "").strip()
    if not rid:
        raise OpenWorldHypothesisError("HYPOTHESIS_COVERAGE_RECEIPT_ID_REQUIRED")
    return {"closed":True,"hypothesis_space_sha256":digest,"receipt_id":rid}

def _residual_invariant(*,environment_id:str,goal_id:str,action:str,receipt:Mapping[str,Any]|None)->str|None:
    if receipt is None:
        return None
    if receipt.get("independent_verified") is not True or receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
        raise OpenWorldHypothesisError("RESIDUAL_ACTION_RECEIPT_INVALID")
    if receipt.get("all_unmodeled_decision_relevant_alternatives_imply_action") is not True:
        raise OpenWorldHypothesisError("RESIDUAL_ACTION_INVARIANCE_NOT_PROVED")
    if str(receipt.get("environment_id") or "").strip()!=str(environment_id or "").strip() or str(receipt.get("goal_id") or "").strip()!=str(goal_id or "").strip():
        raise OpenWorldHypothesisError("RESIDUAL_ACTION_SCOPE_MISMATCH")
    if str(receipt.get("action") or "").strip()!=action:
        raise OpenWorldHypothesisError("RESIDUAL_ACTION_BINDING_MISMATCH")
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise OpenWorldHypothesisError("RESIDUAL_ACTION_RECEIPT_ID_REQUIRED")
    return rid

def decision_sufficient(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],coverage_receipt:Mapping[str,Any]|None=None,residual_action_receipt:Mapping[str,Any]|None=None)->dict[str,Any]:
    coverage=close_space(environment_id=environment_id,goal_id=goal_id,hypotheses=hypotheses,coverage_receipt=coverage_receipt)
    live=[];seen=set()
    for raw in hypotheses:
        hid=str(raw.get("id") or "").strip()
        if not hid or hid in seen:
            raise OpenWorldHypothesisError("HYPOTHESIS_ID_INVALID_OR_DUPLICATE")
        seen.add(hid)
        if raw.get("plausible") is not True:
            continue
        action=str(raw.get("best_action") or "").strip()
        if not action:
            raise OpenWorldHypothesisError("LIVE_HYPOTHESIS_ACTION_REQUIRED")
        live.append((hid,action))
    if not live:
        base={"sufficient":False,"action":None,"reason":"NO_LIVE_PLAUSIBLE_HYPOTHESES"}
    else:
        actions={action for _,action in live}
        base=({"sufficient":True,"action":next(iter(actions)),"reason":"ALL_LIVE_PLAUSIBLE_HYPOTHESES_AGREE"} if len(actions)==1 else {"sufficient":False,"action":None,"reason":"LIVE_PLAUSIBLE_HYPOTHESES_DISAGREE"})
    if not base["sufficient"]:
        return {**base,"hypothesis_space_closed":coverage["closed"],"hypothesis_space_sha256":coverage["hypothesis_space_sha256"],"open_world_safe":False}
    action=str(base["action"])
    if coverage["closed"]:
        return {**base,"hypothesis_space_closed":True,"hypothesis_space_sha256":coverage["hypothesis_space_sha256"],"open_world_safe":True,"coverage_receipt":coverage["receipt_id"]}
    rid=_residual_invariant(environment_id=environment_id,goal_id=goal_id,action=action,receipt=residual_action_receipt)
    if rid:
        return {**base,"hypothesis_space_closed":False,"hypothesis_space_sha256":coverage["hypothesis_space_sha256"],"open_world_safe":True,"residual_action_invariance_receipt":rid,"reason":"ENUMERATED_MODELS_AGREE_AND_UNMODELED_ACTION_INVARIANCE_PROVED"}
    return {"sufficient":False,"action":None,"reason":"DECLARED_HYPOTHESES_AGREE_BUT_OPEN_WORLD_RESIDUAL_CAN_STILL_CHANGE_ACTION","hypothesis_space_closed":False,"hypothesis_space_sha256":coverage["hypothesis_space_sha256"],"open_world_safe":False}

def _probe_receipt(*,environment_id:str,goal_id:str,action_id:str,receipt:Mapping[str,Any])->str:
    if receipt.get("independent_verified") is not True or receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
        raise OpenWorldHypothesisError("PROBE_SAFETY_RECEIPT_INVALID")
    if receipt.get("safe_under_all_admissible_worlds") is not True:
        raise OpenWorldHypothesisError("PROBE_OPEN_WORLD_SAFETY_NOT_PROVED")
    if str(receipt.get("environment_id") or "").strip()!=str(environment_id or "").strip() or str(receipt.get("goal_id") or "").strip()!=str(goal_id or "").strip():
        raise OpenWorldHypothesisError("PROBE_SAFETY_SCOPE_MISMATCH")
    if str(receipt.get("action_id") or "").strip()!=action_id:
        raise OpenWorldHypothesisError("PROBE_SAFETY_ACTION_MISMATCH")
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise OpenWorldHypothesisError("PROBE_SAFETY_RECEIPT_ID_REQUIRED")
    return rid

def robust_rank(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],actions:Sequence[Mapping[str,Any]])->dict[str,Any]:
    live=[h for h in hypotheses if h.get("plausible") is True]
    ids=[]; best={}; seen=set()
    for h in live:
        hid=str(h.get("id") or "").strip(); act=str(h.get("best_action") or "").strip()
        if not hid or hid in seen or not act:
            raise OpenWorldHypothesisError("LIVE_HYPOTHESIS_INVALID")
        seen.add(hid);ids.append(hid);best[hid]=act
    before=len(set(best.values()))
    ranked=[];rejected=[];action_ids=set()
    for raw in actions:
        aid=str(raw.get("id") or "").strip()
        if not aid or aid in action_ids:
            raise OpenWorldHypothesisError("ACTION_ID_INVALID_OR_DUPLICATE")
        action_ids.add(aid)
        try:
            receipt=raw.get("safety_receipt")
            if not isinstance(receipt,Mapping):
                raise OpenWorldHypothesisError("PROBE_SAFETY_RECEIPT_REQUIRED")
            rid=_probe_receipt(environment_id=environment_id,goal_id=goal_id,action_id=aid,receipt=receipt)
            outcomes=raw.get("outcome_by_hypothesis")
            if not isinstance(outcomes,Mapping) or set(ids)-set(map(str,outcomes.keys())):
                raise OpenWorldHypothesisError("ACTION_OUTCOME_MAP_INCOMPLETE")
            groups=defaultdict(set)
            for hid in ids:
                groups[str(outcomes[hid])].add(best[hid])
            worst=max((len(v) for v in groups.values()),default=before)
            gain=max(0,before-worst)
            time=_f(raw.get("time",0),"time");cost=_f(raw.get("cost",0),"cost");risk=_f(raw.get("risk",0),"risk")
            den=time+cost+risk
            if den<=0:
                raise OpenWorldHypothesisError("ACTION_TOTAL_COST_MUST_BE_POSITIVE")
            if gain>0:
                ranked.append({"id":aid,"minimax_action_class_reduction":gain,"worst_case_remaining_action_classes":worst,"value_density":str(Fraction(gain,1)/den),"safety_receipt":rid,"probability_model_required":False,"_den":den})
        except OpenWorldHypothesisError as exc:
            rejected.append({"id":aid or "<missing>","reason":str(exc)})
    ranked.sort(key=lambda x:(-x["minimax_action_class_reduction"],x["_den"],x["id"]))
    for row in ranked: row.pop("_den")
    return {"schema":SCHEMA,"ranked":ranked,"rejected":rejected,"probability_model_required":False}
