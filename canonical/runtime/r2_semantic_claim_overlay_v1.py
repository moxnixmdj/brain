"""Hash-bound additive semantic claim overlay V1."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_R2_SEMANTIC_CLAIM_OVERLAY_V1"
MAX_CLAIMS=128


def _cid(row:Mapping[str,Any])->str:
    return str(row.get("claim_id") or "").strip()


def apply(
    problem:Mapping[str,Any],
    overlay:Any,
    *,
    input_sha256:str,
)->tuple[dict[str,Any],dict[str,Any]]:
    merged=deepcopy(dict(problem))
    docs=merged.get("source_documents")
    if not isinstance(docs,list) or not all(isinstance(x,Mapping) for x in docs):
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    by_id={}
    seen=set()
    for doc in docs:
        did=str(doc.get("document_id") or "").strip()
        claims=doc.get("claims")
        if not did or did in by_id:
            raise ValueError("SOURCE_DOCUMENT_ID_INVALID_OR_DUPLICATE")
        if not isinstance(claims,list) or not all(isinstance(x,Mapping) for x in claims):
            raise ValueError("SOURCE_DOCUMENT_CLAIMS_INVALID:"+did)
        for claim in claims:
            cid=_cid(claim)
            if not cid or cid in seen:
                raise ValueError("EXISTING_CLAIM_ID_INVALID_OR_DUPLICATE:"+cid)
            seen.add(cid)
        by_id[did]=doc
    if overlay is None:
        return merged,{
            "provided":False,"schema":SCHEMA,"input_sha256":input_sha256,
            "overlay_claim_count":0,"overlay_sha256":None,
            "candidate_claims_authority":False,
        }
    if not isinstance(overlay,Mapping):
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_NOT_OBJECT")
    if set(overlay)!={"schema","input_sha256","claims_by_document"}:
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_FIELD_SET_INVALID")
    if overlay.get("schema")!=SCHEMA:
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_SCHEMA_INVALID")
    if str(overlay.get("input_sha256") or "")!=input_sha256:
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_INPUT_SHA256_MISMATCH")
    rows_by_doc=overlay.get("claims_by_document")
    if not isinstance(rows_by_doc,Mapping):
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_CLAIMS_BY_DOCUMENT_INVALID")
    if any(str(k) not in by_id for k in rows_by_doc):
        raise ValueError("SEMANTIC_CLAIM_OVERLAY_UNKNOWN_DOCUMENT")
    count=0
    for raw_did,rows in rows_by_doc.items():
        did=str(raw_did)
        if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
            raise ValueError("SEMANTIC_CLAIM_OVERLAY_DOCUMENT_CLAIMS_INVALID:"+did)
        for raw in rows:
            if not isinstance(raw,Mapping):
                raise ValueError("SEMANTIC_CLAIM_OVERLAY_CLAIM_NOT_OBJECT:"+did)
            claim=deepcopy(dict(raw)); cid=_cid(claim)
            if not cid:
                raise ValueError("SEMANTIC_CLAIM_OVERLAY_CLAIM_ID_REQUIRED:"+did)
            if cid in seen:
                raise ValueError("SEMANTIC_CLAIM_OVERLAY_CLAIM_ID_COLLISION:"+cid)
            seen.add(cid); by_id[did]["claims"].append(claim); count+=1
            if count>MAX_CLAIMS:
                raise ValueError("SEMANTIC_CLAIM_OVERLAY_TOO_LARGE")
    raw=json.dumps(dict(overlay),sort_keys=True,separators=(",",":"),
                   ensure_ascii=False,allow_nan=False).encode()
    return merged,{
        "provided":True,"schema":SCHEMA,"input_sha256":input_sha256,
        "overlay_claim_count":count,"overlay_sha256":sha256(raw).hexdigest(),
        "candidate_claims_authority":False,
    }


def contract(problem:Mapping[str,Any],*,input_path:str,input_sha256:str)->dict[str,Any]:
    docs=problem.get("source_documents")
    ids=sorted(str(x.get("document_id")) for x in docs or []
               if isinstance(x,Mapping) and str(x.get("document_id") or "").strip())
    return {
        "schema":SCHEMA,"request_patch_field":"semantic_claim_overlay",
        "input_path":input_path,"input_sha256":input_sha256,"document_ids":ids,
        "maximum_overlay_claims":MAX_CLAIMS,
        "overlay_semantics":"ADDITIVE_CANDIDATE_CLAIMS_ONLY",
        "source_mutation_authorized":False,"candidate_claims_authority":False,
        "downstream_source_proof_required":True,
        "downstream_independent_verification_required":True,
    }
