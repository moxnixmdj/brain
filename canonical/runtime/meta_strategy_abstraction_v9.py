"""Recursive ordered meta-strategy abstraction for Universal Learning V9."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_META_STRATEGY_ABSTRACTION_V9"
class MetaStrategyError(ValueError): pass
def _s(x): return " ".join(str(x or "").split())

def _seq(xs):
    out=tuple(_s(x) for x in (xs or []))
    if not out or any(not x for x in out): raise MetaStrategyError("STEPS_REQUIRED")
    return out

def skeleton_digest(steps)->str:
    ss=_seq(steps)
    return "sha256:"+hashlib.sha256(json.dumps({"steps":ss},separators=(",",":")).encode()).hexdigest()

def _lcs(a,b):
    n,m=len(a),len(b)
    dp=[[()]*(m+1) for _ in range(n+1)]
    for i in range(n-1,-1,-1):
        for j in range(m-1,-1,-1):
            if a[i]==b[j]:
                dp[i][j]=(a[i],)+dp[i+1][j+1]
            else:
                x,y=dp[i+1][j],dp[i][j+1]
                dp[i][j]=x if (len(x)>len(y) or (len(x)==len(y) and x<=y)) else y
    return dp[0][0]

def induce_candidate(strategies:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if len(strategies)<2: raise MetaStrategyError("AT_LEAST_TWO_STRATEGIES_REQUIRED")
    common=None; source_ids=[]; seen=set()
    for s in strategies:
        sid=_s(s.get("strategy_id")); steps=_seq(s.get("steps"))
        if not sid or sid in seen: raise MetaStrategyError("STRATEGY_ID_INVALID_OR_DUPLICATE")
        seen.add(sid)
        r=s.get("verification_receipt")
        if not isinstance(r,Mapping) or r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
            raise MetaStrategyError("STRATEGY_RECEIPT_INVALID:"+sid)
        if r.get("strategy_id")!=sid or r.get("skeleton_sha256")!=skeleton_digest(steps):
            raise MetaStrategyError("STRATEGY_RECEIPT_BINDING_MISMATCH:"+sid)
        common=steps if common is None else _lcs(common,steps)
        source_ids.append(sid)
    if not common: raise MetaStrategyError("NO_COMMON_META_STRATEGY_STRUCTURE")
    common_steps=list(common)
    body=json.dumps({"source_strategy_ids":sorted(source_ids),"common_steps":common_steps},sort_keys=True,separators=(",",":")).encode()
    return {
        "schema":SCHEMA,"status":"ORDERED_META_STRATEGY_ABSTRACTION_CANDIDATE",
        "source_strategy_ids":sorted(source_ids),"common_steps":common_steps,
        "candidate_sha256":"sha256:"+hashlib.sha256(body).hexdigest(),
        "abstraction_method":"EXACT_LONGEST_COMMON_SUBSEQUENCE_OVER_VERIFIED_ORDERED_STRATEGY_STEPS",
        "verified_abstraction":False,"reuse_authorized":False,
        "separate_independent_behavior_preservation_required":True,
        "promotion_authority":False,"acceptance_credit_delta":0,"ownership_credit_delta":0
    }
