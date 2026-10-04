"""Verified novelty-basis and symmetry compression for Universal Learning V8.

V8 may replace relearning with reuse only when an independent exact-byte-bound
receipt proves either:
1) a composition of verified primitives is behavior-preserving for the target, or
2) a verified source skill is symmetry/equivalence-related to the target.

Description length and primitive count rank already-admissible proofs; they are
never evidence of truth.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_VERIFIED_NOVELTY_BASIS_V8"
RELATIONS={"EXACT","PROVEN_SUPERSET"}

class NoveltyBasisError(ValueError):
    pass

def _s(x:Any)->str:
    return " ".join(str(x or "").split())

def _items(xs)->list[str]:
    return sorted({_s(x) for x in (xs or []) if _s(x)})

def signature_digest(signature)->str:
    sig=_items(signature)
    if not sig:
        raise NoveltyBasisError("NONEMPTY_SIGNATURE_REQUIRED")
    raw=json.dumps(sig,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def target_digest(*,target_id:str,target_signature)->str:
    tid=_s(target_id)
    sig=_items(target_signature)
    if not tid or not sig:
        raise NoveltyBasisError("TARGET_ID_AND_SIGNATURE_REQUIRED")
    raw=json.dumps({"target_id":tid,"signature":sig},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def _primitive(raw:Mapping[str,Any])->dict[str,Any]:
    pid=_s(raw.get("primitive_id"))
    sig=_items(raw.get("canonical_signature"))
    if not pid or not sig:
        raise NoveltyBasisError("PRIMITIVE_ID_AND_SIGNATURE_REQUIRED")
    digest=signature_digest(sig)
    rec=raw.get("verification_receipt")
    if not isinstance(rec,Mapping):
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_REQUIRED:"+pid)
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_INVALID:"+pid)
    if rec.get("behavior_verified") is not True:
        raise NoveltyBasisError("PRIMITIVE_BEHAVIOR_NOT_VERIFIED:"+pid)
    if _s(rec.get("primitive_id"))!=pid or rec.get("signature_sha256")!=digest:
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_BINDING_MISMATCH:"+pid)
    rid=_s(rec.get("receipt_id"))
    if not rid:
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_ID_REQUIRED:"+pid)
    return {"primitive_id":pid,"canonical_signature":sig,"signature_sha256":digest,"receipt_id":rid}

def primitive_catalog(primitives:Sequence[Mapping[str,Any]])->dict[str,dict[str,Any]]:
    out={}
    for raw in primitives:
        p=_primitive(raw)
        if p["primitive_id"] in out:
            raise NoveltyBasisError("PRIMITIVE_ID_DUPLICATE:"+p["primitive_id"])
        out[p["primitive_id"]]=p
    return out

def composition_digest(*,target_id:str,target_signature,primitive_ids,composition_steps)->str:
    tids=sorted(_s(x) for x in primitive_ids if _s(x))
    steps=[]
    for i,raw in enumerate(composition_steps or []):
        if not isinstance(raw,Mapping):
            raise NoveltyBasisError("COMPOSITION_STEP_INVALID")
        op=_s(raw.get("op"))
        ins=_items(raw.get("inputs")); outs=_items(raw.get("outputs"))
        if not op:
            raise NoveltyBasisError("COMPOSITION_STEP_OP_REQUIRED")
        steps.append({"index":i,"op":op,"inputs":ins,"outputs":outs})
    if not tids or not steps:
        raise NoveltyBasisError("COMPOSITION_PRIMITIVES_AND_STEPS_REQUIRED")
    body={
        "target_digest":target_digest(target_id=target_id,target_signature=target_signature),
        "primitive_ids":tids,
        "composition_steps":steps,
    }
    raw=json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def verify_composition(
    *,
    target_id:str,
    target_signature,
    primitives:Sequence[Mapping[str,Any]],
    primitive_ids,
    composition_steps,
    verification_receipt:Mapping[str,Any],
    burden:Any=0,
)->dict[str,Any]:
    catalog=primitive_catalog(primitives)
    ids=sorted(_s(x) for x in primitive_ids if _s(x))
    if not ids or any(x not in catalog for x in ids):
        raise NoveltyBasisError("UNKNOWN_OR_EMPTY_COMPOSITION_PRIMITIVE")
    if len(set(ids))!=len(ids):
        raise NoveltyBasisError("COMPOSITION_PRIMITIVE_DUPLICATE")
    digest=composition_digest(
        target_id=target_id,target_signature=target_signature,
        primitive_ids=ids,composition_steps=composition_steps,
    )
    r=verification_receipt
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise NoveltyBasisError("COMPOSITION_RECEIPT_INVALID")
    if r.get("behavior_preserving_on_claimed_scope") is not True:
        raise NoveltyBasisError("COMPOSITION_BEHAVIOR_PRESERVATION_NOT_PROVED")
    relation=_s(r.get("scope_relation"))
    if relation not in RELATIONS:
        raise NoveltyBasisError("COMPOSITION_SCOPE_RELATION_NOT_ADMISSIBLE")
    if r.get("composition_sha256")!=digest:
        raise NoveltyBasisError("COMPOSITION_RECEIPT_DIGEST_MISMATCH")
    if sorted(_s(x) for x in r.get("primitive_ids",[]) if _s(x))!=ids:
        raise NoveltyBasisError("COMPOSITION_RECEIPT_PRIMITIVE_MISMATCH")
    expected_primitive_digests={pid:catalog[pid]["signature_sha256"] for pid in ids}
    if r.get("primitive_signature_sha256")!=expected_primitive_digests:
        raise NoveltyBasisError("COMPOSITION_RECEIPT_PRIMITIVE_DIGEST_MISMATCH")
    td=target_digest(target_id=target_id,target_signature=target_signature)
    if r.get("target_sha256")!=td:
        raise NoveltyBasisError("COMPOSITION_RECEIPT_TARGET_MISMATCH")
    try:
        b=float(burden)
    except Exception as exc:
        raise NoveltyBasisError("BURDEN_INVALID") from exc
    if b<0:
        raise NoveltyBasisError("BURDEN_INVALID")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise NoveltyBasisError("COMPOSITION_RECEIPT_ID_REQUIRED")
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_BASIS_COMPOSITION",
        "target_id":_s(target_id),
        "target_sha256":td,
        "primitive_ids":ids,
        "primitive_count":len(ids),
        "composition_sha256":digest,
        "scope_relation":relation,
        "burden":b,
        "verification_receipt":rid,
        "structural_reuse_authorized":True,
        "target_execution_authorized":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }

def choose_minimum_verified_composition(candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
    admissible=[]
    for raw in candidates:
        if raw.get("status")!="VERIFIED_BASIS_COMPOSITION" or raw.get("structural_reuse_authorized") is not True:
            continue
        admissible.append(dict(raw))
    if not admissible:
        return {"schema":SCHEMA,"status":"NO_VERIFIED_COMPOSITION","selected":None}
    admissible.sort(key=lambda x:(int(x["primitive_count"]),float(x["burden"]),tuple(x["primitive_ids"]),x["composition_sha256"]))
    return {
        "schema":SCHEMA,
        "status":"MINIMUM_VERIFIED_COMPOSITION_SELECTED",
        "selected":admissible[0],
        "ranking_rule":"PRIMITIVE_COUNT_THEN_BURDEN_THEN_DETERMINISTIC_TIEBREAK__TRUTH_PREESTABLISHED_BY_RECEIPTS",
    }

def symmetry_digest(*,source_id:str,target_id:str,transform_id:str,source_signature,target_signature)->str:
    body={
        "source_id":_s(source_id),"target_id":_s(target_id),"transform_id":_s(transform_id),
        "source_signature_sha256":signature_digest(source_signature),
        "target_signature_sha256":signature_digest(target_signature),
    }
    if not body["source_id"] or not body["target_id"] or not body["transform_id"]:
        raise NoveltyBasisError("SYMMETRY_IDS_REQUIRED")
    raw=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def verify_symmetry(
    *,
    source_primitive:Mapping[str,Any],
    target_id:str,
    target_signature,
    transform_id:str,
    verification_receipt:Mapping[str,Any],
)->dict[str,Any]:
    source=_primitive(source_primitive)
    digest=symmetry_digest(
        source_id=source["primitive_id"],target_id=target_id,transform_id=transform_id,
        source_signature=source["canonical_signature"],target_signature=target_signature,
    )
    r=verification_receipt
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise NoveltyBasisError("SYMMETRY_RECEIPT_INVALID")
    if r.get("bijective_on_claimed_scope") is not True or r.get("behavior_equivariant") is not True or r.get("inverse_verified") is not True:
        raise NoveltyBasisError("SYMMETRY_PROPERTIES_NOT_PROVED")
    relation=_s(r.get("scope_relation"))
    if relation not in RELATIONS:
        raise NoveltyBasisError("SYMMETRY_SCOPE_RELATION_NOT_ADMISSIBLE")
    if r.get("symmetry_sha256")!=digest:
        raise NoveltyBasisError("SYMMETRY_RECEIPT_DIGEST_MISMATCH")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise NoveltyBasisError("SYMMETRY_RECEIPT_ID_REQUIRED")
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_SYMMETRY_REUSE",
        "source_primitive_id":source["primitive_id"],
        "target_id":_s(target_id),
        "transform_id":_s(transform_id),
        "symmetry_sha256":digest,
        "scope_relation":relation,
        "verification_receipt":rid,
        "structural_reuse_authorized":True,
        "target_execution_authorized":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }
