"""Universal Learning V9 meta-optimizer router.

V9 strictly extends V8:
- verified matched evidence may select a preferred learning strategy for a
  verified environment class,
- transfer to another class requires an independent exact/superset relation,
- verified strategies may recursively induce higher-level meta-strategy
  candidates, but no candidate self-certifies.

V8 remains load-bearing for task/learning routing and safety. V9 supplies a
verified learning-strategy choice only; it grants no task execution authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import learning_strategy_optimizer_v9 as opt
from canonical.runtime import meta_strategy_abstraction_v9 as msa
from canonical.runtime import universal_learning_equivalence_basis_router_v8 as v8

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_META_ROUTER_V9"


def route(
    *,
    v8_args: Mapping[str,Any],
    environment_class:str,
    verified_policies:Sequence[Mapping[str,Any]]=(),
    class_mappings:Sequence[Mapping[str,Any]]=(),
    meta_strategy_sources:Sequence[Mapping[str,Any]]=(),
    meta_strategy_verification_receipt:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    base=v8.route(**dict(v8_args))
    selection=opt.select_strategy(
        environment_class=environment_class,
        policies=verified_policies,
        class_mappings=class_mappings,
    )

    meta_candidate=None
    meta_result=None
    meta_status="NOT_REQUESTED"
    if meta_strategy_sources:
        meta_candidate=msa.induce_candidate(meta_strategy_sources)
        meta_status=meta_candidate["status"]
        if meta_strategy_verification_receipt is not None:
            meta_result=msa.verify_candidate(
                candidate=meta_candidate,
                verification_receipt=meta_strategy_verification_receipt,
            )
            meta_status=meta_result["status"]

    return {
        "schema":SCHEMA,
        "status":"V9_VERIFIED_META_LEARNING_POLICY_APPLIED",
        "v8_result":base,
        "route":base.get("route"),
        "reason":"V9_MAY_SELECT_A_VERIFIED_LEARNING_STRATEGY_BUT_V8_REMAINS_LOAD_BEARING_TASK_AND_TRUST_AUTHORITY",
        "next_action":base.get("next_action"),
        "trusted_execution_authorized":base.get("trusted_execution_authorized",False),
        "empirical_information_action_authorized":base.get("empirical_information_action_authorized",False),
        "learning_strategy_selection":selection,
        "preferred_learning_strategy":selection.get("preferred_learning_strategy"),
        "learning_strategy_selection_authorized":selection.get("selection_authorized",False),
        "meta_strategy_candidate":meta_candidate,
        "meta_strategy_result":meta_result,
        "meta_strategy_status":meta_status,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }


def prove_v9_invariants()->dict[str,Any]:
    errors=[]

    episodes=[
        {"strategy_id":"old","task_id":"t","verified":True,"success":True,"safety_violation":False,
         "wall_clock":"10","reality_calls":1,"information_actions":3},
        {"strategy_id":"new","task_id":"t","verified":True,"success":True,"safety_violation":False,
         "wall_clock":"5","reality_calls":1,"information_actions":2},
    ]
    comparison=opt.meta.compare(episodes=episodes,incumbent="old",candidate="new")
    comparison_receipt={
        "receipt_id":"cmp","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "environment_class":"api-like","candidate_strategy":"new",
        "comparison_sha256":comparison["comparison_sha256"],
    }
    policy_candidate=opt.build_policy_candidate(
        episodes=episodes,incumbent_strategy="old",candidate_strategy="new",
        environment_class="api-like",comparison_verification_receipt=comparison_receipt,
    )
    policy_receipt={
        "receipt_id":"policy","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "environment_class":"api-like","strategy_id":"new",
        "policy_sha256":policy_candidate["policy_sha256"],
    }
    policy=opt.verify_policy_candidate(candidate=policy_candidate,policy_artifact_receipt=policy_receipt)
    exact=opt.select_strategy(environment_class="api-like",policies=[policy])
    if exact.get("preferred_learning_strategy")!="new" or exact.get("selection_authorized") is not True:
        errors.append("VERIFIED_EXACT_STRATEGY_SELECTION_BROKEN")

    md=opt.class_mapping_digest(
        source_class="api-like",target_class="schema-api",strategy_id="new",
        relation="SOURCE_PROVEN_SUPERSET_OF_TARGET",
    )
    mapped=opt.select_strategy(
        environment_class="schema-api",policies=[policy],
        class_mappings=[{
            "source_class":"api-like","target_class":"schema-api","strategy_id":"new",
            "relation":"SOURCE_PROVEN_SUPERSET_OF_TARGET",
            "verification_receipt":{
                "receipt_id":"map","independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","strategy_behavior_preserved_on_target":True,
                "source_class":"api-like","target_class":"schema-api","strategy_id":"new",
                "relation":"SOURCE_PROVEN_SUPERSET_OF_TARGET","mapping_sha256":md,
            },
        }],
    )
    if mapped.get("preferred_learning_strategy")!="new" or mapped.get("selection_authorized") is not True:
        errors.append("PROOF_GATED_CLASS_TRANSFER_BROKEN")

    def source(sid,level,sig):
        dg=msa.signature_digest(sig)
        return {
            "strategy_id":sid,"meta_level":level,"canonical_strategy_signature":sig,
            "verification_receipt":{
                "receipt_id":"vr-"+sid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","behavior_verified":True,
                "strategy_id":sid,"meta_level":level,"canonical_signature_sha256":dg,
            },
        }

    cand=msa.induce_candidate([
        source("s1",0,["hypothesize","probe","verify"]),
        source("s2",0,["transfer","probe","verify"]),
    ])
    if cand.get("verified_meta_strategy") is not False or cand.get("recursive_reuse_authorized") is not False:
        errors.append("META_CANDIDATE_SELF_TRUST_BROKEN")
    vrec={
        "receipt_id":"meta-proof","independent_verified":True,"exact_byte_bound":True,
        "conclusion":"success","behavior_verified":True,
        "behavior_preserving_across_source_strategies":True,
        "candidate_sha256":cand["candidate_sha256"],"strategy_id":cand["strategy_id"],
        "meta_level":cand["meta_level"],"source_strategy_ids":cand["source_strategy_ids"],
        "canonical_signature_sha256":cand["canonical_signature_sha256"],"scope_relation":"EXACT",
    }
    verified=msa.verify_candidate(candidate=cand,verification_receipt=vrec)
    next_cand=msa.induce_candidate([
        verified,
        source("s3",0,["probe","verify","compress"]),
    ])
    if next_cand.get("meta_level")!=2:
        errors.append("RECURSIVE_META_ABSTRACTION_BROKEN")

    base=v8.prove_v8_invariants()
    if base.get("pass") is not True:
        errors.append("V8_BASE_INVARIANTS_NOT_PRESERVED")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V9_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "v8_base_preserved":base.get("pass") is True,
        "matched_verified_strategy_selection":passed,
        "proof_gated_environment_class_transfer":passed,
        "meta_candidate_no_self_certification":passed,
        "recursive_meta_abstraction":passed,
        "semantic_success_rate_proved":False,
        "unknown_domain_acceptance_proved":False,
        "universal_strategy_superiority_proved":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "incremental_spend_usd":0,
    }
