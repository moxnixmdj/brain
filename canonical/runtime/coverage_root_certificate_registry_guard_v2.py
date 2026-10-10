"""Stable-mission-authority coverage-root registry guard V2.

V2 preserves every structural and certificate-slot rule from V1, but deletes
one invalid currentness coupling: a frozen claim no longer uses the mutable
CURRENT_MISSION_OBJECTIVE file blob as semantic claim identity.

Claim identity binds the immutable REAL_MISSION_OBJECTIVE authority blob.
The mutable current pointer remains a resolver/currentness assertion and must
still point to the exact authority with the same mission-defining objective.

This module grants no root, property, promotion, acceptance, or terminal credit.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import coverage_root_certificate_registry_guard_v1 as v1
from canonical.runtime import coverage_claim_scope_guard_v2 as claim_guard_v2

SCHEMA="PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V2"
V1_SCHEMA=v1.SCHEMA
NAMESPACE=v1.NAMESPACE
ROOTS=v1.ROOTS
CERTIFICATE_ROOT_IDS=v1.CERTIFICATE_ROOT_IDS
MISSION_AUTHORITY_PATH=claim_guard_v2.MISSION_AUTHORITY_PATH


def _fail(*errors:str, base:Mapping[str,Any]|None=None)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "open_root_ids":list((base or {}).get("open_root_ids") or []),
        "proved_root_ids":list((base or {}).get("proved_root_ids") or []),
        "r4_proof_closure":False,
        "stable_mission_authority_binding":False,
        "terminal_credit_delta":0,
    }


def _mission_coherence(
    *,
    registry:Mapping[str,Any],
    current_mission_pointer:Mapping[str,Any],
    current_mission_authority:Mapping[str,Any],
    current_mission_authority_blob_sha:str,
)->list[str]:
    errors:list[str]=[]
    mission=registry.get("mission_binding") or {}
    if mission.get("pointer_path")!="canonical/governance/CURRENT_MISSION_OBJECTIVE.json":
        errors.append("MISSION_POINTER_PATH_DRIFT")
    if mission.get("authority_path")!=MISSION_AUTHORITY_PATH:
        errors.append("MISSION_AUTHORITY_PATH_DRIFT")
    if mission.get("authority_git_blob_sha")!=current_mission_authority_blob_sha:
        errors.append("MISSION_AUTHORITY_BLOB_STALE")
    source=current_mission_pointer.get("authoritative_source") or {}
    if source.get("path")!=MISSION_AUTHORITY_PATH:
        errors.append("CURRENT_POINTER_AUTHORITY_PATH_DRIFT")
    if current_mission_pointer.get("real_objective")!=current_mission_authority.get("real_objective"):
        errors.append("CURRENT_POINTER_OBJECTIVE_DRIFT")
    if mission.get("real_objective")!=current_mission_authority.get("real_objective"):
        errors.append("REGISTRY_MISSION_OBJECTIVE_DRIFT")
    if current_mission_pointer.get("schema")!=claim_guard_v2.CURRENT_POINTER_SCHEMA:
        errors.append("CURRENT_POINTER_SCHEMA_INVALID")
    if current_mission_authority.get("schema")!=claim_guard_v2.MISSION_AUTHORITY_SCHEMA:
        errors.append("MISSION_AUTHORITY_SCHEMA_INVALID")
    if current_mission_pointer.get("status")!="ACTIVE":
        errors.append("CURRENT_POINTER_NOT_ACTIVE")
    if current_mission_authority.get("status")!="ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
        errors.append("MISSION_AUTHORITY_NOT_ACTIVE")
    return errors


def validate(
    registry:Mapping[str,Any],
    *,
    current_mission_pointer:Mapping[str,Any],
    current_mission_authority:Mapping[str,Any],
    current_mission_authority_blob_sha:str,
)->dict[str,Any]:
    if not isinstance(registry,Mapping):
        return _fail("REGISTRY_NOT_OBJECT")
    if registry.get("schema")!=SCHEMA:
        return _fail("SCHEMA_DRIFT")
    if registry.get("namespace")!=NAMESPACE:
        return _fail("NAMESPACE_DRIFT")

    errors=_mission_coherence(
        registry=registry,
        current_mission_pointer=current_mission_pointer,
        current_mission_authority=current_mission_authority,
        current_mission_authority_blob_sha=current_mission_authority_blob_sha,
    )

    active=registry.get("active_claim")
    if active is not None:
        verdict=claim_guard_v2.validate_claim(
            active,
            current_pointer=current_mission_pointer,
            mission_authority=current_mission_authority,
            mission_authority_blob_sha=current_mission_authority_blob_sha,
        )
        if verdict.get("pass") is not True:
            errors.extend("ACTIVE_CLAIM_"+str(x) for x in verdict.get("errors") or ["INVALID"])

    # Reuse the already-tested V1 structural/slot validator. The only semantic
    # substitution is deliberate: V1's parameter named current_mission_pointer_blob_sha
    # receives the immutable mission authority blob, because V2 claim identity is
    # explicitly authority-bound. All root ids, exact claim bindings, content
    # addresses, counts, alias rules and zero-credit rules remain unchanged.
    shadow=deepcopy(dict(registry))
    shadow["schema"]=V1_SCHEMA
    base=v1.validate(
        shadow,
        current_mission_pointer=current_mission_pointer,
        current_mission_authority_blob_sha=current_mission_authority_blob_sha,
        current_mission_pointer_blob_sha=current_mission_authority_blob_sha,
    )
    if base.get("pass") is not True:
        errors.extend(str(x) for x in base.get("errors") or ["V1_STRUCTURAL_VALIDATION_FAILED"])

    if errors:
        return _fail(*errors,base=base)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__ROOT_CERTIFICATE_REGISTRY__STABLE_MISSION_AUTHORITY",
        "errors":[],
        "open_root_ids":list(base.get("open_root_ids") or []),
        "proved_root_ids":list(base.get("proved_root_ids") or []),
        "r4_proof_closure":base.get("r4_proof_closure") is True,
        "stable_mission_authority_binding":True,
        "mission_authority_path":MISSION_AUTHORITY_PATH,
        "mission_authority_git_blob_sha":current_mission_authority_blob_sha,
        "mutable_pointer_projection_is_claim_identity":False,
        "terminal_credit_delta":0,
    }
