#!/usr/bin/env python3
"""Provenance-gated composite model-independent source authority binding.

Uses only independently qualified narrow primitives:
1. ROR v2 exact active domain binding for research organizations.
2. Wikidata P856 official-website host binding as a broader fallback.

The composite proves only candidate-host <-> declared source/entity identity.
It never upgrades primary-source status, relevance, factual correctness, or
evidence sufficiency.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

SCHEMA="PROJECT_BRAIN_SOURCE_AUTHORITY_COMPOSITE_V1"
_PROVENANCE_OK={"RETRIEVAL_PROVENANCE_VERIFIED","BIBLIOGRAPHIC_PROVENANCE_VERIFIED"}

def _load(name):
    path=pathlib.Path(__file__).resolve().with_name(name+".py")
    spec=importlib.util.spec_from_file_location("project_brain_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _base():
    return {
      "schema":SCHEMA,
      "authority_status":"UNVERIFIED",
      "primary_source_status":"UNVERIFIED",
      "relevance_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }

def bind_verified_candidate(candidate,provenance,timeout=20,ror_module=None,wikidata_module=None):
    candidate=dict(candidate or {})
    provenance=dict(provenance or {})
    if provenance.get("status") not in _PROVENANCE_OK:
        return {**_base(),"status":"AUTHORITY_UNRESOLVED","reason":"QUALIFIED_PROVENANCE_REQUIRED"}

    ror_module=ror_module or _load("source_authority_binding_ror")
    wikidata_module=wikidata_module or _load("source_authority_binding_wikidata")

    # Feed the provenance-final URL/host forward when available, never a
    # different unverified redirect target.
    enriched=dict(candidate)
    if provenance.get("final_url"):
        enriched["final_url"]=provenance["final_url"]
    if provenance.get("final_host"):
        enriched["final_host"]=provenance["final_host"]

    ror=ror_module.bind_candidate(enriched,timeout=timeout)
    wikidata=wikidata_module.bind_candidate(enriched,timeout=timeout)

    proofs=[]
    if ror.get("status")=="AUTHORITY_IDENTITY_VERIFIED":
        proofs.append({"route":"ROR_V2_EXACT_ACTIVE_DOMAIN","result":ror})
    if wikidata.get("status")=="AUTHORITY_IDENTITY_VERIFIED":
        proofs.append({"route":"WIKIDATA_P856_OFFICIAL_WEBSITE","result":wikidata})

    if not proofs:
        return {
          **_base(),
          "status":"AUTHORITY_UNRESOLVED",
          "reason":"NO_QUALIFIED_AUTHORITY_ROUTE_VERIFIED",
          "candidate":candidate,
          "provenance_status":provenance.get("status"),
          "route_results":{"ror":ror,"wikidata":wikidata},
        }

    return {
      **_base(),
      "status":"AUTHORITY_IDENTITY_VERIFIED",
      "authority_status":"VERIFIED",
      "candidate":candidate,
      "provenance_status":provenance.get("status"),
      "proofs":proofs,
      "verification_methods":[x["route"] for x in proofs],
      "authority_claim_scope":"PROVENANCE_VERIFIED_HOST_TO_DECLARED_ENTITY_OR_ORGANIZATION_IDENTITY_ONLY",
      "route_results":{"ror":ror,"wikidata":wikidata},
    }

def bind_frontend(frontend,timeout=20,max_candidates=12):
    if not isinstance(frontend,dict):
        raise ValueError("SOURCE_FRONTEND_OBJECT_REQUIRED")
    rows=frontend.get("provenance_verifications") or []
    if not isinstance(rows,list):
        raise ValueError("PROVENANCE_VERIFICATIONS_LIST_REQUIRED")
    results=[]
    for row in rows[:max(1,min(int(max_candidates),20))]:
        if not isinstance(row,dict):
            continue
        candidate=row.get("candidate") or {}
        provenance=row.get("verification") or {}
        results.append(bind_verified_candidate(candidate,provenance,timeout=timeout))
    verified=[x for x in results if x.get("status")=="AUTHORITY_IDENTITY_VERIFIED"]
    return {
      "schema":SCHEMA,
      "status":"AUTHORITY_BOUND_CANDIDATES_AVAILABLE" if verified else "AUTHORITY_UNRESOLVED",
      "input_provenance_row_count":len(rows),
      "verified_candidate_count":len(verified),
      "verified_candidates":verified,
      "results":results,
      "authority_claim_scope":"PROVENANCE_VERIFIED_HOST_TO_DECLARED_ENTITY_OR_ORGANIZATION_IDENTITY_ONLY",
      "primary_source_verification":"NOT_PERFORMED",
      "relevance_verification":"NOT_PERFORMED",
      "evidence_sufficiency_verification":"NOT_PERFORMED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    path=(root/str(raw or "")).resolve()
    if path==root or root not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path

def run(args,root):
    args=dict(args or {})
    inp=_safe_path(root,args.get("input_path") or args.get("frontend_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise ValueError("SOURCE_FRONTEND_INPUT_MISSING")
    frontend=json.loads(inp.read_text(encoding="utf-8"))
    result=bind_frontend(
        frontend,
        timeout=int(args.get("timeout") or 20),
        max_candidates=int(args.get("max_candidates") or 12),
    )
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=bool(
        result.get("status")=="AUTHORITY_BOUND_CANDIDATES_AVAILABLE"
        and int(result.get("verified_candidate_count") or 0)>0
    )
    return result
