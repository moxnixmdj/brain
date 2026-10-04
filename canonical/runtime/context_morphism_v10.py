"""Proof-gated one-way context morphisms for Universal Learning V10.

Cross-context transport binds the exact canonical strategy semantics and the
exact independently verified source episode evidence being transported.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CONTEXT_MORPHISM_V10"
REQUIRED_METRICS={"BURDEN_REDUCTION","WALL_CLOCK","RISK"}

class ContextMorphismError(ValueError): pass

def _s(x:Any)->str: return " ".join(str(x or "").split())
def _items(xs): return tuple(sorted({_s(x) for x in (xs or []) if _s(x)}))

def _canonical_json(x:Any)->bytes:
    if not isinstance(x,Mapping) or not x:
        raise ContextMorphismError("STRATEGY_SEMANTICS_MAPPING_REQUIRED")
    try:
        return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    except Exception as exc:
        raise ContextMorphismError("STRATEGY_SEMANTICS_NOT_CANONICALIZABLE") from exc

def strategy_semantics_digest(*,strategy_id:str,strategy_semantics:Mapping[str,Any])->str:
    sid=_s(strategy_id)
    if not sid: raise ContextMorphismError("STRATEGY_ID_REQUIRED")
    body=json.dumps({
        "strategy_id":sid,
        "strategy_semantics_sha256":"sha256:"+hashlib.sha256(_canonical_json(strategy_semantics)).hexdigest(),
    },sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _episode_bindings(xs:Sequence[Mapping[str,Any]]):
    out=[]
    seen_ids=set()
    seen_digests=set()
    for raw in xs or ():
        eid=_s(raw.get("episode_id")); esha=_s(raw.get("episode_sha256"))
        if not eid or not esha:
            raise ContextMorphismError("SOURCE_EPISODE_BINDING_REQUIRED")
        if eid in seen_ids:
            raise ContextMorphismError("SOURCE_EPISODE_ID_DUPLICATE:"+eid)
        if esha in seen_digests:
            raise ContextMorphismError("SOURCE_EPISODE_DIGEST_DUPLICATE:"+esha)
        seen_ids.add(eid); seen_digests.add(esha)
        out.append({"episode_id":eid,"episode_sha256":esha})
    if not out:
        raise ContextMorphismError("SOURCE_EPISODE_BINDINGS_REQUIRED")
    return tuple(sorted(out,key=lambda x:(x["episode_id"],x["episode_sha256"])))

def source_episode_set_digest(*,strategy_sha256:str,episode_bindings:Sequence[Mapping[str,Any]])->str:
    sha=_s(strategy_sha256); bindings=_episode_bindings(episode_bindings)
    if not sha:
        raise ContextMorphismError("STRATEGY_SHA_REQUIRED")
    body=json.dumps(
        {"strategy_sha256":sha,"episode_bindings":bindings},
        sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def morphism_digest(*,source_context_sha256:str,target_context_sha256:str,strategy_id:str,
                    strategy_sha256:str,source_episode_set_sha256:str,
                    preserved_preconditions,preserved_metric_semantics,invalidators_checked)->str:
    src=_s(source_context_sha256); dst=_s(target_context_sha256); sid=_s(strategy_id)
    ssha=_s(strategy_sha256); esha=_s(source_episode_set_sha256)
    pre=_items(preserved_preconditions); metrics=_items(preserved_metric_semantics); inv=_items(invalidators_checked)
    if not src or not dst or not sid or not ssha or not esha or not pre or not inv:
        raise ContextMorphismError("MORPHISM_FIELDS_REQUIRED")
    if not REQUIRED_METRICS.issubset(set(metrics)):
        raise ContextMorphismError("REQUIRED_METRIC_SEMANTICS_NOT_PRESERVED")
    body=json.dumps({
        "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
        "strategy_sha256":ssha,"source_episode_set_sha256":esha,
        "preserved_preconditions":pre,"preserved_metric_semantics":metrics,
        "invalidators_checked":inv,
    },sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def verify(*,raw:Mapping[str,Any],expected_source_context_sha256:str,
           expected_target_context_sha256:str,expected_strategy_id:str,
           expected_strategy_semantics:Mapping[str,Any],
           expected_source_episode_bindings:Sequence[Mapping[str,Any]])->dict[str,Any]:
    src=_s(raw.get("source_context_sha256")); dst=_s(raw.get("target_context_sha256"))
    sid=_s(raw.get("strategy_id"))
    if src!=_s(expected_source_context_sha256) or dst!=_s(expected_target_context_sha256):
        raise ContextMorphismError("CONTEXT_BINDING_MISMATCH")
    if sid!=_s(expected_strategy_id):
        raise ContextMorphismError("STRATEGY_BINDING_MISMATCH")
    strategy_sha=strategy_semantics_digest(
        strategy_id=sid,strategy_semantics=expected_strategy_semantics)
    bindings=_episode_bindings(expected_source_episode_bindings)
    episode_set_sha=source_episode_set_digest(
        strategy_sha256=strategy_sha,episode_bindings=bindings)
    if _s(raw.get("strategy_sha256"))!=strategy_sha:
        raise ContextMorphismError("STRATEGY_SEMANTICS_BINDING_MISMATCH")
    if _s(raw.get("source_episode_set_sha256"))!=episode_set_sha:
        raise ContextMorphismError("SOURCE_EPISODE_SET_BINDING_MISMATCH")
    pre=_items(raw.get("preserved_preconditions"))
    metrics=_items(raw.get("preserved_metric_semantics"))
    inv=_items(raw.get("invalidators_checked"))
    digest=morphism_digest(
        source_context_sha256=src,target_context_sha256=dst,strategy_id=sid,
        strategy_sha256=strategy_sha,source_episode_set_sha256=episode_set_sha,
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
        and r.get("source_episodes_executed_bound_strategy") is True
        and r.get("canonical_strategy_semantics_complete_for_transport") is True
        and r.get("source_policy_evidence_complete_for_bound_strategy") is True
        and r.get("source_episodes_distinct_evidence_instances") is True
        and r.get("source_context_strategy_relevant_scope_complete") is True
        and r.get("target_context_strategy_relevant_scope_complete") is True
    )
    if not required:
        raise ContextMorphismError("MORPHISM_SEMANTIC_PROOF_INCOMPLETE")
    if _s(r.get("source_context_sha256"))!=src or _s(r.get("target_context_sha256"))!=dst:
        raise ContextMorphismError("MORPHISM_RECEIPT_CONTEXT_MISMATCH")
    if _s(r.get("strategy_id"))!=sid or _s(r.get("strategy_sha256"))!=strategy_sha:
        raise ContextMorphismError("MORPHISM_RECEIPT_STRATEGY_MISMATCH")
    if _s(r.get("source_episode_set_sha256"))!=episode_set_sha or r.get("morphism_sha256")!=digest:
        raise ContextMorphismError("MORPHISM_RECEIPT_BINDING_MISMATCH")
    return {
        "schema":SCHEMA,"status":"VERIFIED_ONE_WAY_CONTEXT_MORPHISM",
        "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
        "strategy_sha256":strategy_sha,"source_episode_set_sha256":episode_set_sha,
        "source_episode_bindings":[dict(x) for x in bindings],
        "preserved_preconditions":list(pre),"preserved_metric_semantics":list(metrics),
        "invalidators_checked":list(inv),"morphism_sha256":digest,
        "performance_transport_authorized":True,
        "execution_authority":False,"promotion_authority":False,
    }
