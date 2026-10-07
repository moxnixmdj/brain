from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SOURCE_AUTHORITY_COVERAGE_GATE_V1"

def _fail(errors):
    return {
      "schema":SCHEMA,
      "status":"FAIL_CLOSED",
      "pass":False,
      "errors":sorted(set(errors)),
      "semantic_completeness_self_certified":False,
      "authority_discovery_self_certified":False,
      "terminal_credit_delta":0,
    }

def verify(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return _fail(["BUNDLE_NOT_OBJECT"])
    errors=[]
    sources=bundle.get("sources")
    required_dims=bundle.get("required_dimension_ids")
    dimensions=bundle.get("dimensions")
    required_conventions=bundle.get("required_convention_ids")
    conventions=bundle.get("conventions")

    if not isinstance(sources,list) or not sources:
        errors.append("SOURCES_REQUIRED"); sources=[]
    source_ids=set()
    for i,row in enumerate(sources):
        if not isinstance(row,Mapping):
            errors.append(f"SOURCE_NOT_OBJECT:{i}"); continue
        sid=str(row.get("source_id") or "").strip()
        if not sid:
            errors.append(f"SOURCE_ID_MISSING:{i}"); continue
        if sid in source_ids:
            errors.append("SOURCE_ID_DUPLICATE:"+sid)
        source_ids.add(sid)
        if row.get("required") is True:
            if row.get("parsed") is not True:
                errors.append("REQUIRED_SOURCE_NOT_PARSED:"+sid)
            if not str(row.get("content_sha256") or "").strip():
                errors.append("REQUIRED_SOURCE_HASH_MISSING:"+sid)
            if not str(row.get("parser_receipt") or "").strip():
                errors.append("REQUIRED_SOURCE_PARSER_RECEIPT_MISSING:"+sid)
        rank=row.get("authority_rank")
        if not isinstance(rank,int) or isinstance(rank,bool) or rank < 0:
            errors.append("AUTHORITY_RANK_INVALID:"+sid)

    if not isinstance(required_dims,list) or not required_dims or any(not isinstance(x,str) or not x.strip() for x in required_dims):
        errors.append("REQUIRED_DIMENSION_IDS_INVALID"); required_dims=[]
    required_dim_set=set(required_dims)
    if len(required_dim_set)!=len(required_dims):
        errors.append("REQUIRED_DIMENSION_IDS_DUPLICATE")

    if not isinstance(dimensions,list):
        errors.append("DIMENSIONS_INVALID"); dimensions=[]
    dim_ids=set()
    for i,row in enumerate(dimensions):
        if not isinstance(row,Mapping):
            errors.append(f"DIMENSION_NOT_OBJECT:{i}"); continue
        did=str(row.get("dimension_id") or "").strip()
        if not did:
            errors.append(f"DIMENSION_ID_MISSING:{i}"); continue
        if did in dim_ids:
            errors.append("DIMENSION_ID_DUPLICATE:"+did)
        dim_ids.add(did)
        raw=row.get("source_ids")
        if not isinstance(raw,list) or not raw:
            errors.append("DIMENSION_SOURCE_BINDING_MISSING:"+did); continue
        ids={str(x).strip() for x in raw if str(x).strip()}
        if not ids:
            errors.append("DIMENSION_SOURCE_BINDING_MISSING:"+did)
        missing=ids-source_ids
        if missing:
            errors.extend("DIMENSION_SOURCE_UNKNOWN:"+did+":"+x for x in sorted(missing))
        if not str(row.get("coverage_receipt") or "").strip():
            errors.append("DIMENSION_COVERAGE_RECEIPT_MISSING:"+did)

    if dim_ids!=required_dim_set:
        for x in sorted(required_dim_set-dim_ids): errors.append("REQUIRED_DIMENSION_UNCOVERED:"+x)
        for x in sorted(dim_ids-required_dim_set): errors.append("UNDECLARED_DIMENSION:"+x)

    if required_conventions is None:
        required_conventions=[]
    if not isinstance(required_conventions,list) or any(not isinstance(x,str) or not x.strip() for x in required_conventions):
        errors.append("REQUIRED_CONVENTION_IDS_INVALID"); required_conventions=[]
    required_conv_set=set(required_conventions)
    if len(required_conv_set)!=len(required_conventions):
        errors.append("REQUIRED_CONVENTION_IDS_DUPLICATE")

    if not isinstance(conventions,list):
        errors.append("CONVENTIONS_INVALID"); conventions=[]
    conv_ids=set()
    for i,row in enumerate(conventions):
        if not isinstance(row,Mapping):
            errors.append(f"CONVENTION_NOT_OBJECT:{i}"); continue
        cid=str(row.get("convention_id") or "").strip()
        if not cid:
            errors.append(f"CONVENTION_ID_MISSING:{i}"); continue
        if cid in conv_ids: errors.append("CONVENTION_ID_DUPLICATE:"+cid)
        conv_ids.add(cid)
        sid=str(row.get("source_id") or "").strip()
        if sid not in source_ids: errors.append("CONVENTION_SOURCE_UNKNOWN:"+cid)
        if not str(row.get("binding_receipt") or "").strip():
            errors.append("CONVENTION_BINDING_RECEIPT_MISSING:"+cid)

    if conv_ids!=required_conv_set:
        for x in sorted(required_conv_set-conv_ids): errors.append("REQUIRED_CONVENTION_UNBOUND:"+x)
        for x in sorted(conv_ids-required_conv_set): errors.append("UNDECLARED_CONVENTION:"+x)

    if errors:
        return _fail(errors)
    return {
      "schema":SCHEMA,
      "status":"PASS__DECLARED_SOURCE_INGESTION_DIMENSION_COVERAGE_AND_CONVENTION_BINDING_COMPLETE",
      "pass":True,
      "errors":[],
      "source_count":len(source_ids),
      "required_dimension_count":len(required_dim_set),
      "required_convention_count":len(required_conv_set),
      "semantic_completeness_self_certified":False,
      "authority_discovery_self_certified":False,
      "remaining_obligations":[
        "PROVE_THE_DECLARED_SOURCE_MANIFEST_CONTAINS_ALL_LOAD_BEARING_TASK_AUTHORITY",
        "PROVE_THE_DECLARED_REQUIRED_DIMENSION_SET_IS_SEMANTICALLY_COMPLETE",
        "PROVE_BOUND_SOURCE_EVIDENCE_SUPPORTS_THE_SELECTED_POLICY_OR_DELIVERABLE"
      ],
      "terminal_credit_delta":0,
    }
