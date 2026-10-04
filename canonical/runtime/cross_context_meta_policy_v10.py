"""Cold-start cross-context meta-policy transfer for Universal Learning V10."""
from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping, Sequence
from canonical.runtime import meta_learning_policy_v9 as mp
from canonical.runtime import context_morphism_v10 as cm

SCHEMA="PROJECT_BRAIN_CROSS_CONTEXT_META_POLICY_V10"
MIN_SOURCE_EPISODES=2

class CrossContextTransferError(ValueError): pass

def _s(x): return " ".join(str(x or "").split())
def _f(x,name):
    if isinstance(x,bool): raise CrossContextTransferError(name.upper()+"_INVALID")
    try: v=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as e: raise CrossContextTransferError(name.upper()+"_INVALID") from e
    if v<0: raise CrossContextTransferError(name.upper()+"_NEGATIVE")
    return v

def _verified_strategy_rows(*,source_context_sha256,strategy_id,episodes):
    rows=[]
    seen_ids=set()
    seen_receipts=set()
    seen_digests=set()
    for raw in episodes:
        if _s(raw.get("strategy_id"))!=strategy_id: continue
        eid=_s(raw.get("episode_id"))
        if not eid or eid in seen_ids:
            raise CrossContextTransferError("SOURCE_EPISODE_ID_INVALID_OR_DUPLICATE:"+eid)
        if _s(raw.get("context_sha256"))!=source_context_sha256:
            raise CrossContextTransferError("SOURCE_EPISODE_CONTEXT_MISMATCH:"+eid)
        success=raw.get("success")
        vals={k:_f(raw.get(k,0),k) for k in ("burden_before","burden_after","wall_clock","risk","incremental_spend_usd")}
        dig=mp.episode_digest(
            episode_id=eid,context_sha256=source_context_sha256,strategy_id=strategy_id,
            success=success,**vals)
        r=raw.get("verification_receipt")
        if not isinstance(r,Mapping) or r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
            raise CrossContextTransferError("SOURCE_EPISODE_RECEIPT_INVALID:"+eid)
        rid=_s(r.get("receipt_id"))
        if not rid or rid in seen_receipts:
            raise CrossContextTransferError("SOURCE_EPISODE_RECEIPT_ID_INVALID_OR_DUPLICATE:"+eid)
        if _s(r.get("episode_id"))!=eid or r.get("episode_sha256")!=dig:
            raise CrossContextTransferError("SOURCE_EPISODE_RECEIPT_BINDING_MISMATCH:"+eid)
        if dig in seen_digests:
            raise CrossContextTransferError("SOURCE_EPISODE_DIGEST_DUPLICATE:"+eid)
        if vals["incremental_spend_usd"]>0:
            raise CrossContextTransferError("POSITIVE_INCREMENTAL_SPEND_FORBIDDEN:"+eid)
        seen_ids.add(eid); seen_receipts.add(rid); seen_digests.add(dig)
        rows.append({"episode_id":eid,"episode_sha256":dig,"receipt_id":rid,"success":success,**vals})
    if len(rows)<MIN_SOURCE_EPISODES:
        raise CrossContextTransferError("INSUFFICIENT_SOURCE_EPISODES")
    if not all(x["success"] for x in rows):
        raise CrossContextTransferError("FAILED_SOURCE_EPISODE")
    if any(x["burden_after"]>x["burden_before"] for x in rows):
        raise CrossContextTransferError("SOURCE_BURDEN_REGRESSION")
    return rows

def recommend(*,target_context_features,exact_target_episodes=(),transfer_candidates:Sequence[Mapping[str,Any]]=()):
    target_sha=mp.context_digest(features=target_context_features)

    if exact_target_episodes:
        exact=mp.recommend(context_features=target_context_features,episodes=exact_target_episodes)
        if exact.get("recommended_strategy_id") is not None:
            return {
                "schema":SCHEMA,"status":"EXACT_TARGET_META_POLICY_HAS_PRIORITY",
                "recommended_strategy_id":exact["recommended_strategy_id"],
                "evidence_mode":"EXACT_TARGET_CONTEXT","exact_target_policy":exact,
                "planning_only":True,"execution_authority":False,"promotion_authority":False,
                "fresh_reality_authority":False,
            }
        return {
            "schema":SCHEMA,"status":"EXACT_TARGET_EVIDENCE_BLOCKS_CROSS_CONTEXT_FALLBACK",
            "recommended_strategy_id":None,"evidence_mode":"EXACT_TARGET_CONTEXT_NO_SAFE_POLICY",
            "planning_only":True,"execution_authority":False,"promotion_authority":False,
            "fresh_reality_authority":False,
        }

    admissible=[]
    rejected=[]
    for i,c in enumerate(transfer_candidates):
        try:
            source_features=c.get("source_context_features") or ()
            source_sha=mp.context_digest(features=source_features)
            sid=_s(c.get("strategy_id"))
            if not sid: raise CrossContextTransferError("STRATEGY_ID_REQUIRED")
            source_episodes=c.get("source_episodes") or ()
            source_policy=mp.recommend(context_features=source_features,episodes=source_episodes)
            if source_policy.get("recommended_strategy_id")!=sid:
                raise CrossContextTransferError("STRATEGY_NOT_SOURCE_POLICY_WINNER")
            rows=_verified_strategy_rows(
                source_context_sha256=source_sha,strategy_id=sid,episodes=source_episodes)
            semantics=c.get("strategy_semantics") or {}
            proof=cm.verify(
                raw=c.get("context_morphism") or {},
                expected_source_context_sha256=source_sha,
                expected_target_context_sha256=target_sha,
                expected_strategy_id=sid,
                expected_strategy_semantics=semantics,
                expected_source_episode_bindings=[
                    {"episode_id":x["episode_id"],"episode_sha256":x["episode_sha256"]}
                    for x in rows])
            reduction_lcb=min(x["burden_before"]-x["burden_after"] for x in rows)
            wall_ub=max(x["wall_clock"] for x in rows)
            risk_ub=max(x["risk"] for x in rows)
            admissible.append({
                "strategy_id":sid,"source_context_sha256":source_sha,
                "source_episode_count":len(rows),"burden_reduction_lcb":reduction_lcb,
                "wall_clock_ub":wall_ub,"risk_ub":risk_ub,
                "strategy_sha256":proof["strategy_sha256"],
                "source_episode_set_sha256":proof["source_episode_set_sha256"],
                "morphism_sha256":proof["morphism_sha256"],
            })
        except Exception as exc:
            rejected.append({"candidate_index":i,"reason":str(exc)})

    if not admissible:
        return {
            "schema":SCHEMA,"status":"NO_VERIFIED_CROSS_CONTEXT_STRATEGY",
            "recommended_strategy_id":None,"target_context_sha256":target_sha,
            "rejected_candidates":rejected,"planning_only":True,
            "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
        }

    admissible.sort(key=lambda x:(
        -x["burden_reduction_lcb"],x["wall_clock_ub"],x["risk_ub"],
        x["strategy_id"],x["source_context_sha256"]))
    best=admissible[0]
    return {
        "schema":SCHEMA,"status":"VERIFIED_COLD_START_CROSS_CONTEXT_META_POLICY",
        "target_context_sha256":target_sha,"recommended_strategy_id":best["strategy_id"],
        "evidence_mode":"PROOF_GATED_ONE_WAY_CONTEXT_MORPHISM",
        "source_context_sha256":best["source_context_sha256"],
        "source_episode_count":best["source_episode_count"],
        "burden_reduction_lcb":str(best["burden_reduction_lcb"]),
        "wall_clock_ub":str(best["wall_clock_ub"]),"risk_ub":str(best["risk_ub"]),
        "strategy_sha256":best["strategy_sha256"],
        "source_episode_set_sha256":best["source_episode_set_sha256"],
        "morphism_sha256":best["morphism_sha256"],
        "admissible_candidate_count":len(admissible),"rejected_candidates":rejected,
        "selection_rule":["BURDEN_REDUCTION_LCB_DESC","WALL_CLOCK_UB_ASC","RISK_UB_ASC","STRATEGY_ID_ASC"],
        "planning_only":True,"execution_authority":False,"promotion_authority":False,
        "fresh_reality_authority":False,"acceptance_credit_delta":0,"ownership_credit_delta":0,
    }
