"""Fail-closed contract-surface guard for P3 real-context admission.

This guard owns only a syntactic authority boundary. It prevents a positive P3
route from silently projecting away caller-supplied semantic requirements.

It does not prove that the declared surface is semantically complete.
"""
from __future__ import annotations

from typing import Any, Mapping
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

SCHEMA="PROJECT_BRAIN_P3_V3_CONTRACT_SURFACE_GUARD_V1"

_ALLOWED_PUBLIC_FIELDS={"schema","task"}
_ALLOWED_TASK_FIELDS={
    "claims","evidence","audience_profile","required_uncertainty_units",
    "claim_order","title",
}
_ALLOWED_CLAIM_FIELDS={"claim_id","text","required","include"}
_ALLOWED_PROFILE_FIELDS={"profile_id","constraints","title"}

def validate_v3_contract_surface(public:Mapping[str,Any])->str|None:
    if not isinstance(public,Mapping):
        return "V3_INPUT_REQUIRED"
    if public.get("schema")!=INPUT_SCHEMA:
        return "V3_INPUT_SCHEMA_INVALID"
    if set(public)-_ALLOWED_PUBLIC_FIELDS:
        return "UNMODELED_V3_INPUT_FIELDS"
    task=public.get("task")
    if not isinstance(task,Mapping):
        return "TASK_REQUIRED"
    if set(task)-_ALLOWED_TASK_FIELDS:
        return "UNMODELED_TASK_REQUIREMENTS"

    profile=task.get("audience_profile")
    if isinstance(profile,Mapping):
        if set(profile)-_ALLOWED_PROFILE_FIELDS:
            return "UNMODELED_AUDIENCE_PROFILE_FIELDS"
        if profile.get("profile_id")!="EXPLICIT":
            return "AUDIENCE_PROFILE_SEMANTICS_UNMODELED"

    claims=task.get("claims")
    if isinstance(claims,list):
        for row in claims:
            if isinstance(row,Mapping) and set(row)-_ALLOWED_CLAIM_FIELDS:
                return "UNMODELED_CLAIM_REQUIREMENTS"
    return None

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    reason=validate_v3_contract_surface(payload)
    return {
        "schema":SCHEMA,
        "pass":reason is None,
        "status":"PASS__EXACT_DECLARED_P3_CONTRACT_SURFACE" if reason is None else "FAIL_CLOSED",
        "reason":reason,
        "semantic_completeness_authority":False,
        "policy_adequacy_authority":False,
        "terminal_authority":False,
    }
