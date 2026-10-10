"""Conservative compositional-natural semantic claim autofill V4.

V4 preserves V3 and proposes claims from
certified_compositional_natural_effect_clause_v1.

It fills omissions only. Synthesized claims have zero semantic authority and
must be independently reaccepted by source_aligned_semantic_proof_v13.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_semantic_claim_autofill_v3 import (
    synthesize_missing_claims as synthesize_v3,
)
from canonical.runtime.certified_compositional_natural_effect_clause_v1 import (
    parse_compositional_effect_clauses,
)

SCHEMA="PROJECT_BRAIN_SOURCE_SEMANTIC_CLAIM_AUTOFILL_V4"
MAX_COMBINED_CLAIMS=256


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _cid(source_id:str,kind:str,slot:str,payload:Mapping[str,Any])->str:
    return "AUTO_SOURCE_V4::"+sha256(
        _canon({"source_id":source_id,"kind":kind,"slot":slot,"payload":dict(payload)}).encode("utf-8")
    ).hexdigest()


def _fail(reason:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":reason,
        "synthesized_claims":[],
        "semantic_truth_authority":False,"execution_authority":False,
        "acceptance_authority":False,"terminal_authority":False,
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

    base=synthesize_v3(
        source_text,
        source_id=source_id,
        existing_claims=existing_claims,
    )
    if base.get("pass") is not True:
        return _fail("V3_AUTOFILL_FAIL_CLOSED:"+str(base.get("reason") or "UNKNOWN"))

    inventory_owned=set()
    field_owned=set()
    block_inventory=False
    block_fields=False
    ids=set()

    def observe(row:Any)->None:
        nonlocal block_inventory,block_fields
        if not isinstance(row,Mapping):
            return
        cid=row.get("claim_id")
        if isinstance(cid,str) and cid:
            ids.add(cid)
        kind=row.get("kind")
        if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
            t=row.get("target_id")
            if isinstance(t,str) and t.strip():
                inventory_owned.add(t.strip())
            else:
                block_inventory=True
        elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            eid=row.get("effect_id"); field=row.get("field")
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

    parsed=parse_compositional_effect_clauses(source_text,source=source_id)
    diagnostics.append({
        "primitive":"COMPOSITIONAL_NATURAL_EFFECT_CLAUSE_V1",
        "parse_status":parsed.get("status"),
        "parse_reason":parsed.get("reason"),
        "parsed_clause_count":len(parsed.get("clauses") or []),
    })

    if parsed.get("status")=="PARSED":
        for row in parsed.get("clauses") or []:
            if not isinstance(row,Mapping):
                continue
            effect=row.get("effect")
            inv=row.get("inventory")
            if not isinstance(effect,Mapping) or not isinstance(inv,Mapping):
                continue
            target=str(inv.get("target_id") or "")
            eid=str(effect.get("effect_id") or "")

            if not block_inventory and target and target not in inventory_owned:
                payload={
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "target_id":target,
                    "effect_ids":list(inv.get("effect_ids") or []),
                }
                cid=_cid(source_id,payload["kind"],"inventory:"+target,payload)
                if cid in ids:
                    return _fail("AUTO_CLAIM_ID_COLLISION")
                ids.add(cid); inventory_owned.add(target)
                synthesized.append({"claim_id":cid,**payload})

            for field in (
                "target_id","effect_class","value","conditions",
                "valid_from","valid_until","supersedes",
            ):
                key=(eid,field)
                if block_fields or not eid or key in field_owned:
                    continue
                payload={
                    "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
                    "effect_id":eid,
                    "field":field,
                    "value":effect.get(field),
                }
                cid=_cid(source_id,payload["kind"],"field:"+eid+":"+field,payload)
                if cid in ids:
                    return _fail("AUTO_CLAIM_ID_COLLISION")
                ids.add(cid); field_owned.add(key)
                synthesized.append({"claim_id":cid,**payload})

    if len(existing_claims)+len(synthesized)>MAX_COMBINED_CLAIMS:
        return _fail("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")

    return {
        "schema":SCHEMA,
        "status":"PASS__SOURCE_COMPOSITIONAL_NATURAL_OMISSIONS_COMPILED",
        "pass":True,
        "source_id":source_id,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "existing_claim_count":len(existing_claims),
        "v3_synthesized_claim_count":len(base.get("synthesized_claims") or []),
        "compositional_synthesized_claim_count":(
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
