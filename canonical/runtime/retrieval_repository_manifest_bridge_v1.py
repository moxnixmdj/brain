#!/usr/bin/env python3
"""Generic answer-key-blind repository -> package identity bridge.

Given a repository and ecosystem, inspect authoritative package manifests and
recover package identities. This turns repository discovery into package
registry candidates without using expected target identities.
"""
from __future__ import annotations

import base64
import json
import re
import tomllib
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v13 as v13

SCHEMA="PROJECT_BRAIN_REPOSITORY_PACKAGE_MANIFEST_BRIDGE_V1"

GEM_NAME=re.compile(r"""(?im)^\s*(?:[A-Za-z_][A-Za-z0-9_]*\.)?name\s*=\s*['"]([^'"]+)['"]""")
NUSPEC_ID=re.compile(r"(?is)<id>\s*([^<]+?)\s*</id>")
CSPROJ_PACKAGE_ID=re.compile(r"(?is)<PackageId>\s*([^<]+?)\s*</PackageId>")

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _ecosystem(x:Any)->str:
    e=_canon(x).casefold()
    aliases={"ruby":"rubygems","gem":"rubygems","node":"npm","nodejs":"npm","rust":"cargo","crates":"cargo","php":"packagist",".net":"nuget","dotnet":"nuget","java":"maven"}
    return aliases.get(e,e)

def _manifest_match(path:str,ecosystem:str)->bool:
    p=path.casefold()
    if ecosystem=="maven": return p.endswith("pom.xml")
    if ecosystem=="rubygems": return p.endswith(".gemspec")
    if ecosystem=="npm": return p.endswith("package.json")
    if ecosystem=="cargo": return p.endswith("cargo.toml")
    if ecosystem=="packagist": return p.endswith("composer.json")
    if ecosystem=="nuget": return p.endswith(".nuspec") or p.endswith(".csproj")
    return False

def extract_identities(path:str,text:str,ecosystem:str)->list[str]:
    ecosystem=_ecosystem(ecosystem)
    out=[]
    try:
        if ecosystem=="maven":
            out.extend(v13.parse_pom_coordinates(text))
        elif ecosystem=="rubygems":
            out.extend(m.group(1).strip() for m in GEM_NAME.finditer(text))
        elif ecosystem=="npm":
            obj=json.loads(text)
            if isinstance(obj,Mapping) and obj.get("name"): out.append(str(obj["name"]))
        elif ecosystem=="cargo":
            obj=tomllib.loads(text)
            package=obj.get("package") if isinstance(obj,Mapping) else None
            if isinstance(package,Mapping) and package.get("name"): out.append(str(package["name"]))
        elif ecosystem=="packagist":
            obj=json.loads(text)
            if isinstance(obj,Mapping) and obj.get("name"): out.append(str(obj["name"]))
        elif ecosystem=="nuget":
            if path.casefold().endswith(".nuspec"):
                out.extend(m.group(1).strip() for m in NUSPEC_ID.finditer(text))
            else:
                out.extend(m.group(1).strip() for m in CSPROJ_PACKAGE_ID.finditer(text))
    except Exception:
        return []
    seen=set();rows=[]
    for raw in out:
        s=_canon(raw)
        if s and s.casefold() not in seen:
            seen.add(s.casefold());rows.append(s)
    return rows

def _blob_text(repo:str,sha:str,*,timeout:float)->str:
    quoted=urllib.parse.quote(repo,safe="/")
    obj=v13._github_json(f"https://api.github.com/repos/{quoted}/git/blobs/{sha}",timeout=timeout)
    raw=str(obj.get("content") or "").replace("\n","")
    if str(obj.get("encoding") or "").lower()!="base64" or not raw:
        return ""
    try:
        return base64.b64decode(raw).decode("utf-8","replace")
    except Exception:
        return ""

def repository_identities(
    repo:str,
    ecosystem:str,
    *,
    timeout:float=20.0,
    max_files:int=32,
)->dict[str,Any]:
    ecosystem=_ecosystem(ecosystem)
    if ecosystem not in {"maven","rubygems","npm","cargo","packagist","nuget"}:
        raise ValueError("UNSUPPORTED_ECOSYSTEM:"+ecosystem)
    quoted=urllib.parse.quote(repo,safe="/")
    info=v13._github_json(f"https://api.github.com/repos/{quoted}",timeout=timeout)
    branch=str(info.get("default_branch") or "main")
    tree=v13._github_json(
        f"https://api.github.com/repos/{quoted}/git/trees/{urllib.parse.quote(branch,safe='')}?recursive=1",
        timeout=timeout,
    )
    files=[
        x for x in (tree.get("tree") or [])
        if isinstance(x,Mapping) and x.get("type")=="blob"
        and _manifest_match(str(x.get("path") or ""),ecosystem)
    ]
    files.sort(key=lambda x:(str(x.get("path") or "").count("/"),len(str(x.get("path") or "")),str(x.get("path") or "")))
    identities=[];seen=set();traces=[]
    for row in files[:max_files]:
        path=str(row.get("path") or "");sha=str(row.get("sha") or "")
        if not sha: continue
        text=_blob_text(repo,sha,timeout=timeout)
        got=extract_identities(path,text,ecosystem) if text else []
        traces.append({"path":path,"blob_sha":sha,"identities":got})
        for item in got:
            key=item.casefold()
            if key not in seen:
                seen.add(key);identities.append(item)
    return {
        "schema":SCHEMA,
        "status":"REPOSITORY_MANIFEST_IDENTITY_EXTRACTION_COMPLETE",
        "repository":repo,
        "ecosystem":ecosystem,
        "default_branch":branch,
        "manifest_file_count":len(files),
        "inspected_manifest_count":min(len(files),max_files),
        "identities":identities,
        "identity_count":len(identities),
        "traces":traces,
        "answer_key_identity_used":False,
        "candidate_authority":"CANDIDATE_ONLY",
        "nonexistence_claim_authorized":False,
        "incremental_spend_usd":0
    }
