"""Stable-authority freezer for the twelve professional semantic claims.

V3 reuses only the verified *semantics material* frozen in the V2 pack. It does
not transport V2 claim IDs, root certificates, property truth, or authority.

Claim identity binds the immutable REAL_MISSION_OBJECTIVE authority blob. The
mutable CURRENT_MISSION_OBJECTIVE pointer is only required to resolve to that
authority and mirror the mission-defining objective/checkpoint role.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import coverage_claim_scope_guard_v2 as claim_guard_v2

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_V3"
EPOCH="PROFESSIONAL_SEMANTIC_TOTALITY_BATCH_20261010_V3"
AUTHORITY_ID="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_COVERAGE_AUTHORITY_V3"

MISSION_AUTHORITY_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_AUTHORITY_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
EXPECTED_MISSION_AUTHORITY_BLOB=MISSION_AUTHORITY_BLOB
CURRENT_MISSION_PATH="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
MISSION_POINTER_PATH=CURRENT_MISSION_PATH
MISSION_REPAIR_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_MISSION_BINDING_REPAIR_20261010_V1.json"

SOURCE_PACK_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_TOTALITY_FROZEN_CLAIM_PACK_20261010_V2.json"
SOURCE_PACK_BLOB="f16aab3760d4f5958da986782632f3cb2bbd2646"
SOURCE_VERIFY_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_VERIFY_20261010_V2.json"
SOURCE_VERIFY_BLOB="3d1f32e6e0e24d49c394daa365a7e3797c7d9984"
GUARD_V2_PATH="canonical/runtime/coverage_claim_scope_guard_v2.py"
GUARD_V2_BLOB="f28a25ad29cec75fd76f50754ce9a36618583c8d"
GUARD_V2_VERIFY_PATH="canonical/verification/COVERAGE_CLAIM_SCOPE_GUARD_V2_INDEPENDENT_VERIFY_20261010_V1.json"
GUARD_V2_VERIFY_BLOB="f54e555de1dd7fbbba5e83e2d58c6860452f5308"

PINS={
    "source_pack":(SOURCE_PACK_PATH,SOURCE_PACK_BLOB),
    "source_verify":(SOURCE_VERIFY_PATH,SOURCE_VERIFY_BLOB),
    "mission_authority":(MISSION_AUTHORITY_PATH,MISSION_AUTHORITY_BLOB),
    "mission_repair":(MISSION_REPAIR_PATH,"221a4b1554e9ddd1589585eadaa470c84d5d42a8"),
    "claim_guard_v2":(GUARD_V2_PATH,GUARD_V2_BLOB),
    "claim_guard_v2_verify":(GUARD_V2_VERIFY_PATH,GUARD_V2_VERIFY_BLOB),
}


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return value


def _digest(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


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
    if authority_blob_sha!=MISSION_AUTHORITY_BLOB:
        return _fail("MISSION_AUTHORITY_BLOB_DRIFT",observed=authority_blob_sha)
    if not isinstance(pointer,Mapping) or not isinstance(authority,Mapping):
        return _fail("MISSION_BINDING_INPUT_NOT_MAPPING")
    source=pointer.get("authoritative_source")
    if not isinstance(source,Mapping) or source.get("path")!=MISSION_AUTHORITY_PATH:
        return _fail("MISSION_POINTER_AUTHORITY_PATH_DRIFT")
    if pointer.get("schema")!="PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE_POINTER_V1" or pointer.get("status")!="ACTIVE":
        return _fail("MISSION_POINTER_NOT_ACTIVE_CURRENT_SCHEMA")
    if authority.get("schema")!="PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1" or authority.get("status")!="ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
        return _fail("MISSION_AUTHORITY_NOT_ACTIVE")
    if pointer.get("real_objective")!=authority.get("real_objective"):
        return _fail("MISSION_POINTER_OBJECTIVE_DRIFT")
    if pointer.get("opus_5_5_role")!=authority.get("opus_5_5_role"):
        return _fail("MISSION_POINTER_OPUS_ROLE_DRIFT")
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
    resolved=resolve_mission_authority(
        current_pointer,mission_authority,authority_blob_sha=mission_authority_blob_sha
    )
    if resolved.get("pass") is not True:
        return resolved
    if source.get("pass") is not True or source.get("semantic_claim_count")!=12 or source.get("unique_claim_id_count")!=12:
        return _fail("V2_SOURCE_PACK_NOT_VERIFIED_SHAPE")
    if source.get("root_proved_claim_count")!=0 or source.get("property_truth_claim_count")!=0:
        return _fail("V2_SOURCE_PACK_AUTHORITY_OVERCLAIM")
    if source.get("single_active_claim_policy_preserved") is not True or source.get("cross_claim_root_transport_authorized") is not False:
        return _fail("V2_SOURCE_PACK_CLAIM_BOUNDARY_INVALID")
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
        if row.get("semantic_property_truth_authority") is not False:
            return _fail("V2_SOURCE_PROPERTY_AUTHORITY_FORBIDDEN",leaf_id=row.get("leaf_id"))

        claim={
            "claim_kind":"PROPERTY_CERTIFICATE",
            "mission_blob_sha":mission_authority_blob_sha,
            "scope_sha256":scope,
            "target_predicate_sha256":_digest(target),
            "semantics_sha256":_digest(semantics),
            "epoch":EPOCH,
            "authority_id":AUTHORITY_ID,
            "terminal_credit_delta":0,
        }
        claim["claim_id"]=compute_claim_id(claim)
        verdict=claim_guard_v2.validate_claim(
            claim,
            current_pointer=current_pointer,
            mission_authority=mission_authority,
            mission_authority_blob_sha=mission_authority_blob_sha,
        )
        if verdict.get("pass") is not True:
            return _fail("SEMANTIC_FROZEN_CLAIM_INVALID",leaf_id=row.get("leaf_id"),verdict=verdict)

        row["source_v2_claim_id"]=(row.get("frozen_claim") or {}).get("claim_id")
        row["source_v2_claim_authority_transported"]=False
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
    r12=next((x for x in rows if x.get("leaf_id")=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),None)
    if not isinstance(r12,dict):
        return _fail("R12_CURRENT_CLAIM_MISSING")
    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__TWELVE_STABLE_MISSION_AUTHORITY_BOUND_SEMANTIC_CLAIMS_FROZEN__CLAIM_SPECIFIC_ROOT_PROOFS_OPEN__ZERO_PROPERTY_TRUTH_CREDIT",
        "epoch":EPOCH,"authority_id":AUTHORITY_ID,
        "mission_blob_sha":mission_authority_blob_sha,
        "mission_binding_mode":"IMMUTABLE_REAL_MISSION_AUTHORITY__CURRENT_POINTER_COHERENCE",
        "mission_resolution":resolved,
        "semantic_claim_count":12,"unique_claim_id_count":12,
        "claim_id_set_sha256":_digest(sorted(ids)),
        "root_proved_claim_count":0,"property_truth_claim_count":0,
        "single_active_claim_policy_preserved":True,
        "cross_claim_root_transport_authorized":False,
        "source_v2_claim_authority_transported":False,
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
    for key,(rel,expected) in PINS.items():
        p=root/rel
        if not p.is_file() or p.is_symlink():
            return _fail(key.upper()+"_MISSING")
        actual=_blob(p)
        if actual!=expected:
            return _fail(key.upper()+"_BLOB_STALE",expected=expected,observed=actual)
    pointer_path=root/CURRENT_MISSION_PATH
    if not pointer_path.is_file() or pointer_path.is_symlink():
        return _fail("CURRENT_MISSION_POINTER_MISSING")
    try:
        source=_load(root/SOURCE_PACK_PATH)
        source_verify=_load(root/SOURCE_VERIFY_PATH)
        pointer=_load(pointer_path)
        authority=_load(root/MISSION_AUTHORITY_PATH)
    except Exception as exc:
        return _fail("BOUND_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))

    subj=source_verify.get("subject") or {}
    frozen=subj.get("frozen_claim_pack") or {}
    frozen_meta=source_verify.get("frozen_claims") or {}
    if not str(source_verify.get("status") or "").startswith("PASS__"):
        return _fail("V2_SOURCE_VERIFICATION_NOT_PASS")
    if frozen.get("git_blob_sha")!=SOURCE_PACK_BLOB:
        return _fail("V2_SOURCE_VERIFICATION_PACK_BLOB_MISMATCH")
    if frozen_meta.get("semantic_claim_count")!=12 or frozen_meta.get("unique_claim_id_count")!=12:
        return _fail("V2_SOURCE_VERIFICATION_COUNT_MISMATCH")
    if frozen_meta.get("root_proved_claim_count")!=0 or frozen_meta.get("property_truth_claim_count")!=0:
        return _fail("V2_SOURCE_VERIFICATION_AUTHORITY_OVERCLAIM")
    if frozen_meta.get("cross_claim_root_transport_authorized") is not False:
        return _fail("V2_SOURCE_VERIFICATION_CROSS_CLAIM_TRANSPORT")

    return rebind_source_pack(
        source,
        mission_authority_blob_sha=MISSION_AUTHORITY_BLOB,
        current_pointer=pointer,
        mission_authority=authority,
    )


if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
