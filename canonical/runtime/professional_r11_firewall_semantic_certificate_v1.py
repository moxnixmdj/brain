"""Bounded semantic certificate for clean-evaluation-lane firewall policy.

This checker certifies the meaning of one explicit governance policy. It does
not prove general adaptive security, prompt-injection resistance, Goodhart
closure, or holdout lifecycle completeness.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R11_FIREWALL_SEMANTIC_CERTIFICATE_V1"
GOV_SCHEMA="PROJECT_BRAIN_EVALUATION_INFORMATION_FIREWALL_GOVERNANCE_V1"

REQUIRED_RULES={
    "TASK_IDENTITY_EXPOSURE_IS_MONOTONIC_WITHIN_A_LANE",
    "REVOKED_CAPABILITIES_CANNOT_BE_RESTORED_WITHIN_THE_SAME_LANE",
    "DEACTIVATING_CLEAN_MODE_DOES_NOT_REENABLE_DISCOVERY_IN_THE_SAME_LANE",
    "UNKNOWN_CAPABILITY_FAILS_CLOSED",
    "NO_CAPABILITY_OR_FAMILY_CREDIT_FROM_FIREWALL_STATE",
}
REQUIRED_REVOKED={
    "WEB_DISCOVERY","REPO_SEARCH","BROAD_FILESYSTEM_SEARCH",
    "BENCHMARK_HISTORY_LOOKUP","TASK_SPECIFIC_EXTERNAL_SEARCH",
}
REQUIRED_ALLOWED={
    "EXACT_FROZEN_BLOB_READ","DECLARED_TOOL","TASK_RUNTIME_IO",
    "WRITE_CANDIDATE_ARTIFACT","TERMINAL_VERIFIER_EXECUTION",
}
REQUIRED_NONCLAIMS={
    "NO_GENERAL_PROMPT_INJECTION_CLOSURE",
    "NO_GENERAL_GOODHART_CLOSURE",
    "NO_HOLDOUT_LIFECYCLE_CLOSURE",
    "NO_GLOBAL_R11_SEMANTIC_LEAF_CLOSURE",
    "NO_GLOBAL_R11_ROOT_CLOSURE",
}

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(x:Any)->str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()

def certify(governance:Mapping[str,Any], binding:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(governance,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["GOVERNANCE_NOT_OBJECT"],"terminal_authority":False}
    if not isinstance(binding,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_NOT_OBJECT"],"terminal_authority":False}

    if governance.get("schema")!=GOV_SCHEMA:
        errors.append("GOVERNANCE_SCHEMA_INVALID")
    if governance.get("status")!="ACTIVE_FAIL_CLOSED__POST_IDENTITY_DISCOVERY_REVOCATION__ZERO_CREDIT":
        errors.append("GOVERNANCE_STATUS_INVALID")
    if binding.get("governance_sha256")!=digest(dict(governance)):
        errors.append("GOVERNANCE_DIGEST_MISMATCH")

    rules=set(governance.get("hard_rules") or [])
    revoked=set(governance.get("post_identity_revoked") or [])
    allowed=set(governance.get("post_identity_allowlist") or [])
    if not REQUIRED_RULES <= rules:
        errors.append("REQUIRED_FIREWALL_RULES_MISSING")
    if not REQUIRED_REVOKED <= revoked:
        errors.append("REQUIRED_REVOKED_CAPABILITIES_MISSING")
    if not REQUIRED_ALLOWED <= allowed:
        errors.append("REQUIRED_ALLOWED_CAPABILITIES_MISSING")
    if revoked & allowed:
        errors.append("ALLOW_REVOKE_SETS_OVERLAP")

    objective=str(governance.get("objective") or "")
    if "revoking broad discovery capabilities once task identity is exposed" not in objective:
        errors.append("OBJECTIVE_SEMANTICS_INVALID")

    semantics=binding.get("semantic_claim")
    if not isinstance(semantics,Mapping):
        errors.append("SEMANTIC_CLAIM_INVALID")
    else:
        if semantics.get("scope")!="SAME_CLEAN_EVALUATION_LANE_AFTER_TASK_IDENTITY_EXPOSURE":
            errors.append("SEMANTIC_SCOPE_INVALID")
        if semantics.get("discovery_capabilities_revoked") is not True:
            errors.append("REVOCATION_SEMANTICS_MISSING")
        if semantics.get("revocation_monotonic") is not True:
            errors.append("MONOTONICITY_SEMANTICS_MISSING")
        if semantics.get("unknown_capability_disposition")!="DENY_FAIL_CLOSED":
            errors.append("UNKNOWN_CAPABILITY_SEMANTICS_INVALID")
        if semantics.get("new_lane_semantics_claimed") is not False:
            errors.append("CROSS_LANE_OVERCLAIM")

    nonclaims=set(binding.get("hard_nonclaims") or [])
    if not REQUIRED_NONCLAIMS <= nonclaims:
        errors.append("REQUIRED_NONCLAIMS_MISSING")

    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__EXACT_CLEAN_LANE_FIREWALL_SEMANTICS_BOUND" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "governance_sha256":digest(dict(governance)),
        "claim_scope":{
            "kind":"CLEAN_EVALUATION_LANE_POST_IDENTITY_REVOCATION_SEMANTICS",
            "guarantees":[
                "TASK_IDENTITY_EXPOSURE_IS_MONOTONIC_WITHIN_A_LANE",
                "POST_EXPOSURE_BROAD_DISCOVERY_CAPABILITIES_ARE_REVOKED",
                "REVOKED_CAPABILITIES_CANNOT_BE_RESTORED_WITHIN_THE_SAME_LANE",
                "DEACTIVATING_CLEAN_MODE_DOES_NOT_REENABLE_DISCOVERY_IN_THE_SAME_LANE",
                "UNKNOWN_CAPABILITY_DENIES_FAIL_CLOSED",
                "ALLOW_AND_REVOKE_CAPABILITY_CLASSES_ARE_DISJOINT",
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
