"""Stable-claim lossless identity carrier for professional semantic leaves.

Consumes the verified V3 stable semantic claim pack and reuses the universal
identity-carrier theorem:
    Omega_C = W_C
    pi_C = identity
so pi_C(w1)=pi_C(w2) implies w1=w2 and therefore M_C(w1)=M_C(w2).

This closes only the mission-sufficient carrier precondition for each exact
stable claim. It does not transport root proofs across claims and grants no
semantic property truth, quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import coverage_claim_scope_guard_v2 as claim_guard
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_V3"
CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_CERTIFICATE_V3"
BATCH_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_BATCH_V3"
CARRIER_KIND="OTHER_TYPED_OBJECT_WITH_PROVED_MISSION_FACTORIZATION"
PROJECTION="IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE"
PROOF_MODE="FORMAL_REDUCTION__IDENTITY_FUNCTION_CONGRUENCE"
MISSION_BLOB=pack_v3.EXPECTED_MISSION_AUTHORITY_BLOB


def _digest(value:Any)->str:
    return sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "universal_factorization_proved":False,
        "semantic_information_loss":None,
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }


def build_certificate(row:Mapping[str,Any])->dict[str,Any]:
    claim=row.get("frozen_claim") or {}
    cid=str(claim.get("claim_id") or "")
    world="W_CLAIM_WORLD_STATE:"+cid
    return {
        "schema":CERT_SCHEMA,
        "claim_id":cid,
        "mission_blob_sha":claim.get("mission_blob_sha"),
        "scope_sha256":claim.get("scope_sha256"),
        "target_predicate_sha256":claim.get("target_predicate_sha256"),
        "semantics_sha256":claim.get("semantics_sha256"),
        "leaf_id":row.get("leaf_id"),
        "root_id":row.get("root_id"),
        "carrier_kind":CARRIER_KIND,
        "world_space_id":world,
        "carrier_space_id":world,
        "projection":PROJECTION,
        "projection_total":True,
        "projection_injective":True,
        "semantic_information_loss":False,
        "carrier_abstraction_applied":False,
        "mission_function_domain":"EXACT_COMPLETE_FROZEN_CLAIM_WORLD_STATE",
        "factorization":{
            "formula":"FOR_ALL_w1_w2_IN_W_C__pi_C(w1)=pi_C(w2)_IMPLIES_M_C(w1)=M_C(w2)",
            "proof_mode":PROOF_MODE,
            "premises":[
                "OMEGA_C_EQUALS_W_C",
                "PI_C_IS_IDENTITY_ON_W_C",
                "IDENTITY_EQUAL_OUTPUT_IMPLIES_EQUAL_INPUT",
                "M_C_IS_A_FUNCTION_ON_W_C",
            ],
            "derivation":[
                "ASSUME_PI_C_W1_EQUALS_PI_C_W2",
                "SUBSTITUTE_IDENTITY_TO_DERIVE_W1_EQUALS_W2",
                "APPLY_FUNCTION_CONGRUENCE_TO_M_C",
                "DERIVE_M_C_W1_EQUALS_M_C_W2",
            ],
            "universal_not_sampled":True,
            "universal_factorization_proved":True,
        },
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def evaluate_row(
    row:Mapping[str,Any],
    certificate:Mapping[str,Any],
    *,
    current_pointer:Mapping[str,Any],
    mission_authority:Mapping[str,Any],
)->dict[str,Any]:
    if not isinstance(row,Mapping) or not isinstance(certificate,Mapping):
        return _fail("INPUT_NOT_MAPPING")
    claim=row.get("frozen_claim")
    if not isinstance(claim,Mapping):
        return _fail("FROZEN_CLAIM_MISSING")
    leaf_id=row.get("leaf_id")
    root_id=row.get("root_id")
    target=row.get("target_predicate")
    semantics=row.get("semantics")
    scope=row.get("scope_definition_sha256")
    if not isinstance(leaf_id,str) or not leaf_id.endswith("::SEMANTIC"):
        return _fail("SEMANTIC_LEAF_ID_INVALID")
    if not isinstance(root_id,str) or not root_id:
        return _fail("ROOT_ID_INVALID")
    if not isinstance(target,Mapping) or not isinstance(semantics,Mapping):
        return _fail("CLAIM_SEMANTICS_INVALID")
    if not isinstance(scope,str) or len(scope)!=64:
        return _fail("CLAIM_SCOPE_INVALID")

    guarded=claim_guard.validate_claim(
        claim,
        current_pointer=current_pointer,
        mission_authority=mission_authority,
        mission_authority_blob_sha=MISSION_BLOB,
    )
    if guarded.get("pass") is not True:
        return _fail("STABLE_CLAIM_GUARD_REJECTED",claim_guard=guarded)
    if claim.get("scope_sha256")!=scope:
        return _fail("CLAIM_SCOPE_BINDING_DRIFT")
    if claim.get("target_predicate_sha256")!=_digest(target):
        return _fail("TARGET_PREDICATE_BINDING_DRIFT")
    if claim.get("semantics_sha256")!=_digest(semantics):
        return _fail("SEMANTICS_BINDING_DRIFT")

    expected=build_certificate(row)
    fixed=(
        "schema","claim_id","mission_blob_sha","scope_sha256",
        "target_predicate_sha256","semantics_sha256","leaf_id","root_id",
        "carrier_kind","world_space_id","carrier_space_id","projection",
        "projection_total","projection_injective","semantic_information_loss",
        "carrier_abstraction_applied","mission_function_domain",
    )
    for field in fixed:
        if certificate.get(field)!=expected.get(field):
            return _fail("IDENTITY_CARRIER_BINDING_DRIFT:"+field)
    if certificate.get("world_space_id")!=certificate.get("carrier_space_id"):
        return _fail("CARRIER_SPACE_NOT_IDENTICAL_TO_WORLD_SPACE")

    proof=certificate.get("factorization")
    expected_proof=expected["factorization"]
    if not isinstance(proof,Mapping):
        return _fail("FACTORIZATION_PROOF_MISSING")
    for field in (
        "formula","proof_mode","premises","derivation",
        "universal_not_sampled","universal_factorization_proved",
    ):
        if proof.get(field)!=expected_proof.get(field):
            return _fail("FACTORIZATION_PROOF_DRIFT:"+field)
    if proof.get("universal_not_sampled") is not True:
        return _fail("UNIVERSAL_FORMAL_PROOF_REQUIRED")
    if proof.get("universal_factorization_proved") is not True:
        return _fail("UNIVERSAL_FACTORIZATION_NOT_PROVED")

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__STABLE_CLAIM_SCOPED_IDENTITY_CARRIER_UNIVERSAL_FACTORIZATION",
        "leaf_id":leaf_id,"root_id":root_id,
        "claim_id":claim.get("claim_id"),
        "mission_blob_sha":MISSION_BLOB,
        "scope_sha256":claim.get("scope_sha256"),
        "target_predicate_sha256":claim.get("target_predicate_sha256"),
        "semantics_sha256":claim.get("semantics_sha256"),
        "carrier_kind":CARRIER_KIND,"projection":PROJECTION,
        "projection_total":True,"projection_injective":True,
        "semantic_information_loss":False,
        "carrier_abstraction_applied":False,
        "universal_factorization_proved":True,
        "proof_basis":"IDENTITY_PROJECTION_PLUS_FUNCTION_CONGRUENCE__NO_FINITE_WITNESS_SET",
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def evaluate_pack(
    source:Mapping[str,Any],
    *,
    current_pointer:Mapping[str,Any],
    mission_authority:Mapping[str,Any],
)->dict[str,Any]:
    if not isinstance(source,Mapping) or source.get("pass") is not True:
        return _fail("STABLE_CLAIM_PACK_REQUIRED")
    if source.get("semantic_claim_count")!=12 or source.get("unique_claim_id_count")!=12:
        return _fail("STABLE_CLAIM_PACK_NOT_EXACT_12")
    if source.get("mission_blob_sha")!=MISSION_BLOB:
        return _fail("STABLE_CLAIM_PACK_MISSION_DRIFT")
    if source.get("single_active_claim_policy_preserved") is not True:
        return _fail("SINGLE_ACTIVE_CLAIM_POLICY_NOT_PRESERVED")
    if source.get("cross_claim_root_transport_authorized") is not False:
        return _fail("CROSS_CLAIM_ROOT_TRANSPORT_MUST_REMAIN_FORBIDDEN")
    claims=source.get("claims")
    if not isinstance(claims,list) or len(claims)!=12:
        return _fail("STABLE_CLAIM_SET_NOT_12")

    rows=[]
    claim_ids=[]
    leaf_ids=[]
    for row in sorted(claims,key=lambda x:str((x or {}).get("leaf_id") or "")):
        if not isinstance(row,Mapping):
            return _fail("STABLE_CLAIM_ROW_INVALID")
        cert=build_certificate(row)
        verdict=evaluate_row(
            row,cert,
            current_pointer=current_pointer,
            mission_authority=mission_authority,
        )
        if verdict.get("pass") is not True:
            return _fail(
                "STABLE_IDENTITY_CARRIER_BATCH_MEMBER_FAILED",
                leaf_id=row.get("leaf_id"),verdict=verdict,
            )
        claim_ids.append(str(verdict["claim_id"]))
        leaf_ids.append(str(verdict["leaf_id"]))
        rows.append({
            "leaf_id":verdict["leaf_id"],
            "root_id":verdict["root_id"],
            "claim_id":verdict["claim_id"],
            "scope_sha256":verdict["scope_sha256"],
            "target_predicate_sha256":verdict["target_predicate_sha256"],
            "semantics_sha256":verdict["semantics_sha256"],
            "universal_factorization_proved":True,
            "leaf_property_truth_authority":False,
        })
    if len(set(claim_ids))!=12 or len(set(leaf_ids))!=12:
        return _fail("STABLE_BATCH_IDENTITIES_NOT_UNIQUE")
    r12=next(
        (x for x in rows if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),
        None,
    )
    if not r12 or r12["claim_id"]!=source.get("r12_claim_id"):
        return _fail("R12_STABLE_CLAIM_ID_DRIFT")

    return {
        "schema":BATCH_SCHEMA,"pass":True,
        "status":"PASS__12_OF_12_STABLE_V3_SEMANTIC_CLAIMS_IDENTITY_CARRIER_FACTORIZATION",
        "mission_blob_sha":MISSION_BLOB,
        "source_claim_pack_schema":source.get("schema"),
        "source_claim_id_set_sha256":source.get("claim_id_set_sha256"),
        "semantic_leaf_count":12,
        "factorization_pass_count":12,
        "mission_sufficient_carrier_factorization_proved_count":12,
        "unique_claim_id_count":12,
        "r12_claim_id":r12["claim_id"],
        "all_projection_total":True,
        "all_projection_injective":True,
        "all_semantic_information_loss_false":True,
        "cross_claim_root_transport_authorized":False,
        "rows":rows,
        "property_truth_count_delta":0,
        "next":"INSTANTIATE_CLAIM_SPECIFIC_CC_R1_CC_R2_CC_R3_AND_R4__STABLE_IDENTITY_CARRIER_PRECONDITION_CLOSED",
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root else ROOT
    source=pack_v3.verify(repo_root=root)
    if not isinstance(source,Mapping) or source.get("pass") is not True:
        return _fail(
            "STABLE_CLAIM_PACK_VERIFICATION_FAILED",
            source_status=source.get("status") if isinstance(source,Mapping) else None,
            source_reason=source.get("reason") if isinstance(source,Mapping) else None,
        )
    try:
        pointer=json.loads((root/pack_v3.MISSION_POINTER_PATH).read_text(encoding="utf-8"))
        authority=json.loads((root/pack_v3.MISSION_AUTHORITY_PATH).read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail("MISSION_BINDING_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
    return evaluate_pack(
        source,current_pointer=pointer,mission_authority=authority
    )


if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
