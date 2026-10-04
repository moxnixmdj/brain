"""Verified learning-strategy optimizer for Universal Learning V9.

A learning strategy may become preferred only after matched verified evidence
shows noninferior success/safety/cost and at least one strict improvement
through meta_learning_policy_v2. Applying that preference to a different
environment class requires a separate exact-byte-bound class-relation receipt.

No policy selection authorizes task execution or weakens lower-stack gates.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import meta_learning_policy_v2 as meta

SCHEMA="PROJECT_BRAIN_LEARNING_STRATEGY_OPTIMIZER_V9"
RELATIONS={"EXACT","SOURCE_PROVEN_SUPERSET_OF_TARGET"}


class LearningStrategyOptimizerError(ValueError):
    pass


def _s(x:Any)->str:
    return " ".join(str(x or "").split())


def policy_digest(policy:Mapping[str,Any])->str:
    payload={
        "environment_class":_s(policy.get("environment_class")),
        "preferred_learning_strategy":_s(policy.get("preferred_learning_strategy")),
        "scope":_s(policy.get("scope")),
        "fallback":_s(policy.get("fallback")),
        "comparison_sha256":_s(policy.get("comparison_sha256")),
        "universal_superiority_claimed":bool(policy.get("universal_superiority_claimed",False)),
    }
    if not payload["environment_class"] or not payload["preferred_learning_strategy"] or not payload["comparison_sha256"]:
        raise LearningStrategyOptimizerError("POLICY_PAYLOAD_INVALID")
    body=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()


def build_policy_candidate(
    *,
    episodes:Sequence[Mapping[str,Any]],
    incumbent_strategy:str,
    candidate_strategy:str,
    environment_class:str,
    comparison_verification_receipt:Mapping[str,Any],
)->dict[str,Any]:
    comp=meta.compare(
        episodes=episodes,
        incumbent=incumbent_strategy,
        candidate=candidate_strategy,
    )
    base=meta.compile_policy(
        environment_class=environment_class,
        comparison=comp,
        candidate_strategy=candidate_strategy,
        verification_receipt=comparison_verification_receipt,
    )
    digest=policy_digest(base)
    return {
        "schema":SCHEMA,
        **base,
        "policy_sha256":digest,
        "verified_policy":False,
        "candidate_only":True,
        "selection_authority":"NONE_UNTIL_INDEPENDENT_POLICY_ARTIFACT_VERIFICATION",
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }


def verify_policy_candidate(*,candidate:Mapping[str,Any],policy_artifact_receipt:Mapping[str,Any])->dict[str,Any]:
    expected=policy_digest(candidate)
    if candidate.get("policy_sha256")!=expected:
        raise LearningStrategyOptimizerError("POLICY_CANDIDATE_DIGEST_INVALID")
    r=policy_artifact_receipt
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion")!="success"
    ):
        raise LearningStrategyOptimizerError("POLICY_ARTIFACT_RECEIPT_INVALID")
    env=_s(candidate.get("environment_class"))
    strategy=_s(candidate.get("preferred_learning_strategy"))
    if _s(r.get("environment_class"))!=env:
        raise LearningStrategyOptimizerError("POLICY_ARTIFACT_ENVIRONMENT_MISMATCH")
    if _s(r.get("strategy_id"))!=strategy:
        raise LearningStrategyOptimizerError("POLICY_ARTIFACT_STRATEGY_MISMATCH")
    if r.get("policy_sha256")!=expected:
        raise LearningStrategyOptimizerError("POLICY_ARTIFACT_DIGEST_MISMATCH")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise LearningStrategyOptimizerError("POLICY_ARTIFACT_RECEIPT_ID_REQUIRED")
    return {
        **dict(candidate),
        "verified_policy":True,
        "candidate_only":False,
        "selection_authority":"MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY",
        "policy_verification_receipt":dict(r),
    }


def compile_verified_policy(
    *,
    episodes:Sequence[Mapping[str,Any]],
    incumbent_strategy:str,
    candidate_strategy:str,
    environment_class:str,
    comparison_verification_receipt:Mapping[str,Any],
    policy_artifact_receipt:Mapping[str,Any],
)->dict[str,Any]:
    candidate=build_policy_candidate(
        episodes=episodes,
        incumbent_strategy=incumbent_strategy,
        candidate_strategy=candidate_strategy,
        environment_class=environment_class,
        comparison_verification_receipt=comparison_verification_receipt,
    )
    return verify_policy_candidate(candidate=candidate,policy_artifact_receipt=policy_artifact_receipt)

def _verified_policy(raw:Mapping[str,Any])->dict[str,Any]:
    if raw.get("verified_policy") is not True:
        raise LearningStrategyOptimizerError("UNVERIFIED_POLICY")
    expected=policy_digest(raw)
    if raw.get("policy_sha256")!=expected:
        raise LearningStrategyOptimizerError("POLICY_DIGEST_MISMATCH")
    r=raw.get("policy_verification_receipt")
    if not isinstance(r,Mapping):
        raise LearningStrategyOptimizerError("POLICY_RECEIPT_REQUIRED")
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion")!="success"
        or r.get("policy_sha256")!=expected
    ):
        raise LearningStrategyOptimizerError("POLICY_RECEIPT_INVALID")
    if _s(r.get("environment_class"))!=_s(raw.get("environment_class")):
        raise LearningStrategyOptimizerError("POLICY_RECEIPT_ENVIRONMENT_MISMATCH")
    if _s(r.get("strategy_id"))!=_s(raw.get("preferred_learning_strategy")):
        raise LearningStrategyOptimizerError("POLICY_RECEIPT_STRATEGY_MISMATCH")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise LearningStrategyOptimizerError("POLICY_RECEIPT_ID_REQUIRED")
    return dict(raw)


def class_mapping_digest(*,source_class:str,target_class:str,strategy_id:str,relation:str)->str:
    src=_s(source_class);tgt=_s(target_class);sid=_s(strategy_id);rel=_s(relation)
    if not src or not tgt or not sid or rel not in RELATIONS:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_INVALID")
    body=json.dumps(
        {"source_class":src,"target_class":tgt,"strategy_id":sid,"relation":rel},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    ).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()


def _mapping(raw:Mapping[str,Any],*,policy:Mapping[str,Any],target_class:str)->dict[str,Any]:
    src=_s(raw.get("source_class"));tgt=_s(raw.get("target_class"))
    sid=_s(raw.get("strategy_id"));rel=_s(raw.get("relation"))
    if src!=_s(policy.get("environment_class")) or tgt!=_s(target_class):
        raise LearningStrategyOptimizerError("CLASS_MAPPING_SCOPE_MISMATCH")
    if sid!=_s(policy.get("preferred_learning_strategy")) or rel not in RELATIONS:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_STRATEGY_OR_RELATION_INVALID")
    expected=class_mapping_digest(source_class=src,target_class=tgt,strategy_id=sid,relation=rel)
    r=raw.get("verification_receipt")
    if not isinstance(r,Mapping):
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_REQUIRED")
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion")!="success"
        or r.get("strategy_behavior_preserved_on_target") is not True
    ):
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_INVALID")
    if r.get("mapping_sha256")!=expected:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_DIGEST_MISMATCH")
    if _s(r.get("source_class"))!=src or _s(r.get("target_class"))!=tgt:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_SCOPE_MISMATCH")
    if _s(r.get("strategy_id"))!=sid or _s(r.get("relation"))!=rel:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_RELATION_MISMATCH")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise LearningStrategyOptimizerError("CLASS_MAPPING_RECEIPT_ID_REQUIRED")
    return {
        "source_class":src,"target_class":tgt,"strategy_id":sid,"relation":rel,
        "mapping_sha256":expected,"verification_receipt":rid,
    }


def select_strategy(
    *,
    environment_class:str,
    policies:Sequence[Mapping[str,Any]],
    class_mappings:Sequence[Mapping[str,Any]]=(),
)->dict[str,Any]:
    target=_s(environment_class)
    if not target:
        raise LearningStrategyOptimizerError("TARGET_ENVIRONMENT_CLASS_REQUIRED")
    ps=[_verified_policy(x) for x in policies]
    if len({_s(x.get("environment_class")) for x in ps})!=len(ps):
        raise LearningStrategyOptimizerError("DUPLICATE_POLICY_ENVIRONMENT_CLASS")

    exact=[p for p in ps if _s(p.get("environment_class"))==target]
    if exact:
        strategies={_s(p.get("preferred_learning_strategy")) for p in exact}
        if len(strategies)!=1:
            raise LearningStrategyOptimizerError("CONFLICTING_EXACT_POLICIES")
        p=exact[0]
        return {
            "schema":SCHEMA,"status":"VERIFIED_EXACT_CLASS_STRATEGY",
            "environment_class":target,"preferred_learning_strategy":_s(p["preferred_learning_strategy"]),
            "source_environment_class":target,"relation":"EXACT_POLICY_SCOPE",
            "policy_sha256":p["policy_sha256"],"class_mapping_receipts":[],
            "selection_authorized":True,"universal_superiority_claimed":False,
            "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
        }

    by_class={_s(p.get("environment_class")):p for p in ps}
    admitted=[]
    for raw in class_mappings:
        src=_s(raw.get("source_class"))
        if src not in by_class or _s(raw.get("target_class"))!=target:
            continue
        admitted.append((_mapping(raw,policy=by_class[src],target_class=target),by_class[src]))

    if not admitted:
        return {
            "schema":SCHEMA,"status":"NO_VERIFIED_STRATEGY_FOR_CLASS__FALLBACK_V8",
            "environment_class":target,"preferred_learning_strategy":None,
            "selection_authorized":False,
            "fallback":"UNIVERSAL_LEARNING_EQUIVALENCE_BASIS_ROUTER_V8",
            "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
        }

    strategies={m["strategy_id"] for m,_ in admitted}
    if len(strategies)!=1:
        raise LearningStrategyOptimizerError("CONFLICTING_TRANSFERRED_STRATEGIES")
    strategy=next(iter(strategies))
    return {
        "schema":SCHEMA,"status":"VERIFIED_TRANSFERRED_CLASS_STRATEGY",
        "environment_class":target,"preferred_learning_strategy":strategy,
        "source_environment_classes":sorted({m["source_class"] for m,_ in admitted}),
        "relations":sorted({m["relation"] for m,_ in admitted}),
        "class_mapping_receipts":sorted(m["verification_receipt"] for m,_ in admitted),
        "selection_authorized":True,"universal_superiority_claimed":False,
        "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
    }
