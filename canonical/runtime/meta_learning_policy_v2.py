from fractions import Fraction
from typing import Any, Mapping, Sequence

class MetaLearningPolicyError(ValueError):
    pass

def _f(x):
    return x if isinstance(x,Fraction) else Fraction(str(x))

def compare(*,episodes:Sequence[Mapping[str,Any]],incumbent:str,candidate:str):
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
    for tid in old:
        a,b=old[tid],new[tid]
        if a.get("success") is True and b.get("success") is not True:
            success=False
        if a.get("safety_violation") is not True and b.get("safety_violation") is True:
            safety=False
        if b.get("success") is True and a.get("success") is not True:
            strict=True
        if a.get("safety_violation") is True and b.get("safety_violation") is not True:
            strict=True
        old_cost[0]+=_f(a.get("wall_clock",0))
        new_cost[0]+=_f(b.get("wall_clock",0))
        old_cost[1]+=int(a.get("reality_calls",0))
        new_cost[1]+=int(b.get("reality_calls",0))
        old_cost[2]+=int(a.get("information_actions",0))
        new_cost[2]+=int(b.get("information_actions",0))
    cost=all(n<=o for o,n in zip(old_cost,new_cost))
    strict=strict or any(n<o for o,n in zip(old_cost,new_cost))
    return {
        "matched_task_ids":sorted(old),
        "success_noninferior":success,
        "safety_noninferior":safety,
        "cost_noninferior":cost,
        "strict_improvement":strict,
        "preference_admissible":success and safety and cost and strict,
        "universal_superiority_claimed":False,
    }

def compile_policy(*,environment_class:str,comparison:Mapping[str,Any],candidate_strategy:str,verification_receipt:Mapping[str,Any]):
    if comparison.get("preference_admissible") is not True:
        raise MetaLearningPolicyError("META_PREFERENCE_NOT_ADMISSIBLE")
    if verification_receipt.get("independent_verified") is not True or verification_receipt.get("exact_byte_bound") is not True or verification_receipt.get("conclusion")!="success":
        raise MetaLearningPolicyError("META_VERIFICATION_RECEIPT_INVALID")
    rid=str(verification_receipt.get("receipt_id") or "").strip()
    cls=str(environment_class or "").strip()
    if not rid or not cls:
        raise MetaLearningPolicyError("META_IDENTITY_REQUIRED")
    return {
        "environment_class":cls,
        "preferred_learning_strategy":str(candidate_strategy),
        "scope":"MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY",
        "fallback":"UNIVERSAL_LEARNING_DECISION_ROUTER_V3",
        "verification_receipt":rid,
        "universal_superiority_claimed":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authorized":False,
    }
