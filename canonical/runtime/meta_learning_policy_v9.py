"""Receipt-bound meta-learning policy for Universal Learning V9.

Learns which learning strategy is safest and most efficient for a proved context.
Planning-only: it cannot override V1-V8 route, trust, execution, or experiment gates.
"""
from __future__ import annotations
import hashlib, json
from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_META_LEARNING_POLICY_V9"

class MetaLearningError(ValueError): pass

def _s(x): return " ".join(str(x or "").split())
def _items(xs): return tuple(sorted({_s(x) for x in (xs or []) if _s(x)}))
def _f(x,name):
    if isinstance(x,bool): raise MetaLearningError(name.upper()+"_INVALID")
    try: v=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as e: raise MetaLearningError(name.upper()+"_INVALID") from e
    if v<0: raise MetaLearningError(name.upper()+"_NEGATIVE")
    return v

def context_digest(*, features) -> str:
    fs=_items(features)
    if not fs: raise MetaLearningError("CONTEXT_FEATURES_REQUIRED")
    body=json.dumps({"features":fs},sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def episode_digest(*, episode_id, context_sha256, strategy_id, success, burden_before, burden_after, wall_clock, risk, incremental_spend_usd) -> str:
    eid=_s(episode_id); sid=_s(strategy_id)
    if not eid or not sid or not isinstance(success,bool): raise MetaLearningError("EPISODE_INVALID")
    vals={k:_f(v,k) for k,v in {
        "burden_before":burden_before,"burden_after":burden_after,"wall_clock":wall_clock,
        "risk":risk,"incremental_spend_usd":incremental_spend_usd}.items()}
    body=json.dumps({
        "episode_id":eid,"context_sha256":context_sha256,"strategy_id":sid,"success":success,
        **{k:str(v) for k,v in vals.items()}
    },sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _verified_episode(raw:Mapping[str,Any], expected_context:str)->dict[str,Any]:
    eid=_s(raw.get("episode_id")); sid=_s(raw.get("strategy_id"))
    csha=_s(raw.get("context_sha256"))
    if csha!=expected_context: raise MetaLearningError("CONTEXT_SCOPE_MISMATCH:"+eid)
    success=raw.get("success")
    vals={k:_f(raw.get(k,0),k) for k in ("burden_before","burden_after","wall_clock","risk","incremental_spend_usd")}
    dig=episode_digest(episode_id=eid,context_sha256=csha,strategy_id=sid,success=success,**vals)
    r=raw.get("verification_receipt")
    if not isinstance(r,Mapping): raise MetaLearningError("EPISODE_RECEIPT_REQUIRED:"+eid)
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise MetaLearningError("EPISODE_RECEIPT_INVALID:"+eid)
    if _s(r.get("episode_id"))!=eid or r.get("episode_sha256")!=dig:
        raise MetaLearningError("EPISODE_RECEIPT_BINDING_MISMATCH:"+eid)
    if vals["incremental_spend_usd"]>0: raise MetaLearningError("POSITIVE_INCREMENTAL_SPEND_FORBIDDEN:"+eid)
    return {"episode_id":eid,"strategy_id":sid,"success":success,**vals}

def recommend(*, context_features, episodes:Sequence[Mapping[str,Any]])->dict[str,Any]:
    csha=context_digest(features=context_features)
    xs=[_verified_episode(x,csha) for x in episodes]
    if not xs:
        return {"schema":SCHEMA,"status":"NO_VERIFIED_MATCHED_EPISODES","recommended_strategy_id":None,"planning_only":True}
    by={}
    for x in xs: by.setdefault(x["strategy_id"],[]).append(x)
    admissible=[]
    for sid,rows in by.items():
        if not all(r["success"] for r in rows): continue
        if any(r["burden_after"]>r["burden_before"] for r in rows): continue
        reduction_lcb=min(r["burden_before"]-r["burden_after"] for r in rows)
        wall_ub=max(r["wall_clock"] for r in rows)
        risk_ub=max(r["risk"] for r in rows)
        admissible.append(( -reduction_lcb, wall_ub, risk_ub, sid, len(rows)))
    if not admissible:
        return {"schema":SCHEMA,"status":"NO_NO_REGRESSION_STRATEGY","recommended_strategy_id":None,"planning_only":True}
    admissible.sort()
    best=admissible[0]
    return {
        "schema":SCHEMA,"status":"VERIFIED_MATCHED_CONTEXT_META_POLICY",
        "context_sha256":csha,"recommended_strategy_id":best[3],"episode_count":best[4],
        "selection_rule":["BURDEN_REDUCTION_LCB_DESC","WALL_CLOCK_UB_ASC","RISK_UB_ASC","STRATEGY_ID_ASC"],
        "planning_only":True,"execution_authority":False,"promotion_authority":False,
        "fresh_reality_authority":False,"acceptance_credit_delta":0,"ownership_credit_delta":0
    }
