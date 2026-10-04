"""Proof-gated one-way context morphisms for Universal Learning V10.

A morphism is not a similarity score. It is an independently verified claim that,
for one learning strategy, the target context preserves the strategy-relevant
preconditions, performance metric semantics, and invalidator boundary required
to transport conservative source evidence.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CONTEXT_MORPHISM_V10"
REQUIRED_METRICS={"BURDEN_REDUCTION","WALL_CLOCK","RISK"}

class ContextMorphismError(ValueError): pass

def _s(x:Any)->str: return " ".join(str(x or "").split())
def _items(xs): return tuple(sorted({_s(x) for x in (xs or []) if _s(x)}))

def morphism_digest(*,source_context_sha256:str,target_context_sha256:str,strategy_id:str,
                    preserved_preconditions,preserved_metric_semantics,invalidators_checked)->str:
    src=_s(source_context_sha256); dst=_s(target_context_sha256); sid=_s(strategy_id)
    pre=_items(preserved_preconditions); metrics=_items(preserved_metric_semantics); inv=_items(invalidators_checked)
    if not src or not dst or not sid or not pre or not inv:
        raise ContextMorphismError("MORPHISM_FIELDS_REQUIRED")
    if not REQUIRED_METRICS.issubset(set(metrics)):
        raise ContextMorphismError("REQUIRED_METRIC_SEMANTICS_NOT_PRESERVED")
    body=json.dumps({
        "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
        "preserved_preconditions":pre,"preserved_metric_semantics":metrics,
        "invalidators_checked":inv,
    },sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def verify(*,raw:Mapping[str,Any],expected_source_context_sha256:str,
           expected_target_context_sha256:str,expected_strategy_id:str)->dict[str,Any]:
    src=_s(raw.get("source_context_sha256")); dst=_s(raw.get("target_context_sha256"))
    sid=_s(raw.get("strategy_id"))
    if src!=_s(expected_source_context_sha256) or dst!=_s(expected_target_context_sha256):
        raise ContextMorphismError("CONTEXT_BINDING_MISMATCH")
    if sid!=_s(expected_strategy_id):
        raise ContextMorphismError("STRATEGY_BINDING_MISMATCH")
    pre=_items(raw.get("preserved_preconditions"))
    metrics=_items(raw.get("preserved_metric_semantics"))
    inv=_items(raw.get("invalidators_checked"))
    digest=morphism_digest(
        source_context_sha256=src,target_context_sha256=dst,strategy_id=sid,
        preserved_preconditions=pre,preserved_metric_semantics=metrics,invalidators_checked=inv)
    r=raw.get("verification_receipt")
    if not isinstance(r,Mapping):
        raise ContextMorphismError("MORPHISM_RECEIPT_REQUIRED")
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise ContextMorphismError("MORPHISM_RECEIPT_INVALID")
    required=(
        r.get("strategy_applicability_preserved") is True
        and r.get("performance_metric_semantics_preserved") is True
        and r.get("no_new_strategy_invalidators") is True
        and r.get("conservative_performance_transport_valid") is True
    )
    if not required:
        raise ContextMorphismError("MORPHISM_SEMANTIC_PROOF_INCOMPLETE")
    if _s(r.get("source_context_sha256"))!=src or _s(r.get("target_context_sha256"))!=dst:
        raise ContextMorphismError("MORPHISM_RECEIPT_CONTEXT_MISMATCH")
    if _s(r.get("strategy_id"))!=sid or r.get("morphism_sha256")!=digest:
        raise ContextMorphismError("MORPHISM_RECEIPT_BINDING_MISMATCH")
    return {
        "schema":SCHEMA,"status":"VERIFIED_ONE_WAY_CONTEXT_MORPHISM",
        "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
        "preserved_preconditions":list(pre),"preserved_metric_semantics":list(metrics),
        "invalidators_checked":list(inv),"morphism_sha256":digest,
        "performance_transport_authorized":True,
        "execution_authority":False,"promotion_authority":False,
    }
