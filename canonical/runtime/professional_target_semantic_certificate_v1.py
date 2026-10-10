"""Bounded R1 target-semantics certificate for one canonical professional behavior.

This checker does not interpret arbitrary natural language. It verifies that the
canonical PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001 behavioral
contract exposes the target-defining parameters and semantics required for a
claim-scoped R1 contribution, and that the binding does not strengthen the
contract into a unique-optimum or arbitrary-source-completeness claim.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TARGET_SEMANTIC_CERTIFICATE_V1"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"

EXPECTED_INPUT_ANCHORS=(
    "User objective",
    "audience",
    "source evidence",
    "artifact type",
    "constraints",
    "current draft/render",
)
REQUIRED_FIELDS=(
    "behavior_id","inputs","environment_state","allowed_information",
    "required_output_or_action","success_condition","failure_condition",
    "terminal_consequence","verification_route","dependency_boundary","scope",
)

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(x:Any)->str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()

def certify(contract:Mapping[str,Any], binding:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(contract,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["CONTRACT_NOT_OBJECT"],"terminal_authority":False}
    if not isinstance(binding,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_NOT_OBJECT"],"terminal_authority":False}

    if contract.get("behavior_id")!=BEHAVIOR_ID:
        errors.append("BEHAVIOR_ID_MISMATCH")
    for field in REQUIRED_FIELDS:
        value=contract.get(field)
        if not isinstance(value,str) or not value.strip():
            errors.append("REQUIRED_CONTRACT_FIELD_MISSING:"+field)

    inputs=str(contract.get("inputs") or "")
    for anchor in EXPECTED_INPUT_ANCHORS:
        if anchor not in inputs:
            errors.append("TARGET_PARAMETER_ANCHOR_MISSING:"+anchor)

    if binding.get("behavior_id")!=BEHAVIOR_ID:
        errors.append("BINDING_BEHAVIOR_ID_MISMATCH")
    if binding.get("contract_sha256")!=digest(dict(contract)):
        errors.append("CONTRACT_DIGEST_MISMATCH")

    required_roles={
        "objective":"required_output_or_action",
        "audience":"inputs",
        "hard_constraints":"allowed_information",
        "success_semantics":"success_condition",
        "failure_semantics":"failure_condition",
        "target_construct":"success_condition",
        "claim_scope":"scope",
        "evidence_boundary":"dependency_boundary",
    }
    role_bindings=binding.get("role_bindings")
    if not isinstance(role_bindings,Mapping):
        errors.append("ROLE_BINDINGS_INVALID")
        role_bindings={}
    for role,field in required_roles.items():
        row=role_bindings.get(role)
        if not isinstance(row,Mapping):
            errors.append("ROLE_BINDING_MISSING:"+role)
            continue
        if row.get("source_field")!=field:
            errors.append("ROLE_SOURCE_FIELD_INVALID:"+role)
        if row.get("source_value_sha256")!=digest(contract.get(field)):
            errors.append("ROLE_SOURCE_VALUE_STALE:"+role)

    ambiguity=binding.get("ambiguity_policy")
    if not isinstance(ambiguity,Mapping):
        errors.append("AMBIGUITY_POLICY_INVALID")
    else:
        if ambiguity.get("unique_optimum_claimed") is not False:
            errors.append("UNIQUE_OPTIMUM_OVERCLAIM")
        if ambiguity.get("admissible_plan_definition")!="ANY_PLAN_SATISFYING_SUCCESS_AND_AVOIDING_FAILURE_WITHIN_DECLARED_SCOPE":
            errors.append("ADMISSIBLE_PLAN_DEFINITION_INVALID")
        if ambiguity.get("unresolved_runtime_task_ambiguity_must_remain_open") is not True:
            errors.append("RUNTIME_AMBIGUITY_FAIL_CLOSED_RULE_MISSING")

    nonclaims=set(binding.get("hard_nonclaims") or [])
    required_nonclaims={
        "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
        "NO_SOURCE_EXTRACTION_COMPLETENESS",
        "NO_UNIQUE_BEST_PLAN",
        "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
        "NO_GLOBAL_R1_ROOT_CLOSURE",
    }
    if not required_nonclaims <= nonclaims:
        errors.append("REQUIRED_NONCLAIMS_MISSING")

    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__EXACT_PARAMETERIZED_TARGET_SEMANTICS_BOUND" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "behavior_id":BEHAVIOR_ID,
        "contract_sha256":digest(dict(contract)),
        "parameter_anchors":list(EXPECTED_INPUT_ANCHORS),
        "role_bindings_verified":sorted(required_roles) if not errors else [],
        "claim_scope":{
            "kind":"EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS",
            "behavior_id":BEHAVIOR_ID,
            "guarantees":[
                "OBJECTIVE_AUDIENCE_EVIDENCE_ARTIFACT_TYPE_CONSTRAINTS_AND_CURRENT_DRAFT_ARE_EXPLICIT_RUNTIME_PARAMETERS",
                "SUCCESS_FAILURE_TARGET_CONSTRUCT_SCOPE_AND_EVIDENCE_BOUNDARY_ARE_BOUND_TO_EXACT_CONTRACT_FIELDS",
                "CONTRACT_TARGET_DRIFT_FAILS_CLOSED_BY_CONTENT_DIGEST",
                "UNIQUE_OPTIMUM_IS_NOT_INFERRED_FROM_NONUNIQUE_SUCCESS_SEMANTICS",
                "UNRESOLVED_RUNTIME_TASK_AMBIGUITY_REMAINS_OPEN",
            ],
            "limitations":sorted(required_nonclaims),
        },
        "semantic_leaf_credit":False,
        "global_leaf_closure":False,
        "global_root_closure":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
