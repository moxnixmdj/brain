"""Identity-carrier certificates for stable mission-authority semantic claims V3."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_semantic_identity_carrier_v2 as carrier_v2

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_V3"
BATCH_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_BATCH_V3"
MISSION_AUTHORITY_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
EXPECTED_R12_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "mission_sufficient_carrier_factorization_proved_count":0,
        "semantic_truth_authority":False,"quality_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "incremental_spend_usd":0,**extra,
    }


def evaluate_pack(pack:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(pack,Mapping) or pack.get("pass") is not True:
        return _fail("V3_PACK_NOT_PASS")
    if pack.get("mission_blob_sha")!=MISSION_AUTHORITY_BLOB:
        return _fail("MISSION_AUTHORITY_BINDING_DRIFT")
    if pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:
        return _fail("V3_PACK_COUNT_INVALID")
    claims=pack.get("claims")
    if not isinstance(claims,list) or len(claims)!=12:
        return _fail("V3_CLAIMS_INVALID")

    rows=[]
    for row in sorted(claims,key=lambda x:str(x.get("leaf_id") or "")):
        if not isinstance(row,Mapping):
            return _fail("V3_CLAIM_ROW_INVALID")
        cert=carrier_v2.build_certificate(row)
        verdict=carrier_v2.evaluate_claim(
            row,cert,current_mission_blob_sha=MISSION_AUTHORITY_BLOB
        )
        if verdict.get("pass") is not True:
            return _fail(
                "V3_IDENTITY_CARRIER_MEMBER_FAILED",
                leaf_id=row.get("leaf_id"),
                verdict=verdict,
            )
        rows.append({
            "leaf_id":verdict["leaf_id"],
            "root_id":verdict["root_id"],
            "claim_id":verdict["claim_id"],
            "scope_sha256":verdict["scope_sha256"],
            "target_predicate_sha256":verdict["target_predicate_sha256"],
            "semantics_sha256":verdict["semantics_sha256"],
            "projection_total":verdict["projection_total"],
            "projection_injective":verdict["projection_injective"],
            "semantic_information_loss":verdict["semantic_information_loss"],
            "universal_factorization_proved":verdict["universal_factorization_proved"],
        })

    ids=[x["claim_id"] for x in rows]
    if len(ids)!=12 or len(set(ids))!=12:
        return _fail("V3_CARRIER_CLAIM_IDS_NOT_UNIQUE")
    r12=next((x for x in rows if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),None)
    if not r12 or r12["claim_id"]!=EXPECTED_R12_CLAIM_ID:
        return _fail("R12_V3_CLAIM_ID_DRIFT",observed=(r12 or {}).get("claim_id"))

    return {
        "schema":BATCH_SCHEMA,"pass":True,
        "status":"PASS__V3_12_OF_12_STABLE_MISSION_AUTHORITY_SEMANTIC_CLAIMS_IDENTITY_CARRIER_FACTORIZATION",
        "semantic_leaf_count":12,
        "factorization_pass_count":12,
        "unique_claim_id_count":12,
        "mission_blob_sha":MISSION_AUTHORITY_BLOB,
        "r12_claim_id":r12["claim_id"],
        "all_projection_total":True,
        "all_projection_injective":True,
        "all_semantic_information_loss_false":True,
        "mission_sufficient_carrier_factorization_proved_count":12,
        "rows":rows,
        "property_truth_count_delta":0,
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
    pack=pack_v3.verify(repo_root=root)
    if pack.get("pass") is not True:
        return _fail(
            "V3_CLAIM_GENERATOR_FAILED",
            source_status=pack.get("status"),
            source_reason=pack.get("reason"),
        )
    return evaluate_pack(pack)


if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
