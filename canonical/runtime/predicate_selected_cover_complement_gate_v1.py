"""Predicate-selected-cover complement gate.

This gate checks the STRUCTURE of claimed evidence for a finite set of
content-addressed positive admission predicates A_i(c). It validates the
declared predicate-set identity and asserted complement result that:

  S_TRACE(c) AND NOT(A_1(c) OR ... OR A_n(c))

is unsatisfiable over the claimed scope.

It DOES NOT authenticate these receipts, check their Git objects, execute
admission predicates, validate their adequacy, or verify any UNSAT proof.
A self-asserted receipt with SHA-shaped strings must NEVER authorize selected
cover, U-empty, ABC closure, or terminal truth. This structural checker is
only a prerequisite for a separate independently authenticated semantic proof
checker. D finality remains separate. This hardening intentionally fails closed
for claims that lack that external independent proof validation.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_PREDICATE_SELECTED_COVER_COMPLEMENT_GATE_V1"
ALLOWED_PROOF_KINDS={"FORMAL_UNSAT","UNIVERSAL_THEOREM","PROVEN_SUPERSET_COVER"}

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha256(x:Any)->str:
    return "sha256:"+sha256(_canon(x).encode("utf-8")).hexdigest()

def _hex40(x:Any)->bool:
    return isinstance(x,str) and len(x)==40 and all(c in "0123456789abcdef" for c in x)

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "selected_cover_complete_authorized":False,
        "u_empty_authorized":False,
        "abc_closed_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def predicate_set_digest(scope_id:str, routes:Sequence[Mapping[str,Any]])->str:
    rows=[]
    for row in routes:
        rows.append({
            "cell_id":str(row.get("cell_id") or ""),
            "route_id":str(row.get("route_id") or ""),
            "admission_predicate_id":str(row.get("admission_predicate_id") or ""),
            "admission_predicate_blob_sha":str(row.get("admission_predicate_blob_sha") or ""),
            "adequacy_certificate_blob_sha":str(row.get("adequacy_certificate_blob_sha") or ""),
            "admission_soundness_receipt_blob_sha":str(row.get("admission_soundness_receipt_blob_sha") or ""),
        })
    rows.sort(key=lambda x:(x["admission_predicate_id"],x["route_id"],x["cell_id"]))
    return _sha256({"scope_id":scope_id,"routes":rows})

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    scope_id=str(payload.get("scope_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    routes=payload.get("routes")
    if not isinstance(routes,Sequence) or isinstance(routes,(str,bytes)) or not routes:
        return _fail("ROUTES_REQUIRED")

    seen_predicates=set()
    seen_routes=set()
    normalized=[]
    for i,row in enumerate(routes):
        if not isinstance(row,Mapping):
            return _fail("ROUTE_NOT_MAPPING",index=i)
        cell_id=str(row.get("cell_id") or "").strip()
        route_id=str(row.get("route_id") or "").strip()
        pid=str(row.get("admission_predicate_id") or "").strip()
        if not cell_id or not route_id or not pid:
            return _fail("ROUTE_IDENTITY_REQUIRED",index=i)
        if route_id in seen_routes:
            return _fail("ROUTE_ID_DUPLICATE",route_id=route_id)
        seen_routes.add(route_id)
        if pid in seen_predicates:
            return _fail("ADMISSION_PREDICATE_ID_DUPLICATE",admission_predicate_id=pid)
        seen_predicates.add(pid)

        for field in (
            "admission_predicate_blob_sha",
            "adequacy_certificate_blob_sha",
            "admission_soundness_receipt_blob_sha",
        ):
            if not _hex40(row.get(field)):
                return _fail("INVALID_GIT_BLOB_SHA",index=i,field=field)

        sr=row.get("admission_soundness_receipt")
        if not isinstance(sr,Mapping):
            return _fail("ADMISSION_SOUNDNESS_RECEIPT_REQUIRED",route_id=route_id)
        if (
            sr.get("independent_verified") is not True
            or sr.get("exact_byte_bound") is not True
            or sr.get("conclusion")!="success"
            or sr.get("admission_implies_route_adequacy") is not True
        ):
            return _fail("ADMISSION_SOUNDNESS_UNPROVED",route_id=route_id)
        if str(sr.get("scope_id") or "").strip()!=scope_id:
            return _fail("ADMISSION_SOUNDNESS_SCOPE_MISMATCH",route_id=route_id)
        if str(sr.get("cell_id") or "").strip()!=cell_id:
            return _fail("ADMISSION_SOUNDNESS_CELL_MISMATCH",route_id=route_id)
        if str(sr.get("route_id") or "").strip()!=route_id:
            return _fail("ADMISSION_SOUNDNESS_ROUTE_MISMATCH",route_id=route_id)
        if str(sr.get("admission_predicate_id") or "").strip()!=pid:
            return _fail("ADMISSION_SOUNDNESS_PREDICATE_MISMATCH",route_id=route_id)
        if sr.get("admission_predicate_blob_sha")!=row.get("admission_predicate_blob_sha"):
            return _fail("ADMISSION_SOUNDNESS_PREDICATE_BLOB_MISMATCH",route_id=route_id)
        if sr.get("adequacy_certificate_blob_sha")!=row.get("adequacy_certificate_blob_sha"):
            return _fail("ADMISSION_SOUNDNESS_ADEQUACY_BLOB_MISMATCH",route_id=route_id)

        normalized.append({
            "cell_id":cell_id,"route_id":route_id,"admission_predicate_id":pid,
            "admission_predicate_blob_sha":row["admission_predicate_blob_sha"],
            "adequacy_certificate_blob_sha":row["adequacy_certificate_blob_sha"],
            "admission_soundness_receipt_blob_sha":row["admission_soundness_receipt_blob_sha"],
        })

    digest=predicate_set_digest(scope_id,routes)
    cr=payload.get("complement_coverage_receipt")
    if not isinstance(cr,Mapping):
        return _fail("COMPLEMENT_COVERAGE_RECEIPT_REQUIRED")
    if (
        cr.get("independent_verified") is not True
        or cr.get("exact_byte_bound") is not True
        or cr.get("conclusion")!="success"
        or cr.get("residual_complement_unsat") is not True
    ):
        return _fail("RESIDUAL_COMPLEMENT_UNSAT_UNPROVED")
    if cr.get("proof_kind") not in ALLOWED_PROOF_KINDS:
        return _fail("COMPLEMENT_PROOF_KIND_INVALID")
    if str(cr.get("scope_id") or "").strip()!=scope_id:
        return _fail("COMPLEMENT_SCOPE_MISMATCH")
    if cr.get("predicate_set_sha256")!=digest:
        return _fail("COMPLEMENT_PREDICATE_SET_DIGEST_MISMATCH")
    if str(cr.get("residual_definition") or "")!="S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE":
        return _fail("COMPLEMENT_RESIDUAL_DEFINITION_MISMATCH")
    if not str(cr.get("receipt_id") or "").strip():
        return _fail("COMPLEMENT_RECEIPT_ID_REQUIRED")

    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"UNVERIFIED__STRUCTURAL_COMPLEMENT_CLAIMS_ONLY__PROOF_AUTHENTICATION_REQUIRED",
        "scope_id":scope_id,
        "predicate_set_sha256":digest,
        "route_count":len(normalized),
        "routes":sorted(normalized,key=lambda x:(x["admission_predicate_id"],x["route_id"])),
        "selected_cover_complete_authorized":False,
        "u_empty_authorized":False,
        "abc_closed_authorized":False,
        "d_finality_required":True,
        "structural_claim_consistency_checked":True,
        "proof_bytes_authenticated":False,
        "semantic_unsat_proof_checked":False,
        "selected_policy_adequacy_authenticated":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "proof_rule":"EVERY_REGISTERED_ADMISSION_IMPLIES_ADEQUACY__AND_NO_SCOPE_CONTEXT_EXISTS_OUTSIDE_THE_UNION_OF_REGISTERED_ADMISSIONS__THEREFORE_EVERY_SCOPE_CONTEXT_HAS_A_SOUND_BRAIN_ROUTE",
        "boundary":"ONLY_CONDITIONAL_CLAIM_CONSISTENCY__EXPLICIT_EXTERNAL_AUTHENTICATION_AND_SEMANTIC_PROOF_CHECK_NEEDED_BEFORE_SELECTED_COVER_U_EMPTY_OR_ABC_AUTHORITY",
    }
