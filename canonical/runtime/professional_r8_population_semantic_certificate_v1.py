"""Bounded R8 frozen-population semantic certificate.

Certifies the meaning of one exact delegation evaluation population: identity,
size, deterministic slot generation, required classes, and no adaptive
selection/replacement/tuning. It does not establish constituency support,
operator generalization, measurement invariance, or social/reactivity closure.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R8_POPULATION_SEMANTIC_CERTIFICATE_V1"
SOURCE_SCHEMA="PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1"

REQUIRED_VERIFIED={
    "FROZEN_BINDING_MANIFEST_INVARIANTS_PASS",
    "FRESH_512_CASE_PRE_BEACON_POPULATION_PASSES",
    "ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
    "ZERO_CASE_REPLACEMENT",
    "ZERO_ADAPTIVE_CASE_SELECTION",
    "ZERO_TUNING_REPLAY",
}
REQUIRED_CLASSES={
    "BASE_PARALLEL",
    "RESOURCE_CONFLICT",
    "WORKER_UNAVAILABLE",
    "STEP_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
}
REQUIRED_NONCLAIMS={
    "NO_CONSTITUENCY_SUPPORT_CLAIM",
    "NO_PRESENTER_OR_OPERATOR_GENERALIZATION",
    "NO_MEASUREMENT_INVARIANCE_CLAIM",
    "NO_SOCIAL_INFLUENCE_OR_REACTIVITY_CLOSURE",
    "NO_GLOBAL_R8_SEMANTIC_LEAF_CLOSURE",
    "NO_GLOBAL_R8_ROOT_CLOSURE",
}

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(x:Any)->str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()

def certify(source:Mapping[str,Any], binding:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(source,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["SOURCE_NOT_OBJECT"],"terminal_authority":False}
    if not isinstance(binding,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_NOT_OBJECT"],"terminal_authority":False}

    if source.get("schema")!=SOURCE_SCHEMA:
        errors.append("SOURCE_SCHEMA_INVALID")
    if source.get("status")!="INDEPENDENT_PASS__EXACT_CURRENT_512_CASE_BINDING_PREFLIGHT__ZERO_TERMINAL_RESULT":
        errors.append("SOURCE_STATUS_INVALID")
    if not REQUIRED_VERIFIED <= set(source.get("verified") or []):
        errors.append("SOURCE_REQUIRED_POPULATION_PROPERTIES_MISSING")
    if source.get("terminal_results_observed")!=0:
        errors.append("TERMINAL_RESULT_OVERCLAIM")
    if binding.get("source_sha256")!=digest(dict(source)):
        errors.append("SOURCE_DIGEST_MISMATCH")

    sem=binding.get("semantic_claim")
    if not isinstance(sem,Mapping):
        errors.append("SEMANTIC_CLAIM_INVALID")
    else:
        expected={
            "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
            "route_population_version":"DELEGATION_WHOLE_SCOPE_TERMINAL_POP_V1",
            "sample_count":512,
            "slot_generation":"DETERMINISTIC_COMMITMENT_BEACON_INDEX_DERIVATION",
            "acceptance_rule":"ALL_512_CASES_EXACT_PASS_AND_ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
            "case_replacement":False,
            "adaptive_case_selection":False,
            "replay_for_tuning":False,
            "post_freeze_terminal_result_claimed":False,
        }
        for field,value in expected.items():
            if sem.get(field)!=value:
                errors.append("SEMANTIC_POLICY_INVALID:"+field)
        if set(sem.get("required_case_classes") or [])!=REQUIRED_CLASSES:
            errors.append("REQUIRED_CASE_CLASSES_INVALID")

    nonclaims=set(binding.get("hard_nonclaims") or [])
    if not REQUIRED_NONCLAIMS <= nonclaims:
        errors.append("REQUIRED_NONCLAIMS_MISSING")

    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__EXACT_FROZEN_DELEGATION_POPULATION_SEMANTICS_BOUND" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "source_sha256":digest(dict(source)),
        "claim_scope":{
            "kind":"FROZEN_512_CASE_DELEGATION_POPULATION_SEMANTICS",
            "guarantees":[
                "POPULATION_IDENTITY_IS_BEHAVIOR_AND_VERSION_BOUND",
                "POPULATION_SIZE_IS_EXACTLY_512",
                "SLOT_GENERATION_IS_DETERMINISTIC_FROM_COMMITMENT_BEACON_AND_INDEX",
                "ALL_SIX_DECLARED_DELEGATION_CASE_CLASSES_ARE_REQUIRED",
                "ALL_512_CASES_MUST_PASS",
                "CASE_REPLACEMENT_ADAPTIVE_SELECTION_AND_TUNING_REPLAY_ARE_FORBIDDEN",
                "POST_FREEZE_TERMINAL_RESULT_IS_NOT_INFERRED_FROM_PREFLIGHT",
            ],
            "limitations":sorted(REQUIRED_NONCLAIMS),
        },
        "semantic_leaf_credit":False,
        "global_leaf_closure":False,
        "global_root_closure":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
