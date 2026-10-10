"""Stable-authority freezer for the twelve professional semantic claims.

V2 bound claim identity to CURRENT_MISSION_OBJECTIVE.json bytes. That pointer
contains mutable currentness projections, so unrelated bookkeeping changes can
invalidate every semantic claim without changing the real mission.

V3 keeps V2's exact scope, witness and claim construction semantics but binds
claim identity to the immutable REAL_MISSION_OBJECTIVE authority. The mutable
pointer is checked only as a resolver to that authority and for the two mission
fields it mirrors directly.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import coverage_claim_scope_guard_v1 as claim_guard_v1
from canonical.runtime import coverage_claim_scope_guard_v2 as claim_guard_v2
from canonical.runtime import professional_semantic_totality_claim_pack_v2 as v2

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_V3"
EPOCH="PROFESSIONAL_SEMANTIC_TOTALITY_BATCH_20261010_V3"
AUTHORITY_ID="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_COVERAGE_AUTHORITY_V3"
MISSION_AUTHORITY_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_POINTER_PATH="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
EXPECTED_MISSION_AUTHORITY_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
MISSION_REPAIR_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_MISSION_BINDING_REPAIR_20261010_V1.json"


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "semantic_claim_count":0,"unique_claim_id_count":0,
        "root_proved_claim_count":0,"property_truth_claim_count":0,
        "single_active_claim_policy_preserved":True,
        "cross_claim_root_transport_authorized":False,
        "semantic_truth_authority":False,"quality_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "incremental_spend_usd":0,**extra,
    }


def resolve_mission_authority(
    pointer:Mapping[str,Any],
    authority:Mapping[str,Any],
    *,
    authority_blob_sha:str,
)->dict[str,Any]:
    if authority_blob_sha!=EXPECTED_MISSION_AUTHORITY_BLOB:
        return _fail("MISSION_AUTHORITY_BLOB_DRIFT",observed=authority_blob_sha)
    source=pointer.get("authoritative_source")
    if not isinstance(source,Mapping) or source.get("path")!=MISSION_AUTHORITY_PATH:
        return _fail("MISSION_POINTER_AUTHORITY_PATH_DRIFT")
    if pointer.get("real_objective")!=authority.get("real_objective"):
        return _fail("MISSION_POINTER_OBJECTIVE_DRIFT")
    if pointer.get("opus_5_5_role")!=authority.get("opus_5_5_role"):
        return _fail("MISSION_POINTER_OPUS_ROLE_DRIFT")
    if authority.get("status")!="ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
        return _fail("MISSION_AUTHORITY_NOT_ACTIVE")
    return {
        "pass":True,
        "status":"PASS__CURRENT_POINTER_RESOLVES_STABLE_MISSION_AUTHORITY",
        "mission_authority_path":MISSION_AUTHORITY_PATH,
        "mission_authority_git_blob_sha":authority_blob_sha,
        "real_objective":authority.get("real_objective"),
        "opus_5_5_role":authority.get("opus_5_5_role"),
    }


def rebind_source_pack(
    source:Mapping[str,Any],
    *,
    mission_authority_blob_sha:str,
    current_pointer:Mapping[str,Any],
    mission_authority:Mapping[str,Any],
)->dict[str,Any]:
    if source.get("pass") is not True or source.get("semantic_claim_count")!=12:
        return _fail("V2_SOURCE_PACK_NOT_VALID_CURRENT_SHAPE")
    claims=source.get("claims")
    if not isinstance(claims,list) or len(claims)!=12:
        return _fail("V2_SOURCE_CLAIM_SET_INVALID")

    rows=[]
    for row0 in claims:
        if not isinstance(row0,Mapping):
            return _fail("V2_SOURCE_CLAIM_ROW_INVALID")
        row=deepcopy(dict(row0))
        target=row.get("target_predicate")
        semantics=row.get("semantics")
        scope=row.get("scope_definition_sha256")
        if not isinstance(target,Mapping) or not isinstance(semantics,Mapping):
            return _fail("V2_SOURCE_CLAIM_SEMANTICS_INVALID",leaf_id=row.get("leaf_id"))
        if not isinstance(scope,str) or len(scope)!=64:
            return _fail("V2_SOURCE_CLAIM_SCOPE_INVALID",leaf_id=row.get("leaf_id"))
        claim={
            "claim_kind":"PROPERTY_CERTIFICATE",
            "mission_blob_sha":mission_authority_blob_sha,
            "scope_sha256":scope,
            "target_predicate_sha256":v2._digest(target),
            "semantics_sha256":v2._digest(semantics),
            "epoch":EPOCH,
            "authority_id":AUTHORITY_ID,
        }
        claim["claim_id"]=claim_guard_v1.compute_claim_id(claim)
        claim["terminal_credit_delta"]=0
        verdict=claim_guard_v2.validate_claim(
            claim,
            current_pointer=current_pointer,
            mission_authority=mission_authority,
            mission_authority_blob_sha=mission_authority_blob_sha,
        )
        if verdict.get("pass") is not True:
            return _fail("V3_CLAIM_GUARD_REJECTED",leaf_id=row.get("leaf_id"),verdict=verdict)
        row["frozen_claim"]=claim
        row["claim_guard_pass"]=True
        row["mission_sufficient_carrier_factorization_proved"]=False
        row["cc_r1_reality_containment_proved"]=False
        row["cc_r2_mission_soundness_proved"]=False
        row["cc_r3_terminal_closure_proved"]=False
        row["r4_proof_closure"]=False
        row["semantic_property_truth_authority"]=False
        row["activation_authorized"]=False
        rows.append(row)

    ids=[x["frozen_claim"]["claim_id"] for x in rows]
    if len(ids)!=12 or len(set(ids))!=12:
        return _fail("V3_CLAIM_IDENTITIES_NOT_UNIQUE")
    r12=next(
        (x for x in rows if x.get("leaf_id")=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),
        None,
    )
    if not isinstance(r12,dict):
        return _fail("R12_CURRENT_CLAIM_MISSING")
    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__TWELVE_STABLE_MISSION_AUTHORITY_BOUND_SEMANTIC_CLAIMS_FROZEN__CLAIM_SPECIFIC_ROOT_PROOFS_OPEN__ZERO_PROPERTY_TRUTH_CREDIT",
        "epoch":EPOCH,"authority_id":AUTHORITY_ID,
        "mission_blob_sha":mission_authority_blob_sha,
        "mission_binding_mode":"IMMUTABLE_REAL_MISSION_AUTHORITY_WITH_CURRENT_POINTER_RESOLUTION_CHECK",
        "semantic_claim_count":12,"unique_claim_id_count":12,
        "claim_id_set_sha256":v2._digest(sorted(ids)),
        "root_proved_claim_count":0,"property_truth_claim_count":0,
        "single_active_claim_policy_preserved":True,
        "cross_claim_root_transport_authorized":False,
        "activation_policy":"ACTIVATE_AT_MOST_ONE_FROZEN_CLAIM_AT_A_TIME__CLAIM_SPECIFIC_CC_R1_CC_R2_CC_R3_AND_R4_REQUIRED",
        "r12_claim_id":r12["frozen_claim"]["claim_id"],
        "claims":rows,
        "semantic_truth_authority":False,"quality_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root else ROOT
    for rel in (MISSION_AUTHORITY_PATH,MISSION_POINTER_PATH,MISSION_REPAIR_PATH):
        p=root/rel
        if not p.is_file() or p.is_symlink():
            return _fail("BOUND_FILE_MISSING:"+rel)
    if v2._blob(root/MISSION_AUTHORITY_PATH)!=EXPECTED_MISSION_AUTHORITY_BLOB:
        return _fail("MISSION_AUTHORITY_BLOB_STALE")
    try:
        pointer=v2._load(root/MISSION_POINTER_PATH)
        authority=v2._load(root/MISSION_AUTHORITY_PATH)
    except Exception as exc:
        return _fail("MISSION_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
    resolved=resolve_mission_authority(
        pointer,authority,authority_blob_sha=EXPECTED_MISSION_AUTHORITY_BLOB
    )
    if resolved.get("pass") is not True:
        return resolved

    source=v2.verify(repo_root=root)
    if source.get("pass") is not True:
        return _fail("V2_SOURCE_VALIDATION_FAILED",source_status=source.get("status"),source_reason=source.get("reason"))
    out=rebind_source_pack(
        source,
        mission_authority_blob_sha=EXPECTED_MISSION_AUTHORITY_BLOB,
        current_pointer=pointer,
        mission_authority=authority,
    )
    if out.get("pass") is not True:
        return out
    out["mission_resolution"]=resolved
    out["source_v2_dynamic_pack_status"]=source.get("status")
    return out


if __name__=="__main__":
    import json
    print(json.dumps(verify(),indent=2,sort_keys=True))
