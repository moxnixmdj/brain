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
        # Named profiles may encode requirements the bounded renderer cannot infer.
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
            if isinstance(row,Mapping) and set(row)-_ALLOWED_EVIDENCE:
                return "UNMODELED_EVIDENCE_REQUIREMENTS"
    return None


def validate_outer(payload: Any) -> str | None:
    if not isinstance(payload,Mapping):
        return "PAYLOAD_MAPPING_REQUIRED"
    if set(payload)-_ALLOWED_OUTER:
        return "UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"
    context_id=payload.get("context_id")
    if not isinstance(context_id,str) or not context_id.strip():
        return "CONTEXT_ID_REQUIRED"
    return validate_v3_input(payload.get("v3_input"))
