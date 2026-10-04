"""Recursive meta-strategy abstraction for Universal Learning V9."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_META_STRATEGY_ABSTRACTION_V9"
class MetaStrategyError(ValueError): pass
def _s(x): return " ".join(str(x or "").split())
def _items(xs): return tuple(sorted({_s(x) for x in (xs or []) if _s(x)}))

def skeleton_digest(steps)->str:
    ss=_items(steps)
    if not ss: raise MetaStrategyError("STEPS_REQUIRED")
    return "sha256:"+hashlib.sha256(json.dumps({"steps":ss},sort_keys=True,separators=(",",":")).encode()).hexdigest()

def induce_candidate(strategies:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if len(strategies)<2: raise MetaStrategyError("AT_LEAST_TWO_STRATEGIES_REQUIRED")
    common=None; source_ids=[]
    for s in strategies:
        sid=_s(s.get("strategy_id")); steps=_items(s.get("steps"))
        if not sid or not steps: raise MetaStrategyError("STRATEGY_INVALID")
        r=s.get("verification_receipt")
        if not isinstance(r,Mapping) or r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
            raise MetaStrategyError("STRATEGY_RECEIPT_INVALID:"+sid)
        if r.get("strategy_id")!=sid or r.get("skeleton_sha256")!=skeleton_digest(steps):
            raise MetaStrategyError("STRATEGY_RECEIPT_BINDING_MISMATCH:"+sid)
        common=set(steps) if common is None else common & set(steps)
        source_ids.append(sid)
    if not common: raise MetaStrategyError("NO_COMMON_META_STRATEGY_STRUCTURE")
    common_steps=sorted(common)
    body=json.dumps({"source_strategy_ids":sorted(source_ids),"common_steps":common_steps},sort_keys=True,separators=(",",":")).encode()
    return {
        "schema":SCHEMA,"status":"META_STRATEGY_ABSTRACTION_CANDIDATE",
        "source_strategy_ids":sorted(source_ids),"common_steps":common_steps,
        "candidate_sha256":"sha256:"+hashlib.sha256(body).hexdigest(),
        "verified_abstraction":False,"reuse_authorized":False,
        "separate_independent_behavior_preservation_required":True,
        "promotion_authority":False,"acceptance_credit_delta":0,"ownership_credit_delta":0
    }
