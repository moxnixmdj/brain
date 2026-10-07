"""Symbolic positive-admission selected-route router.

Selection-only successor candidate to the exact-context-digest router.

Each route carries a callable positive admission predicate over an arbitrary
context mapping. The predicate must return an attestation bound to the exact
canonical context digest, cell id, and predicate id. The router selects only
literal-positive matches and otherwise returns the explicit residual escape.

This module does NOT authenticate files, prove admission soundness, prove cover
completeness, execute the route, or grant credit. A production entrypoint must
content-address predicate/route/certificate bytes and the complement UNSAT
receipt before any ABC credit.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_SYMBOLIC_POSITIVE_ADMISSION_ROUTE_ROUTER_V1"

class PredicateRouterError(ValueError):
    pass

def _canon(x:Any)->str:
    try:
        return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError) as exc:
        raise PredicateRouterError("CONTEXT_NOT_CANONICAL_JSON") from exc

def context_sha256(context:Mapping[str,Any])->str:
    if not isinstance(context,Mapping):
        raise PredicateRouterError("CONTEXT_MAPPING_REQUIRED")
    return "sha256:"+sha256(_canon(dict(context)).encode("utf-8")).hexdigest()

def _hex40(value:str,label:str)->None:
    if not isinstance(value,str) or len(value)!=40 or any(c not in "0123456789abcdef" for c in value):
        raise PredicateRouterError(label+"_INVALID")

@dataclass(frozen=True)
class PredicateRoute:
    cell_id:str
    route_id:str
    admission_predicate_id:str
    admission_predicate_blob_sha:str
    route_blob_sha:str
    adequacy_certificate_blob_sha:str
    admission_soundness_receipt_blob_sha:str
    admission_soundness_verified:bool
    predicate:Callable[[Mapping[str,Any]],Mapping[str,Any]]

def _validate_route(r:PredicateRoute)->None:
    for label,value in (
        ("CELL_ID",r.cell_id),("ROUTE_ID",r.route_id),("ADMISSION_PREDICATE_ID",r.admission_predicate_id)
    ):
        if not isinstance(value,str) or not value.strip():
            raise PredicateRouterError(label+"_REQUIRED")
    for label,value in (
        ("ADMISSION_PREDICATE_BLOB_SHA",r.admission_predicate_blob_sha),
        ("ROUTE_BLOB_SHA",r.route_blob_sha),
        ("ADEQUACY_CERTIFICATE_BLOB_SHA",r.adequacy_certificate_blob_sha),
        ("ADMISSION_SOUNDNESS_RECEIPT_BLOB_SHA",r.admission_soundness_receipt_blob_sha),
    ):
        _hex40(value,label)
    if r.admission_soundness_verified is not True:
        raise PredicateRouterError("ADMISSION_SOUNDNESS_NOT_VERIFIED:"+r.route_id)
    if not callable(r.predicate):
        raise PredicateRouterError("ADMISSION_PREDICATE_NOT_CALLABLE:"+r.route_id)

def select(context:Mapping[str,Any], routes:Sequence[PredicateRoute])->dict[str,Any]:
    digest=context_sha256(context)
    if not isinstance(routes,Sequence) or isinstance(routes,(str,bytes)) or not routes:
        raise PredicateRouterError("ROUTES_REQUIRED")

    seen=set()
    matches=[]
    evaluated=[]
    for r in routes:
        if not isinstance(r,PredicateRoute):
            raise PredicateRouterError("ROUTE_TYPE_INVALID")
        _validate_route(r)
        identity=(r.cell_id,r.route_id,r.admission_predicate_id,r.admission_predicate_blob_sha,
                  r.route_blob_sha,r.adequacy_certificate_blob_sha,r.admission_soundness_receipt_blob_sha)
        if identity in seen:
            raise PredicateRouterError("DUPLICATE_ROUTE_IDENTITY")
        seen.add(identity)

        att=r.predicate(dict(context))
        if not isinstance(att,Mapping):
            raise PredicateRouterError("PREDICATE_ATTESTATION_NOT_MAPPING:"+r.route_id)
        admitted=att.get("admitted")
        if type(admitted) is not bool:
            raise PredicateRouterError("PREDICATE_ADMISSION_NOT_LITERAL_BOOL:"+r.route_id)
        if att.get("cell_id")!=r.cell_id:
            raise PredicateRouterError("PREDICATE_CELL_ID_MISMATCH:"+r.route_id)
        if att.get("admission_predicate_id")!=r.admission_predicate_id:
            raise PredicateRouterError("PREDICATE_ID_MISMATCH:"+r.route_id)
        if att.get("context_sha256")!=digest:
            raise PredicateRouterError("PREDICATE_CONTEXT_DIGEST_MISMATCH:"+r.route_id)
        evaluated.append({"route_id":r.route_id,"cell_id":r.cell_id,"admitted":admitted})
        if admitted:
            matches.append(r)

    if not matches:
        return {
            "schema":SCHEMA,
            "status":"RESIDUAL_ESCAPE__NO_SOUND_ADMISSION_PREDICATE_MATCHED",
            "pass":False,
            "context_sha256":digest,
            "evaluated":evaluated,
            "residual_escape":True,
            "selected_route":None,
            "selected_cover_complete_claimed":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }

    matches.sort(key=lambda r:(
        r.admission_soundness_receipt_blob_sha,
        r.adequacy_certificate_blob_sha,
        r.admission_predicate_blob_sha,
        r.route_blob_sha,
        r.cell_id,
        r.route_id,
    ))
    r=matches[0]
    return {
        "schema":SCHEMA,
        "status":"PASS__SYMBOLIC_CERTIFIED_ROUTE_SELECTED",
        "pass":True,
        "context_sha256":digest,
        "evaluated":evaluated,
        "residual_escape":False,
        "selected_route":{
            "cell_id":r.cell_id,
            "route_id":r.route_id,
            "admission_predicate_id":r.admission_predicate_id,
            "admission_predicate_blob_sha":r.admission_predicate_blob_sha,
            "route_blob_sha":r.route_blob_sha,
            "adequacy_certificate_blob_sha":r.adequacy_certificate_blob_sha,
            "admission_soundness_receipt_blob_sha":r.admission_soundness_receipt_blob_sha,
        },
        "selected_cover_complete_claimed":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"SELECTION_ONLY__PRODUCTION_MUST_AUTHENTICATE_EXACT_BYTES_AND_COVERAGE_COMPLEMENT_PROOF",
    }
