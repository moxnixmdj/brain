"""Producer for bounded regulatory-capital necessary-property decisions."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import regcap_necessary_property_authority_v1 as authority

SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_RESULT_V1"
CASE_SCHEMA="PROJECT_BRAIN_REGCAP_NECESSARY_PROPERTY_CASE_V1"

def compute(case:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    allowed={"schema","scope_id","concept_id","property_id"}
    if set(case)!=allowed:
        raise ValueError("CASE_FIELD_SET_INVALID")
    req={
        "schema":authority.REQUEST_SCHEMA,
        "scope_id":case.get("scope_id"),
        "concept_id":case.get("concept_id"),
        "property_id":case.get("property_id"),
    }
    out=authority.verify_property_request(req,repo_root=repo_root)
    if out.get("pass") is not True:
        raise ValueError("REGCAP_PROPERTY_NOT_AUTHENTICATED:"+str(out.get("status") or out.get("reason")))
    edge=out.get("edge_receipt")
    if not isinstance(edge,Mapping):
        raise ValueError("EDGE_RECEIPT_MISSING")
    return {
        "schema":SCHEMA,
        "status":"PROVED_ENTAILS",
        "scope_id":req["scope_id"],
        "concept_id":req["concept_id"],
        "property_id":req["property_id"],
        "relation":"ENTAILS",
        "source_authority":True,
        "semantic_truth_authority":True,
        "edge_receipt":deepcopy(dict(edge)),
        "reverse_inference_authorized":False,
        "absence_means_false":False,
        "open_world_ontology_complete":False,
        "terminal_authority":False,
    }
