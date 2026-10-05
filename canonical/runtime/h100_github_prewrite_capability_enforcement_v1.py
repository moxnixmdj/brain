"""Content-addressed prewrite capability enforcement for authenticated GitHub mutation.

This module has no GitHub/network/tool access. It compiles an exact mutation plan
into one authorized effect descriptor only when every authority field matches a
frozen content-addressed capability token. All deviations fail closed before
external effect execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_GITHUB_PREWRITE_CAPABILITY_ENFORCEMENT_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_GITHUB_PREWRITE_CAPABILITY_ENFORCEMENT_V1"

class PrewriteCapabilityError(ValueError):
    pass

def _git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _sha256(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def _load() -> tuple[dict[str,Any],dict[str,Any]]:
    pre=json.loads(PRE.read_text())
    tok_path=ROOT/pre["capability_token"]["path"]
    raw=tok_path.read_bytes()
    actual=_git_blob_sha(raw)
    expected=pre["capability_token"]["git_blob_sha"]
    if actual!=expected:
        raise PrewriteCapabilityError("CAPABILITY_TOKEN_BLOB_MISMATCH")
    token=json.loads(raw)
    if token.get("schema")!="PROJECT_BRAIN_H100_PREWRITE_CAPABILITY_TOKEN_V1":
        raise PrewriteCapabilityError("CAPABILITY_TOKEN_SCHEMA_INVALID")
    return pre,token

def desired_plan()->dict[str,Any]:
    pre,token=_load()
    auth=token["authority"]
    content=pre["desired_content_utf8"]
    raw=content.encode("utf-8")
    if len(raw)!=int(auth["desired_content_bytes"]):
        raise PrewriteCapabilityError("FROZEN_CONTENT_BYTE_COUNT_MISMATCH")
    if _sha256(raw)!=auth["desired_content_sha256"]:
        raise PrewriteCapabilityError("FROZEN_CONTENT_SHA256_MISMATCH")
    return {
        "provider":auth["provider"],
        "repository":auth["repository"],
        "branch":auth["branch"],
        "path":auth["path"],
        "operation":auth["operation"],
        "message":auth["message"],
        "content_utf8":content,
        "content_bytes":len(raw),
        "content_sha256":_sha256(raw),
        "idempotency_key":auth["idempotency_key"],
    }

def authorize(plan:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(plan,Mapping):
        raise PrewriteCapabilityError("PLAN_INVALID")
    pre,token=_load()
    expected=desired_plan()
    if set(plan)!=set(expected):
        raise PrewriteCapabilityError("PLAN_FIELDS_MISMATCH")
    mismatch=[k for k in expected if plan.get(k)!=expected[k]]
    if mismatch:
        raise PrewriteCapabilityError("PLAN_AUTHORITY_MISMATCH:"+",".join(sorted(mismatch)))
    constraints=token.get("constraints")
    if not isinstance(constraints,Mapping):
        raise PrewriteCapabilityError("CONSTRAINTS_INVALID")
    for forbidden in ("merge","delete","rename","overwrite","force"):
        if constraints.get(forbidden) is not False:
            raise PrewriteCapabilityError("FORBIDDEN_AUTHORITY_ENABLED:"+forbidden)
    if constraints.get("additional_paths")!=0:
        raise PrewriteCapabilityError("ADDITIONAL_PATH_AUTHORITY_INVALID")
    return {
        "schema":SCHEMA,
        "status":"AUTHORIZED_EXACTLY_ONE_CREATE_EFFECT",
        "capability_token_git_blob_sha":pre["capability_token"]["git_blob_sha"],
        "effect":{
            "provider":"GITHUB",
            "action":"CREATE_FILE",
            "repository_full_name":expected["repository"],
            "branch":expected["branch"],
            "path":expected["path"],
            "message":expected["message"],
            "content":expected["content_utf8"],
        },
        "audit_expectation":{
            "desired_content_bytes":expected["content_bytes"],
            "desired_content_sha256":expected["content_sha256"],
            "idempotency_key":expected["idempotency_key"],
            "maximum_mutation_calls":1,
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "external_effects_executed_by_broker":0,
    }

def classify_existing(existing_content_utf8:str|None)->dict[str,Any]:
    expected=desired_plan()
    if existing_content_utf8 is None:
        return {"status":"TARGET_ABSENT__ONE_CREATE_ALLOWED","mutation_calls_authorized":1}
    if not isinstance(existing_content_utf8,str):
        raise PrewriteCapabilityError("EXISTING_CONTENT_INVALID")
    raw=existing_content_utf8.encode("utf-8")
    if len(raw)==expected["content_bytes"] and _sha256(raw)==expected["content_sha256"] and existing_content_utf8==expected["content_utf8"]:
        return {"status":"TARGET_EXACT_MATCH__NOOP","mutation_calls_authorized":0}
    return {"status":"TARGET_PRESENT_MISMATCH__FAIL_CLOSED","mutation_calls_authorized":0}
