"""Conservative source-explicit semantic claim autofill V2.

V2 preserves V1 scope/inventory/full-relation autofill and adds V9
CERTIFIED_DOCUMENT_EFFECT_DIMENSION claims parsed from exact source bytes.

Autofill fills omissions only. An existing caller claim owns its semantic slot,
including malformed or contradictory claims; V2 never silently repairs it.
All synthesized claims remain non-authoritative and must pass V9 verification.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_explicit_semantic_claim_autofill_v1 import (
    synthesize_missing_claims as synthesize_v1,
    MAX_COMBINED_CLAIMS,
)
from canonical.runtime.certified_document_effect_dimension_v1 import (
    parse_effect_dimensions,
)

SCHEMA="PROJECT_BRAIN_SOURCE_EXPLICIT_SEMANTIC_CLAIM_AUTOFILL_V2"
_ALLOWED_DIMS={
    "target","effect_class","value","conditions",
    "valid_from","valid_until","supersedes",
}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _claim_id(source_id:str,effect_id:str,dimension:str,value:Any)->str:
    raw={
        "source_id":source_id,
        "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
        "effect_id":effect_id,
        "dimension":dimension,
        "value":value,
    }
    return "AUTO_SOURCE_V2::"+sha256(_canon(raw).encode("utf-8")).hexdigest()


def _fail(reason:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
        "reason":reason,"synthesized_claims":[],
        "semantic_truth_authority":False,"execution_authority":False,
        "acceptance_authority":False,"terminal_authority":False,
    }


def synthesize_missing_claims(
    source_text:str,
    *,
    source_id:str,
    existing_claims:Sequence[Any],
)->dict[str,Any]:
    if not isinstance(existing_claims,Sequence) or isinstance(existing_claims,(str,bytes)):
        return _fail("EXISTING_CLAIMS_INVALID")
    if len(existing_claims)>MAX_COMBINED_CLAIMS:
        return _fail("EXISTING_CLAIM_COUNT_EXCEEDS_BOUND")

    base=synthesize_v1(
        source_text,
        source_id=source_id,
        existing_claims=existing_claims,
    )
    if base.get("pass") is not True:
        return _fail("V1_AUTOFILL_FAIL_CLOSED:"+str(base.get("reason") or "UNKNOWN"))

    base_rows=list(base.get("synthesized_claims") or [])
    occupied=set()
    block_all=False
    all_ids=set()
    for row in list(existing_claims)+base_rows:
        if not isinstance(row,Mapping):
            continue
        cid=row.get("claim_id")
        if isinstance(cid,str) and cid:
            all_ids.add(cid)
        if row.get("kind")!="CERTIFIED_DOCUMENT_EFFECT_DIMENSION":
            continue
        eid=row.get("effect_id"); dim=row.get("dimension")
        if (
            isinstance(eid,str) and eid.strip()
            and isinstance(dim,str) and dim in _ALLOWED_DIMS
        ):
            occupied.add((eid.strip(),dim))
        else:
            block_all=True

    parsed=parse_effect_dimensions(source_text,source=source_id)
    dimension_rows=[]
    if not block_all and parsed.get("status")=="PARSED":
        for row in parsed.get("dimensions") or []:
            if not isinstance(row,Mapping):
                continue
            eid=str(row.get("effect_id") or "")
            dim=str(row.get("dimension") or "")
            if not eid or dim not in _ALLOWED_DIMS or (eid,dim) in occupied:
                continue
            claim={
                "claim_id":_claim_id(source_id,eid,dim,row.get("value")),
                "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
                "effect_id":eid,
                "dimension":dim,
                "value":row.get("value"),
            }
            if claim["claim_id"] in all_ids:
                return _fail("AUTO_CLAIM_ID_COLLISION")
            all_ids.add(claim["claim_id"])
            dimension_rows.append(claim)

    synthesized=base_rows+dimension_rows
    if len(existing_claims)+len(synthesized)>MAX_COMBINED_CLAIMS:
        return _fail("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")

    diagnostics=list(base.get("diagnostics") or [])
    diagnostics.append({
        "primitive":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
        "parse_status":parsed.get("status"),
        "parse_reason":parsed.get("reason"),
        "autofill_blocked_by_malformed_existing_dimension_claim":block_all,
    })
    return {
        "schema":SCHEMA,
        "status":"PASS__SOURCE_EXPLICIT_V9_OMISSIONS_COMPILED",
        "pass":True,
        "source_id":source_id,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "existing_claim_count":len(existing_claims),
        "v1_synthesized_claim_count":len(base_rows),
        "dimension_synthesized_claim_count":len(dimension_rows),
        "synthesized_claim_count":len(synthesized),
        "combined_claim_count":len(existing_claims)+len(synthesized),
        "synthesized_claims":synthesized,
        "diagnostics":diagnostics,
        "fills_omissions_only":True,
        "caller_claim_replacement_allowed":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }
