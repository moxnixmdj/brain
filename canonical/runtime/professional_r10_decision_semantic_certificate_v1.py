"""Bounded R10 decision-sufficiency semantic certificate.

Certifies the meaning of one explicit professional decision-sufficiency policy:
lossless baseline, omission-by-certificate only, minimum policy-changing
information, immutable verification authority, and fail-closed false progress.
It does not close general risk, normative aggregation, model multiplicity, or
professional decision semantics.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R10_DECISION_SEMANTIC_CERTIFICATE_V1"
SOURCE_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_V1"
HISTORY_SCHEMA="PROJECT_BRAIN_ONE_SHOT_DECISION_SUFFICIENT_GATE_VERIFY_20261009_V2"

REQUIRED_GUARANTEES={
    "DECISION_SUFFICIENT_BASELINE_IS_LOSSLESS_IDENTITY_AND_CONTENT_ADDRESSED",
    "NO_EVIDENCE_IS_OMITTED_WITHOUT_A_FUTURE_OMISSION_CERTIFICATE",
    "MINIMUM_INFORMATION_REQUESTS_DEDUPLICATE_EVIDENCE_BLOCKERS",
    "BROAD_ACQUISITION_IS_FORBIDDEN_WITHOUT_MINIMALITY_PROOF",
    "FULL_EMPIRICAL_EVALUATION_REMAINS_LAST",
    "PROVIDERS_CANNOT_MUTATE_VERIFICATION_AUTHORITY",
    "FALSE_PROGRESS_WITH_UNCHANGED_FRONTIER_FAILS_CLOSED",
    "STRUCTURED_R2_ACQUISITION_SURVIVES_MINIMUM_INFORMATION_COMPILATION",
}
REQUIRED_LIMITATIONS={
    "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
    "NO_NORMATIVE_AGGREGATION_CLOSURE",
    "NO_MODEL_MULTIPLICITY_DECISION_CLOSURE",
    "NO_GENERAL_SEMANTIC_COMPRESSION_CLAIM",
    "NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE",
}
HISTORY_REQUIRED={
    "BUILTIN_DECISION_REDUCTION_IS_LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
    "FUTURE_COMPRESSION_REQUIRES_OMISSION_CERTIFICATE",
    "EVIDENCE_ACQUISITION_RECEIVES_DEDUPLICATED_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT",
    "FULL_EMPIRICAL_EVALUATION_REMAINS_LAST",
    "SYNTHESIS_AND_ACQUISITION_CANNOT_MUTATE_VERIFICATION_AUTHORITY",
}

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(x:Any)->str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()

def certify(source:Mapping[str,Any], history:Mapping[str,Any], binding:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(source,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["SOURCE_NOT_OBJECT"],"terminal_authority":False}
    if not isinstance(history,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["HISTORY_NOT_OBJECT"],"terminal_authority":False}
    if not isinstance(binding,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_NOT_OBJECT"],"terminal_authority":False}

    if source.get("schema")!=SOURCE_SCHEMA:
        errors.append("SOURCE_SCHEMA_INVALID")
    if source.get("status")!="PASS__PINNED_CURRENT_BYTES__PYCOMPILE__23_OF_23__BOUNDED_DECISION_SUFFICIENCY_AND_MINIMUM_INFORMATION_ROUTING__ZERO_GLOBAL_LEAF_CREDIT":
        errors.append("SOURCE_STATUS_INVALID")
    scope=source.get("claim_scope")
    if not isinstance(scope,Mapping):
        errors.append("SOURCE_SCOPE_INVALID")
        scope={}
    if not REQUIRED_GUARANTEES <= set(scope.get("guarantees") or []):
        errors.append("SOURCE_REQUIRED_GUARANTEES_MISSING")
    if not REQUIRED_LIMITATIONS <= set(scope.get("limitations") or []):
        errors.append("SOURCE_REQUIRED_LIMITATIONS_MISSING")

    current=source.get("current_state")
    if not isinstance(current,Mapping):
        errors.append("SOURCE_CURRENT_STATE_INVALID")
    else:
        for field in ("global_leaf_credit","global_r10_root_closed","domain_semantic_closure","domain_execution_closure"):
            if current.get(field) is not False:
                errors.append("SOURCE_GLOBAL_OVERCLAIM:"+field)

    if history.get("schema")!=HISTORY_SCHEMA:
        errors.append("HISTORY_SCHEMA_INVALID")
    if history.get("status")!="PASS__FOCUSED_18_OF_18__CURRENT_V1_ADJACENT_7_OF_7__PY_COMPILE_PASS":
        errors.append("HISTORY_STATUS_INVALID")
    if not HISTORY_REQUIRED <= set(history.get("guarantees") or []):
        errors.append("HISTORY_REQUIRED_GUARANTEES_MISSING")
    if "NO_OPEN_WORLD_TERMINAL_CLOSURE_CLAIM" not in set(history.get("nonclaims") or []):
        errors.append("HISTORY_OPEN_WORLD_NONCLAIM_MISSING")

    if binding.get("source_sha256")!=digest(dict(source)):
        errors.append("SOURCE_DIGEST_MISMATCH")
    if binding.get("history_sha256")!=digest(dict(history)):
        errors.append("HISTORY_DIGEST_MISMATCH")

    semantic=binding.get("semantic_claim")
    if not isinstance(semantic,Mapping):
        errors.append("SEMANTIC_CLAIM_INVALID")
    else:
        expected={
            "baseline_representation":"LOSSLESS_IDENTITY_CONTENT_ADDRESSED",
            "omission_rule":"INDEPENDENT_OMISSION_CERTIFICATE_REQUIRED",
            "information_rule":"MINIMUM_POLICY_CHANGING_INFORMATION_FIRST",
            "broad_acquisition_rule":"FORBIDDEN_WITHOUT_MINIMALITY_PROOF",
            "empirical_evaluation_position":"LAST",
            "provider_verification_authority_mutation":False,
            "unchanged_frontier_progress":"FAIL_CLOSED",
        }
        for field,value in expected.items():
            if semantic.get(field)!=value:
                errors.append("SEMANTIC_POLICY_INVALID:"+field)

    nonclaims=set(binding.get("hard_nonclaims") or [])
    if not REQUIRED_LIMITATIONS <= nonclaims:
        errors.append("REQUIRED_NONCLAIMS_MISSING")

    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__EXACT_DECISION_SUFFICIENCY_SEMANTICS_BOUND" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "source_sha256":digest(dict(source)),
        "history_sha256":digest(dict(history)),
        "claim_scope":{
            "kind":"LOSSLESS_MINIMUM_INFORMATION_DECISION_SUFFICIENCY_SEMANTICS",
            "guarantees":sorted(REQUIRED_GUARANTEES),
            "limitations":sorted(REQUIRED_LIMITATIONS),
        },
        "semantic_leaf_credit":False,
        "global_leaf_closure":False,
        "global_root_closure":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
