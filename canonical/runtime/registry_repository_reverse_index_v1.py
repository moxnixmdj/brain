#!/usr/bin/env python3
"""Deterministic repository -> package reverse index from registry metadata.

The index is a retrieval bridge, not a source of capability truth. It allows a
repository candidate discovered in one ecosystem to map into package identities
from another ecosystem without depending on repository descriptions.

Completeness is admitted only when the caller supplies an independently
verified complete bounded registry snapshot receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_REGISTRY_REPOSITORY_REVERSE_INDEX_V1"

def canon_repo(value:Any)->str:
    s=" ".join(str(value or "").strip().split())
    s=re.sub(r"^git\+","",s,flags=re.I)
    s=re.sub(r"^git://","https://",s,flags=re.I)
    s=re.sub(r"\.git$","",s,flags=re.I)
    s=s.rstrip("/")
    m=re.search(r"github\.com[/:]([^/]+/[^/#]+)",s,re.I)
    if m:
        return "github:"+m.group(1).casefold()
    m=re.search(r"gitlab\.com[/:]([^/]+/[^/#]+)",s,re.I)
    if m:
        return "gitlab:"+m.group(1).casefold()
    return s.casefold()

def build(
    rows:Sequence[Mapping[str,Any]],
    *,
    snapshot_id:str,
    independently_complete:bool=False,
    completeness_receipt:str|None=None,
)->dict[str,Any]:
    sid=str(snapshot_id or "").strip()
    if not sid:
        raise ValueError("SNAPSHOT_ID_REQUIRED")
    if independently_complete and not str(completeness_receipt or "").strip():
        raise ValueError("COMPLETE_SNAPSHOT_REQUIRES_RECEIPT")

    by_repo=defaultdict(list)
    normalized=[]
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise ValueError("METADATA_ROW_MAPPING_REQUIRED")
        ecosystem=str(raw.get("ecosystem") or "").strip().casefold()
        package_id=str(raw.get("package_id") or raw.get("name") or "").strip()
        repo=canon_repo(raw.get("repository_url") or raw.get("repository"))
        if not ecosystem or not package_id:
            raise ValueError("ECOSYSTEM_AND_PACKAGE_ID_REQUIRED")
        item={
            "ecosystem":ecosystem,
            "package_id":package_id,
            "repository_canonical":repo or None,
            "source_record_id":str(raw.get("source_record_id") or "").strip() or None,
        }
        normalized.append(item)
        if repo:
            by_repo[repo].append({
                "ecosystem":ecosystem,
                "package_id":package_id,
                "source_record_id":item["source_record_id"],
            })

    index={
        repo:sorted(vals,key=lambda x:(x["ecosystem"],x["package_id"].casefold()))
        for repo,vals in sorted(by_repo.items())
    }
    payload={"snapshot_id":sid,"rows":normalized}
    digest=hashlib.sha256(
        json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
    ).hexdigest()
    return {
        "schema":SCHEMA,
        "status":"BUILT_REGISTRY_REPOSITORY_REVERSE_INDEX",
        "snapshot_id":sid,
        "metadata_row_count":len(normalized),
        "repository_identity_count":len(index),
        "repository_to_packages":index,
        "snapshot_content_sha256":digest,
        "independently_complete":bool(independently_complete),
        "completeness_receipt":str(completeness_receipt or "").strip() or None,
        "negative_lookup_authority":bool(independently_complete and completeness_receipt),
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "REVERSE_INDEX_IS_IDENTITY_BRIDGING_NOT_CAPABILITY_SUFFICIENCY",
            "NEGATIVE_LOOKUP_IS_AUTHORITATIVE_ONLY_FOR_AN_INDEPENDENTLY_COMPLETE_BOUNDED_SNAPSHOT",
            "OPEN_OR_PARTIAL_REGISTRY_SNAPSHOT_MISS_REMAINS_UNKNOWN",
            "MULTIPLE_PACKAGES_MAY_MAP_TO_ONE_REPOSITORY_AND_MUST_NOT_BE_COLLAPSED",
        ],
    }

def lookup(index:Mapping[str,Any],repository:Any)->dict[str,Any]:
    if index.get("schema")!=SCHEMA:
        raise ValueError("REVERSE_INDEX_SCHEMA_REQUIRED")
    repo=canon_repo(repository)
    rows=list((index.get("repository_to_packages") or {}).get(repo) or [])
    return {
        "repository_canonical":repo,
        "packages":rows,
        "package_count":len(rows),
        "negative_authoritative":bool(index.get("negative_lookup_authority") and not rows),
        "unknown_if_empty":not bool(index.get("negative_lookup_authority")),
    }
