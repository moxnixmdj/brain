"""Conservative source-explicit semantic claim autofill V2.

V2 preserves V1 target-scope, effect-ID inventory and full-relation autofill,
then adds CERTIFIED_DOCUMENT_EFFECT_FIELD proposals parsed from exact source.

Autofill fills omissions only:
- an existing valid (effect_id, field) claim owns that field slot;
- a malformed field claim blocks all field autofill rather than being silently
  replaced;
- every synthesized claim still requires source_aligned_semantic_proof_v9.

No synthesized claim has semantic, execution, acceptance, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_explicit_semantic_claim_autofill_v1 import (
    synthesize_missing_claims as synthesize_v1,
)
from canonical.runtime.certified_document_effect_field_v1 import parse_effect_fields

SCHEMA="PROJECT_BRAIN_SOURCE_EXPLICIT_SEMANTIC_CLAIM_AUTOFILL_V2"
MAX_COMBINED_CLAIMS=256


def _canon(value:Any)->str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _claim_id(
    source_id:str,
    effect_id:str,
    field:str,
    value:Any,
)->str:
    raw={
        "source_id":source_id,
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
        "effect_id":effect_id,
        "field":field,
        "value":value,
    }
    return "AUTO_SOURCE_V2::"+sha256(_canon(raw).encode("utf-8")).hexdigest()


def _fail(reason:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "reason":reason,
        "synthesized_claims":[],
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }


def synthesize_missing_claims(
    source_text:str,
    *,
    source_id:str,
    existing_claims:Sequence[Any],
)->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text:
        return _fail("SOURCE_TEXT_MISSING")
    if not isinstance(source_id,str) or not source_id.strip():
        return _fail("SOURCE_ID_MISSING")
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
        return _fail(
            "V1_AUTOFILL_FAIL_CLOSED:"+str(base.get("reason") or "UNKNOWN")
        )

    existing_ids=set()
    owned_slots=set()
    block_all_fields=False

    for row in existing_claims:
        if not isinstance(row,Mapping):
            continue
        cid=row.get("claim_id")
        if isinstance(cid,str) and cid:
            existing_ids.add(cid)
        if row.get("kind")!="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            continue
        eid=row.get("effect_id")
        field=row.get("field")
        if (
            isinstance(eid,str) and eid.strip()
            and isinstance(field,str) and field.strip()
        ):
            owned_slots.add((eid.strip(),field.strip()))
        else:
            block_all_fields=True

    for row in base.get("synthesized_claims") or []:
        if isinstance(row,Mapping):
            cid=row.get("claim_id")
            if isinstance(cid,str) and cid:
                existing_ids.add(cid)

    synthesized=list(base.get("synthesized_claims") or [])
    diagnostics=list(base.get("diagnostics") or [])

    parsed=parse_effect_fields(source_text,source=source_id)
    diagnostics.append({
        "primitive":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
        "parse_status":parsed.get("status"),
        "parse_reason":parsed.get("reason"),
    })

    if not block_all_fields and parsed.get("status")=="PARSED":
        for row in parsed.get("fields") or []:
            if not isinstance(row,Mapping):
                continue
            eid=str(row.get("effect_id") or "")
            field=str(row.get("field") or "")
            if not eid or not field or (eid,field) in owned_slots:
                continue
            claim={
                "claim_id":_claim_id(
                    source_id,
                    eid,
                    field,
                    row.get("value"),
                ),
                "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
                "effect_id":eid,
                "field":field,
                "value":row.get("value"),
            }
            if claim["claim_id"] in existing_ids:
                return _fail("AUTO_CLAIM_ID_COLLISION")
            existing_ids.add(claim["claim_id"])
            synthesized.append(claim)

    if len(existing_claims)+len(synthesized)>MAX_COMBINED_CLAIMS:
        return _fail("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")

    return {
        "schema":SCHEMA,
        "status":"PASS__SOURCE_EXPLICIT_OMISSIONS_COMPILED",
        "pass":True,
        "source_id":source_id,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "existing_claim_count":len(existing_claims),
        "v1_synthesized_claim_count":len(base.get("synthesized_claims") or []),
        "field_synthesized_claim_count":(
            len(synthesized)-len(base.get("synthesized_claims") or [])
        ),
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
