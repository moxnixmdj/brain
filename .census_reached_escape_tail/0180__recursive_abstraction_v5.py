"""Proof-gated recursive abstraction induction for Universal Learning V5."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RECURSIVE_ABSTRACTION_V5"
BASES={"STRUCTURAL_EQUIVALENCE","CAUSAL_ISOMORPHISM","FORMAL_REDUCTION","PROTOCOL_EQUIVALENCE"}
RELATIONS={"EXACT","PROVEN_SUPERSET"}

class RecursiveAbstractionError(ValueError):
    pass

def _signature(values)->list[str]:
    out=sorted({str(x).strip() for x in values if str(x).strip()})
    if not out:
        raise RecursiveAbstractionError("CANONICAL_SIGNATURE_REQUIRED")
    return out

def signature_digest(values)->str:
    sig=_signature(values)
    body=json.dumps(sig,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _verify_skill(raw:Mapping[str,Any])->tuple[str,list[str],str]:
    sid=str(raw.get("skill_id") or "").strip()
    if not sid:
        raise RecursiveAbstractionError("SKILL_ID_REQUIRED")
    if raw.get("independent_verified") is not True or raw.get("exact_byte_bound") is not True or raw.get("conclusion")!="success":
        raise RecursiveAbstractionError("SKILL_NOT_INDEPENDENTLY_VERIFIED:"+sid)
    sig=_signature(raw.get("canonical_signature",[]))
    rec=raw.get("canonicalization_receipt")
    if not isinstance(rec,Mapping):
        raise RecursiveAbstractionError("CANONICALIZATION_RECEIPT_REQUIRED:"+sid)
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise RecursiveAbstractionError("CANONICALIZATION_RECEIPT_INVALID:"+sid)
    if str(rec.get("skill_id") or "").strip()!=sid:
        raise RecursiveAbstractionError("CANONICALIZATION_SKILL_BINDING_MISMATCH:"+sid)
    if rec.get("signature_sha256")!=signature_digest(sig):
        raise RecursiveAbstractionError("CANONICALIZATION_SIGNATURE_DIGEST_MISMATCH:"+sid)
    basis=str(rec.get("mapping_basis") or "").strip()
    if basis not in BASES:
        raise RecursiveAbstractionError("CANONICALIZATION_BASIS_NOT_ADMISSIBLE:"+sid)
    rid=str(rec.get("receipt_id") or "").strip()
    if not rid:
        raise RecursiveAbstractionError("CANONICALIZATION_RECEIPT_ID_REQUIRED:"+sid)
    return sid,sig,rid

def _candidate_digest(*,source_skill_ids,common_signature)->str:
    body=json.dumps({"source_skill_ids":sorted(source_skill_ids),"common_signature":sorted(common_signature)},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def induce_candidate(skills:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if len(skills)<2:
        raise RecursiveAbstractionError("AT_LEAST_TWO_VERIFIED_SKILLS_REQUIRED")
    ids=[];receipts=[];common=None
    for raw in skills:
        sid,sig,rid=_verify_skill(raw)
        if sid in ids:
            raise RecursiveAbstractionError("SKILL_ID_DUPLICATE:"+sid)
        ids.append(sid);receipts.append(rid)
        common=set(sig) if common is None else common & set(sig)
    common=sorted(common or set())
    if not common:
        raise RecursiveAbstractionError("NO_COMMON_VERIFIED_STRUCTURE")
    digest=_candidate_digest(source_skill_ids=ids,common_signature=common)
    return {
        "schema":SCHEMA,
        "status":"ABSTRACTION_CANDIDATE_ONLY",
        "source_skill_ids":sorted(ids),
        "canonicalization_receipts":sorted(receipts),
        "common_signature":common,
        "candidate_sha256":digest,
        "verified_abstraction":False,
        "structural_reuse_authorized":False,
        "separate_abstraction_verification_required":True,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }

def verify_candidate(*,candidate:Mapping[str,Any],verification_receipt:Mapping[str,Any])->dict[str,Any]:
    digest=str(candidate.get("candidate_sha256") or "").strip()
    source_ids=sorted(str(x).strip() for x in candidate.get("source_skill_ids",[]) if str(x).strip())
    common=_signature(candidate.get("common_signature",[]))
    if digest!=_candidate_digest(source_skill_ids=source_ids,common_signature=common):
        raise RecursiveAbstractionError("ABSTRACTION_CANDIDATE_DIGEST_INVALID")
    r=verification_receipt
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise RecursiveAbstractionError("ABSTRACTION_VERIFICATION_RECEIPT_INVALID")
    if r.get("candidate_sha256")!=digest:
        raise RecursiveAbstractionError("ABSTRACTION_RECEIPT_DIGEST_MISMATCH")
    if sorted(str(x).strip() for x in r.get("source_skill_ids",[]) if str(x).strip())!=source_ids:
        raise RecursiveAbstractionError("ABSTRACTION_RECEIPT_SOURCE_BINDING_MISMATCH")
    if r.get("behavior_preserving_across_source_skills") is not True:
        raise RecursiveAbstractionError("ABSTRACTION_BEHAVIOR_PRESERVATION_NOT_PROVED")
    relation=str(r.get("scope_relation") or "").strip()
    if relation not in RELATIONS:
        raise RecursiveAbstractionError("ABSTRACTION_SCOPE_RELATION_NOT_ADMISSIBLE")
    rid=str(r.get("receipt_id") or "").strip()
    if not rid:
        raise RecursiveAbstractionError("ABSTRACTION_RECEIPT_ID_REQUIRED")
    return {
        **dict(candidate),
        "status":"VERIFIED_STRUCTURAL_ABSTRACTION",
        "verified_abstraction":True,
        "structural_reuse_authorized":True,
        "scope_relation":relation,
        "verification_receipt":rid,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }
