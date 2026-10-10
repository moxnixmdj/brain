"""Coverage-root certificate registry guard V2.

V2 preserves the V1 registry law while making claim mission binding explicit:
- CURRENT_POINTER_BLOB preserves V1 behavior.
- MISSION_AUTHORITY_BLOB permits a frozen claim to bind the canonical mission
  authority bytes instead of incidental mutable pointer bytes.

No mode is inferred from the claim. Legacy registries default to
CURRENT_POINTER_BLOB. Root IDs, exact claim equality, certificate content
addresses, and zero-credit rules remain unchanged.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.coverage_claim_scope_guard_v1 import ALLOWED_KINDS, CORE_FIELDS, compute_claim_id
from canonical.runtime.coverage_root_certificate_registry_guard_v1 import (
    SCHEMA,NAMESPACE,ROOTS,CERTIFICATE_ROOT_IDS,ALLOWED_SLOT_STATUSES,CLAIM_BINDING_FIELDS,
)

BINDING_MODES=frozenset({"CURRENT_POINTER_BLOB","MISSION_AUTHORITY_BLOB"})

def validate(
    registry: Mapping[str,Any], *,
    current_mission_pointer: Mapping[str,Any],
    current_mission_authority_blob_sha: str,
    current_mission_pointer_blob_sha: str|None=None,
)->dict[str,Any]:
    errors=[]
    if not isinstance(registry,Mapping):
        return {"pass":False,"status":"FAIL_CLOSED","errors":["REGISTRY_NOT_OBJECT"],"terminal_credit_delta":0}
    if registry.get("schema")!=SCHEMA: errors.append("SCHEMA_DRIFT")
    if registry.get("namespace")!=NAMESPACE: errors.append("NAMESPACE_DRIFT")

    mission=registry.get("mission_binding") or {}
    if mission.get("pointer_path")!="canonical/governance/CURRENT_MISSION_OBJECTIVE.json":
        errors.append("MISSION_POINTER_PATH_DRIFT")
    authority=current_mission_pointer.get("authoritative_source") or {}
    if mission.get("authority_path")!=authority.get("path"): errors.append("MISSION_AUTHORITY_PATH_DRIFT")
    if mission.get("authority_git_blob_sha")!=current_mission_authority_blob_sha:
        errors.append("MISSION_AUTHORITY_BLOB_STALE")
    if mission.get("real_objective")!=current_mission_pointer.get("real_objective"):
        errors.append("MISSION_OBJECTIVE_DRIFT")

    identities=registry.get("root_identities")
    if not isinstance(identities,list) or len(identities)!=4:
        errors.append("ROOT_IDENTITIES_SHAPE_INVALID"); identities=[]
    else:
        seen=set()
        for i,(cid,alias,claim) in enumerate(ROOTS):
            row=identities[i]
            if not isinstance(row,Mapping): errors.append(f"ROOT_IDENTITY_NOT_OBJECT:{i}"); continue
            if row.get("canonical_id")!=cid: errors.append(f"CANONICAL_ROOT_ID_DRIFT:{i}")
            if row.get("display_alias")!=alias: errors.append(f"DISPLAY_ALIAS_DRIFT:{i}")
            if row.get("claim")!=claim: errors.append(f"ROOT_CLAIM_DRIFT:{i}")
            if row.get("canonical_id") in seen: errors.append(f"DUPLICATE_CANONICAL_ROOT_ID:{i}")
            seen.add(row.get("canonical_id"))

    policy=registry.get("claim_binding_policy") or {}
    mode=policy.get("mission_binding_mode","CURRENT_POINTER_BLOB")
    if mode not in BINDING_MODES: errors.append("MISSION_BINDING_MODE_INVALID")

    active=registry.get("active_claim")
    if active is not None:
        if not isinstance(active,Mapping):
            errors.append("ACTIVE_CLAIM_NOT_OBJECT")
        else:
            for field in CORE_FIELDS:
                v=active.get(field)
                if not isinstance(v,str) or not v: errors.append("ACTIVE_CLAIM_INVALID_FIELD:"+field)
            if active.get("claim_kind") not in ALLOWED_KINDS: errors.append("ACTIVE_CLAIM_KIND_NOT_ALLOWED")
            if mode=="CURRENT_POINTER_BLOB":
                if current_mission_pointer_blob_sha is None:
                    errors.append("CURRENT_MISSION_POINTER_BLOB_REQUIRED_FOR_ACTIVE_CLAIM")
                elif active.get("mission_blob_sha")!=current_mission_pointer_blob_sha:
                    errors.append("ACTIVE_CLAIM_MISSION_BINDING_STALE")
            elif mode=="MISSION_AUTHORITY_BLOB":
                if active.get("mission_blob_sha")!=current_mission_authority_blob_sha:
                    errors.append("ACTIVE_CLAIM_MISSION_AUTHORITY_BINDING_STALE")
            for field in ("scope_sha256","target_predicate_sha256","semantics_sha256"):
                v=active.get(field)
                if isinstance(v,str) and (len(v)!=64 or any(c not in "0123456789abcdef" for c in v)):
                    errors.append("ACTIVE_CLAIM_INVALID_SHA256:"+field)
            if active.get("claim_id")!=compute_claim_id(active): errors.append("ACTIVE_CLAIM_ID_MISMATCH")
            if active.get("terminal_credit_delta",0)!=0: errors.append("ACTIVE_CLAIM_NONZERO_CREDIT_FORBIDDEN")

    alias=registry.get("alias_policy") or {}
    if alias.get("short_aliases_are_display_only") is not True: errors.append("SHORT_ALIAS_AUTHORITY_ENABLED")
    if alias.get("short_aliases_have_zero_cross_artifact_authority") is not True: errors.append("SHORT_ALIAS_CROSS_ARTIFACT_AUTHORITY_ENABLED")
    if alias.get("cross_artifact_binding_requires_namespace_and_canonical_id") is not True: errors.append("CANONICAL_ID_BINDING_NOT_REQUIRED")

    slots=registry.get("certificate_slots")
    if not isinstance(slots,list) or len(slots)!=3:
        errors.append("CERTIFICATE_SLOT_SHAPE_INVALID"); slots=[]
    open_ids=[]; proved_ids=[]; seen_slots=set()
    for i,slot in enumerate(slots):
        if not isinstance(slot,Mapping): errors.append(f"CERTIFICATE_SLOT_NOT_OBJECT:{i}"); continue
        rid=slot.get("root_id")
        if rid not in CERTIFICATE_ROOT_IDS: errors.append(f"INVALID_CERTIFICATE_ROOT_ID:{rid}"); continue
        if rid in seen_slots: errors.append(f"DUPLICATE_CERTIFICATE_SLOT:{rid}")
        seen_slots.add(rid)
        status=slot.get("status")
        if status not in ALLOWED_SLOT_STATUSES: errors.append(f"INVALID_CERTIFICATE_STATUS:{rid}"); continue
        if status=="OPEN_NO_GLOBAL_CERTIFICATE_BOUND":
            open_ids.append(rid)
            if any(slot.get(f) is not None for f in ("certificate","semantic_verifier","independent_verification")):
                errors.append(f"OPEN_SLOT_HAS_AUTHORITY_PAYLOAD:{rid}")
            continue
        proved_ids.append(rid)
        cert=slot.get("certificate"); verifier=slot.get("semantic_verifier"); verify=slot.get("independent_verification")
        if active is None: errors.append(f"PROVED_SLOT_WITHOUT_ACTIVE_CLAIM:{rid}")
        if not isinstance(cert,Mapping): errors.append(f"PROVED_SLOT_CERTIFICATE_MISSING:{rid}")
        else:
            if cert.get("root_id")!=rid: errors.append(f"PROVED_SLOT_ROOT_ID_MISMATCH:{rid}")
            if cert.get("mission_authority_blob_sha")!=current_mission_authority_blob_sha:
                errors.append(f"PROVED_SLOT_MISSION_AUTHORITY_DRIFT:{rid}")
            if not isinstance(cert.get("path"),str) or not isinstance(cert.get("git_blob_sha"),str):
                errors.append(f"PROVED_SLOT_CONTENT_ADDRESS_MISSING:{rid}")
            binding=cert.get("claim_binding")
            if isinstance(active,Mapping):
                if not isinstance(binding,Mapping): errors.append(f"PROVED_SLOT_CLAIM_BINDING_MISSING:{rid}")
                else:
                    for field in CLAIM_BINDING_FIELDS:
                        if binding.get(field)!=active.get(field):
                            errors.append(f"PROVED_SLOT_CLAIM_BINDING_MISMATCH:{rid}:{field}")
        if not isinstance(verifier,Mapping) or not isinstance(verifier.get("path"),str) or not isinstance(verifier.get("git_blob_sha"),str):
            errors.append(f"PROVED_SLOT_SEMANTIC_VERIFIER_MISSING:{rid}")
        if not isinstance(verify,Mapping) or not isinstance(verify.get("path"),str) or not isinstance(verify.get("git_blob_sha"),str):
            errors.append(f"PROVED_SLOT_INDEPENDENT_VERIFICATION_MISSING:{rid}")
        elif isinstance(active,Mapping) and verify.get("claim_id")!=active.get("claim_id"):
            errors.append(f"PROVED_SLOT_VERIFICATION_CLAIM_MISMATCH:{rid}")

    if set(seen_slots)!=set(CERTIFICATE_ROOT_IDS): errors.append("CERTIFICATE_SLOT_COVERAGE_INCOMPLETE")
    if registry.get("currently_proved_root_certificates")!=len(proved_ids): errors.append("PROVED_COUNT_DRIFT")
    if registry.get("currently_open_root_certificates")!=len(open_ids): errors.append("OPEN_COUNT_DRIFT")
    proof_closed=len(proved_ids)==3 and not errors
    if registry.get("r4_proof_closure") is not proof_closed: errors.append("R4_PROOF_CLOSURE_FLAG_DRIFT")
    if (registry.get("accounting") or {}).get("terminal_credit_delta")!=0: errors.append("UNAUTHORIZED_TERMINAL_CREDIT")
    return {
        "pass":not errors,"status":"PASS__ROOT_CERTIFICATE_REGISTRY_V2" if not errors else "FAIL_CLOSED",
        "errors":errors,"mission_binding_mode":mode,"open_root_ids":open_ids,"proved_root_ids":proved_ids,
        "r4_proof_closure":proof_closed,"terminal_credit_delta":0,
    }
