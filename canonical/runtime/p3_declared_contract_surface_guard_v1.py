"""Fail-closed syntactic requirement preservation for P3 positive admissions.

Checks only that no visible requirement-bearing fields are silently projected away.
It does not certify that all implicit real-world requirements have been extracted.
No source authenticity, Opus comparison, U-empty or terminal credit.
"""
from __future__ import annotations

from typing import Any, Mapping
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

_ALLOWED_PUBLIC={"schema","task"}
_ALLOWED_TASK={"claims","evidence","audience_profile","required_uncertainty_units","claim_order","title"}
_ALLOWED_CLAIM={"claim_id","text","required","include"}
_ALLOWED_EVIDENCE={"evidence_id","text","verified","provenance"}
_ALLOWED_PROFILE={"profile_id","constraints","title"}
_ALLOWED_RENDER_CONSTRAINTS={
    "output_format","citation_mode","style","required_sections",
    "allowed_sections","max_items","max_chars","heading_level","require_title",
}
_ALLOWED_OUTER={"context_id","v3_input","objective_weights","semantic_certificates"}
_ALLOWED_DEPENDENCY_CONTRACT={
    "environment_id","goal_id","goal_nodes","dependencies","dependency_verification_ref"
}
_ALLOWED_DEPENDENCY_REF={"path","git_blob_sha"}


def validate_v3_input(public: Any) -> str | None:
    if not isinstance(public,Mapping):
        return "V3_INPUT_REQUIRED"
    if public.get("schema")!=INPUT_SCHEMA:
        return "V3_INPUT_SCHEMA_INVALID"
    if set(public)-_ALLOWED_PUBLIC:
        return "UNMODELED_V3_INPUT_FIELDS"
    task=public.get("task")
    if not isinstance(task,Mapping):
        return "TASK_REQUIRED"
    if set(task)-_ALLOWED_TASK:
        return "UNMODELED_TASK_REQUIREMENTS"
    profile=task.get("audience_profile")
    if isinstance(profile,Mapping):
        if set(profile)-_ALLOWED_PROFILE:
            return "UNMODELED_AUDIENCE_PROFILE_FIELDS"
        if profile.get("profile_id")!="EXPLICIT":
            return "AUDIENCE_PROFILE_SEMANTICS_UNMODELED"
        constraints=profile.get("constraints")
        if isinstance(constraints,Mapping):
            if set(constraints)-_ALLOWED_RENDER_CONSTRAINTS:
                return "UNMODELED_RENDER_REQUIREMENTS"
        if (isinstance(task.get("title"),str)
                and isinstance(profile.get("title"),str)
                and task["title"] != profile["title"]):
            return "CONFLICTING_TITLE_REQUIREMENTS"
    claims=task.get("claims")
    if isinstance(claims,list):
        for row in claims:
            if isinstance(row,Mapping) and set(row)-_ALLOWED_CLAIM:
                return "UNMODELED_CLAIM_REQUIREMENTS"
    evidence=task.get("evidence")
    if isinstance(evidence,list):
        for row in evidence:
            if isinstance(row,Mapping):
                if set(row)-_ALLOWED_EVIDENCE:
                    return "UNMODELED_EVIDENCE_REQUIREMENTS"
                prov=row.get("provenance")
                if isinstance(prov,list):
                    for unit in prov:
                        if isinstance(unit,Mapping) and set(unit)-{"source_id","locator"}:
                            return "UNMODELED_PROVENANCE_REQUIREMENTS"
    return None


def validate_decision_dependency_contract(contract: Any) -> str | None:
    if not isinstance(contract,Mapping):
        return "DECISION_DEPENDENCY_CONTRACT_INVALID"
    if set(contract)-_ALLOWED_DEPENDENCY_CONTRACT:
        return "UNMODELED_DECISION_DEPENDENCY_REQUIREMENTS"
    ref=contract.get("dependency_verification_ref")
    if isinstance(ref,Mapping) and set(ref)-_ALLOWED_DEPENDENCY_REF:
        return "UNMODELED_DEPENDENCY_VERIFICATION_REQUIREMENTS"
    return None


def validate_outer(payload: Any, *, allow_decision_dependency_contract: bool=False) -> str | None:
    if not isinstance(payload,Mapping):
        return "PAYLOAD_MAPPING_REQUIRED"
    allowed=set(_ALLOWED_OUTER)
    if allow_decision_dependency_contract:
        allowed.add("decision_dependency_contract")
    if set(payload)-allowed:
        return "UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"
    context_id=payload.get("context_id")
    if not isinstance(context_id,str) or not context_id.strip():
        return "CONTEXT_ID_REQUIRED"
    v3_failure=validate_v3_input(payload.get("v3_input"))
    if v3_failure is not None:
        return v3_failure
    if "decision_dependency_contract" in payload:
        if not allow_decision_dependency_contract:
            return "UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"
        return validate_decision_dependency_contract(payload.get("decision_dependency_contract"))
    return None
