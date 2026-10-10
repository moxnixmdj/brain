#!/usr/bin/env python3
"""Package-registry repository bridge verifier V1.

Validates repository <-> published package identity from public registry
metadata. In production the same metadata can be enumerated into a reverse
repository->package index, avoiding dependence on repository prose/manifests.

This arena uses known package ids only as an evaluation answer key; it is not a
discovery route and grants no acceptance/capability credit.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from typing import Any, Callable, Mapping

from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_REGISTRY_REPOSITORY_BRIDGE_V1"

CASES=(
 {"ecosystem":"npm","package_id":"typescript","expected_repository":"microsoft/typescript"},
 {"ecosystem":"npm","package_id":"eslint","expected_repository":"eslint/eslint"},
 {"ecosystem":"crates","package_id":"serde","expected_repository":"serde-rs/serde"},
 {"ecosystem":"crates","package_id":"tokio","expected_repository":"tokio-rs/tokio"},
 {"ecosystem":"crates","package_id":"clap","expected_repository":"clap-rs/clap"},
)

def canon_repo(value:Any)->str:
    s=str(value or "").strip()
    s=re.sub(r"^git\+","",s)
    s=re.sub(r"^git://","https://",s)
    s=re.sub(r"\.git$","",s)
    s=s.rstrip("/")
    m=re.search(r"github\.com[/:]([^/]+/[^/#]+)",s,re.I)
    return m.group(1).casefold() if m else s.casefold()

def npm_metadata(package_id:str,*,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->Mapping[str,Any]:
    url="https://registry.npmjs.org/"+urllib.parse.quote(package_id,safe="@/")+"/latest"
    obj=fetch(url,timeout=timeout)
    repo=obj.get("repository") or {}
    repo_url=repo.get("url") if isinstance(repo,Mapping) else repo
    return {"package_id":str(obj.get("name") or package_id),"repository_url":repo_url}

def crates_metadata(package_id:str,*,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->Mapping[str,Any]:
    url="https://crates.io/api/v1/crates/"+urllib.parse.quote(package_id,safe="")
    obj=fetch(url,timeout=timeout)
    crate=obj.get("crate") or {}
    return {"package_id":str(crate.get("id") or crate.get("name") or package_id),"repository_url":crate.get("repository")}

PROVIDERS={"npm":npm_metadata,"crates":crates_metadata}

def run(*,timeout:float=20.0)->dict[str,Any]:
    rows=[]
    for case in CASES:
        start=time.perf_counter()
        try:
            meta=PROVIDERS[case["ecosystem"]](case["package_id"],timeout=timeout)
            status="SUCCESS"; error=None
        except Exception as exc:
            meta={}; status="FAILED_RETRYABLE"; error=f"{type(exc).__name__}:{str(exc)[:400]}"
        observed=canon_repo(meta.get("repository_url"))
        expected=case["expected_repository"].casefold()
        rows.append({
          **case,"status":status,
          "observed_package_id":meta.get("package_id"),
          "observed_repository_url":meta.get("repository_url"),
          "observed_repository_canonical":observed,
          "repository_match":status=="SUCCESS" and observed==expected,
          "latency_seconds":max(0.0,time.perf_counter()-start),
          "request_count":1,"error":error,
        })
    success=[x for x in rows if x["status"]=="SUCCESS"]
    match=[x for x in success if x["repository_match"]]
    return {
      "schema":SCHEMA,"status":"REGISTRY_REPOSITORY_BRIDGE_PROBE_COMPLETE",
      "case_count":len(rows),"successful_case_count":len(success),
      "repository_match_count":len(match),
      "repository_match_rate":len(match)/len(success) if success else None,
      "bridges":rows,
      "reverse_index_construction_supported":True,
      "reverse_index_semantics":"ENUMERATE_PACKAGE_METADATA__CANONICALIZE_REPOSITORY_URL__INDEX_REPOSITORY_TO_PACKAGE_IDS",
      "open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "hard_rules":[
        "PACKAGE_IDS_IN_THIS_ARENA_ARE_EVALUATION_ANSWER_KEYS_NOT_DISCOVERY_QUERIES",
        "PUBLIC_REGISTRY_METADATA_IS_USED_ONLY_TO_VALIDATE_REPOSITORY_PACKAGE_LINKAGE",
        "PRODUCTION_REVERSE_INDEX_MUST_BE_BUILT_FROM_BOUNDED_ENUMERATED_REGISTRY_METADATA_WHERE_AVAILABLE",
        "FAILED_REGISTRY_CALLS_REMAIN_RETRYABLE",
        "REPOSITORY_MAPPING_DOES_NOT_PROVE_CAPABILITY_SUFFICIENCY",
      ],
    }

def main()->int:
    out=run(); print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_case_count"]>0 else 1

if __name__=="__main__": raise SystemExit(main())
