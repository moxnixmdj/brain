import hashlib
import json
from fractions import Fraction
from typing import Any, Mapping, Sequence

class MetaLearningPolicyError(ValueError):
    pass

def _f(x,name):
    if isinstance(x,bool):
        raise MetaLearningPolicyError(name.upper()+"_INVALID")
    try:
        out=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise MetaLearningPolicyError(name.upper()+"_INVALID") from exc
    if out<0:
        raise MetaLearningPolicyError(name.upper()+"_NEGATIVE")
    return out

def _count(x,name):
    if isinstance(x,bool):
        raise MetaLearningPolicyError(name.upper()+"_INVALID")
    if isinstance(x,int):
        out=x
    elif isinstance(x,str) and x.strip().isdigit():
        out=int(x.strip())
    else:
        raise MetaLearningPolicyError(name.upper()+"_INVALID")
    if out<0:
        raise MetaLearningPolicyError(name.upper()+"_NEGATIVE")
    return out

def comparison_digest(comparison:Mapping[str,Any])->str:
    body=json.dumps(comparison,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def compare(*,episodes:Sequence[Mapping[str,Any]],incumbent:str,candidate:str):
    incumbent=str(incumbent or "").strip()
    candidate=str(candidate or "").strip()
    if not incumbent or not candidate or incumbent==candidate:
        raise MetaLearningPolicyError("META_STRATEGY_IDENTITY_INVALID")
    def idx(strategy):
        out={}
        for e in episodes:
            if str(e.get("strategy_id"))!=strategy:
                continue
            if e.get("verified") is not True:
                raise MetaLearningPolicyError("UNVERIFIED_META_EPISODE")
            tid=str(e.get("task_id") or "").strip()
            if not tid or tid in out:
                raise MetaLearningPolicyError("META_TASK_ID_INVALID_OR_DUPLICATE")
            out[tid]=e
        return out
    old=idx(incumbent)
    new=idx(candidate)
    if not old or not new or set(old)!=set(new):
        raise MetaLearningPolicyError("MATCHED_META_TASK_SET_REQUIRED")
    success=True
    safety=True
    strict=False
    old_cost=[Fraction(0),0,0]
    new_cost=[Fraction(0),0,0]
    for tid in sorted(old):
        a,b=old[tid],new[tid]
        if a.get("success") is True and b.get("success") is not True:
            success=False
        if a.get("safety_violation") is not True and b.get("safety_violation") is True:
            safety=False
        if b.get("success") is True and a.get("success") is not True:
            strict=True
        if a.get("safety_violation") is True and b.get("safety_violation") is not True:
            strict=True
        old_cost[0]+=_f(a.get("wall_clock",0),"wall_clock")
        new_cost[0]+=_f(b.get("wall_clock",0),"wall_clock")
        old_cost[1]+=_count(a.get("reality_calls",0),"reality_calls")
        new_cost[1]+=_count(b.get("reality_calls",0),"reality_calls")
        old_cost[2]+=_count(a.get("information_actions",0),"information_actions")
        new_cost[2]+=_count(b.get("information_actions",0),"information_actions")
    cost=all(n<=o for o,n in zip(old_cost,new_cost))
    strict=strict or any(n<o for o,n in zip(old_cost,new_cost))
    result={
        "matched_task_ids":sorted(old),
        "incumbent_strategy":incumbent,
        "candidate_strategy":candidate,
        "success_noninferior":success,
        "safety_noninferior":safety,
        "cost_noninferior":cost,
        "strict_improvement":strict,
        "preference_admissible":success and safety and cost and strict,
        "universal_superiority_claimed":False,
    }
    result["comparison_sha256"]=comparison_digest(result)
    return result

def compile_policy(*,environment_class:str,comparison:Mapping[str,Any],candidate_strategy:str,verification_receipt:Mapping[str,Any]):
    if comparison.get("preference_admissible") is not True:
        raise MetaLearningPolicyError("META_PREFERENCE_NOT_ADMISSIBLE")
    cls=str(environment_class or "").strip()
    candidate=str(candidate_strategy or "").strip()
    if not cls or not candidate:
        raise MetaLearningPolicyError("META_IDENTITY_REQUIRED")
    expected_digest=comparison_digest({k:v for k,v in comparison.items() if k!="comparison_sha256"})
    if comparison.get("comparison_sha256")!=expected_digest:
        raise MetaLearningPolicyError("META_COMPARISON_DIGEST_MISMATCH")
    if comparison.get("candidate_strategy")!=candidate:
        raise MetaLearningPolicyError("META_CANDIDATE_BINDING_MISMATCH")
    if verification_receipt.get("independent_verified") is not True or verification_receipt.get("exact_byte_bound") is not True or verification_receipt.get("conclusion")!="success":
        raise MetaLearningPolicyError("META_VERIFICATION_RECEIPT_INVALID")
    rid=str(verification_receipt.get("receipt_id") or "").strip()
    if not rid:
        raise MetaLearningPolicyError("META_RECEIPT_ID_REQUIRED")
    if str(verification_receipt.get("environment_class") or "").strip()!=cls:
        raise MetaLearningPolicyError("META_RECEIPT_ENVIRONMENT_BINDING_MISMATCH")
    if str(verification_receipt.get("candidate_strategy") or "").strip()!=candidate:
        raise MetaLearningPolicyError("META_RECEIPT_STRATEGY_BINDING_MISMATCH")
    if verification_receipt.get("comparison_sha256")!=expected_digest:
        raise MetaLearningPolicyError("META_RECEIPT_COMPARISON_BINDING_MISMATCH")
    return {
        "environment_class":cls,
        "preferred_learning_strategy":candidate,
        "scope":"MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY",
        "fallback":"UNIVERSAL_LEARNING_DECISION_ROUTER_V3",
        "verification_receipt":rid,
        "comparison_sha256":expected_digest,
        "universal_superiority_claimed":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authorized":False,
    }
