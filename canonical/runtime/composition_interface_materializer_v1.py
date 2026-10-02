"""Literal frozen composition-interface materializer.

This module performs a deliberately narrow syntactic compilation of the frozen
MULTI_CAPABILITY_COMPOSITION protocol. It does not infer family mappings,
semantic equivalence, or proof credit.

Grammar used:
* task dimensions containing '+' are treated as explicit composition clauses;
  each plus-delimited literal becomes a distinct component role.
* task dimensions without '+' remain interaction-only requirements and are not
  converted into isolated component proof obligations.

Literal role names are preserved. In particular, apparent synonyms are not
merged without separate verified semantic authority.
"""
from __future__ import annotations
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_COMPOSITION_INTERFACE_MATERIALIZER_V1"
FAMILY="MULTI_CAPABILITY_COMPOSITION"
PROOF_MODE="MATCHED_INTERACTION_AND_COMPOSITION_PROTOCOL"

def _slug(text:str)->str:
    s=re.sub(r"[^A-Z0-9]+","_",text.upper()).strip("_")
    if not s:
        raise ValueError("EMPTY_ROLE_SLUG")
    return s

def _fail(*errors:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
      "claim_id":None,"interfaces":[],"interaction_requirements":[],
      "new_reality_units_consumed":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

def materialize(protocols:Mapping[str,Any], *, source_protocol_blob_sha:str)->dict[str,Any]:
    if not isinstance(protocols,Mapping):
        return _fail("PROTOCOLS_NOT_OBJECT")
    if not isinstance(source_protocol_blob_sha,str) or len(source_protocol_blob_sha)!=40:
        return _fail("SOURCE_PROTOCOL_BLOB_SHA_REQUIRED")
    rows=protocols.get("protocols")
    if not isinstance(rows,list):
        return _fail("PROTOCOL_ROWS_REQUIRED")
    found=[x for x in rows if isinstance(x,Mapping) and x.get("family")==FAMILY]
    if len(found)!=1:
        return _fail("COMPOSITION_PROTOCOL_NOT_UNIQUE")
    row=found[0]
    if row.get("proof_mode")!=PROOF_MODE:
        return _fail("COMPOSITION_PROOF_MODE_CHANGED")
    if row.get("status")!="DEFINED_RESULT_OPEN":
        return _fail("COMPOSITION_PROTOCOL_STATUS_UNEXPECTED")
    dims=row.get("task_dimensions")
    if not isinstance(dims,list) or not dims or any(not isinstance(x,str) or not x.strip() for x in dims):
        return _fail("TASK_DIMENSIONS_INVALID")
    if len(dims)!=len(set(dims)):
        return _fail("TASK_DIMENSIONS_DUPLICATE")

    role_sources:dict[str,list[str]]={}
    interactions:list[str]=[]
    for raw in dims:
        dim=raw.strip()
        if "+" not in dim:
            interactions.append(dim)
            continue
        parts=[x.strip() for x in dim.split("+")]
        if len(parts)<2 or any(not x for x in parts):
            return _fail("MALFORMED_COMPOSITION_CLAUSE:"+dim)
        for role in parts:
            role_sources.setdefault(role,[]).append(dim)

    if not role_sources:
        return _fail("NO_EXPLICIT_COMPONENT_ROLES")
    interfaces=[]
    for role in sorted(role_sources):
        slug=_slug(role)
        interfaces.append({
          "component_id":"LITERAL_ROLE::"+slug,
          "interface_id":"FROZEN_COMPOSITION_USE::"+slug,
          "role_literal":role,
          "source_dimensions":sorted(role_sources[role]),
          "required_properties":["SCOPED_ACCEPTANCE_PROOF_FOR_EXACT_ROLE::"+slug],
        })
    return {
      "schema":SCHEMA,
      "status":"MATERIALIZED_LITERAL_COMPONENT_INTERFACES__ZERO_CREDIT",
      "claim_id":"MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1",
      "source_protocol":{
        "path":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
        "git_blob_sha":source_protocol_blob_sha,
        "family":FAMILY,
        "proof_mode":PROOF_MODE,
      },
      "interfaces":interfaces,
      "interaction_requirements":interactions,
      "rules":[
        "PLUS_DELIMITED_LITERALS_ONLY__NO_SEMANTIC_COMPONENT_INFERENCE",
        "NON_PLUS_DIMENSIONS_REMAIN_INTERACTION_REQUIREMENTS",
        "NO_LITERAL_SYNONYM_MERGE",
        "NO_FAMILY_MAPPING_OR_PROOF_INHERITANCE",
        "INTERFACE_MATERIALIZATION_ALONE_GRANTS_ZERO_ACCEPTANCE_CAPABILITY_OR_FAMILY_CREDIT",
      ],
      "new_reality_units_consumed":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }
