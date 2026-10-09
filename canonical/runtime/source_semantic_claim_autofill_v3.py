"""Conservative bounded-natural semantic claim autofill V3.

V3 preserves explicit-source autofill V2 and adds proposals from
certified_bounded_natural_effect_clause_v1.

It fills omissions only:
- caller-owned scope blocks natural scope autofill;
- caller-owned inventory target blocks that natural inventory;
- caller-owned (effect_id, field) blocks that natural field;
- malformed caller claims conservatively block the corresponding autofill class.

All synthesized claims still require source_aligned_semantic_proof_v10.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_explicit_semantic_claim_autofill_v2 import (
    synthesize_missing_claims as synthesize_v2,
)
from canonical.runtime.certified_bounded_natural_effect_clause_v1 import (
    parse_natural_effect_clauses,
)

SCHEMA="PROJECT_BRAIN_SOURCE_SEMANTIC_CLAIM_AUTOFILL_V3"
MAX_COMBINED_CLAIMS=256


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _claim_id(source_id:str,kind:str,slot:str,payload:Mapping[str,Any])->str:
    raw={"source_id":source_id,"kind":kind,"slot":slot,"payload":dict(payload)}
    return "AUTO_SOURCE_V3::"+sha256(_canon(raw).encode("utf-8")).hexdigest()


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

    base=synthesize_v2(
        source_text,
        source_id=source_id,
        existing_claims=existing_claims,
    )
    if base.get("pass") is not True:
        return _fail("V2_AUTOFILL_FAIL_CLOSED:"+str(base.get("reason") or "UNKNOWN"))

    scope_owned=False
    inventory_owned=set()
    field_owned=set()
    block_inventory=False
    block_fields=False
    ids=set()

    def observe(row:Any)->None:
        nonlocal scope_owned,block_inventory,block_fields
        if not isinstance(row,Mapping):
            return
        cid=row.get("claim_id")
        if isinstance(cid,str) and cid:
            ids.add(cid)
        kind=row.get("kind")
        if kind=="CERTIFIED_EFFECT_TARGET_SCOPE":
            scope_owned=True
        elif kind=="CERTIFIED_EFFECT_ID_INVENTORY":
            target=row.get("target_id")
            if isinstance(target,str) and target.strip():
                inventory_owned.add(target.strip())
            else:
                block_inventory=True
        elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            eid=row.get("effect_id")
            field=row.get("field")
            if (
                isinstance(eid,str) and eid.strip()
                and isinstance(field,str) and field.strip()
            ):
                field_owned.add((eid.strip(),field.strip()))
            else:
                block_fields=True

    for row in existing_claims:
        observe(row)
    for row in base.get("synthesized_claims") or []:
        observe(row)

    synthesized=list(base.get("synthesized_claims") or [])
    diagnostics=list(base.get("diagnostics") or [])

    parsed=parse_natural_effect_clauses(source_text,source=source_id)
    diagnostics.append({
        "primitive":"BOUNDED_NATURAL_EFFECT_CLAUSE_V1",
        "parse_status":parsed.get("status"),
        "parse_reason":parsed.get("reason"),
        "parsed_clause_count":len(parsed.get("clauses") or []),
    })

    if parsed.get("status")=="PARSED":
        for row in parsed.get("clauses") or []:
            if not isinstance(row,Mapping):
                continue
            kind=row.get("kind")

            if kind=="TARGET_SCOPE":
                if scope_owned:
                    continue
                payload={
                    "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                    "target_ids":list(row.get("target_ids") or []),
                }
                slot="scope"
                scope_owned=True

            elif kind=="INVENTORY":
                target=str(row.get("target_id") or "")
                if block_inventory or not target or target in inventory_owned:
                    continue
                payload={
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "target_id":target,
                    "effect_ids":list(row.get("effect_ids") or []),
                }
                slot="inventory:"+target
                inventory_owned.add(target)

            elif kind=="FIELD":
                eid=str(row.get("effect_id") or "")
                field=str(row.get("field") or "")
                key=(eid,field)
                if block_fields or not eid or not field or key in field_owned:
                    continue
                payload={
                    "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
                    "effect_id":eid,
                    "field":field,
                    "value":row.get("value"),
                }
                slot="field:"+eid+":"+field
                field_owned.add(key)

            else:
                continue

            claim={
                "claim_id":_claim_id(source_id,payload["kind"],slot,payload),
                **payload,
            }
            if claim["claim_id"] in ids:
                return _fail("AUTO_CLAIM_ID_COLLISION")
            ids.add(claim["claim_id"])
            synthesized.append(claim)

    if len(existing_claims)+len(synthesized)>MAX_COMBINED_CLAIMS:
        return _fail("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")

    return {
        "schema":SCHEMA,
        "status":"PASS__SOURCE_EXPLICIT_AND_BOUNDED_NATURAL_OMISSIONS_COMPILED",
        "pass":True,
        "source_id":source_id,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "existing_claim_count":len(existing_claims),
        "v2_synthesized_claim_count":len(base.get("synthesized_claims") or []),
        "natural_synthesized_claim_count":(
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
