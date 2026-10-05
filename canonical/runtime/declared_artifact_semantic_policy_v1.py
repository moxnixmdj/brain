"""Pinned semantic verifiers for declared artifact finalization.

These verifiers authorize only the exact FINAL_OUTPUT replace surface under the
reserved artifact root. They do not execute writes and they do not judge
artifact content quality.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from canonical.runtime.effect_broker_contract_v1 import verify_request

AUTHORITY_RECEIPT_SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_AUTHORITY_RECEIPT_V1"
COMPOSITION_RECEIPT_SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_COMPOSITION_RECEIPT_V1"
DESCRIPTOR_SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_DESCRIPTOR_V1"
POLICY_ID="DECLARED_ARTIFACT_FINAL_OUTPUT_V1"
ARTIFACT_ROOT="canonical/astra_runtime/artifacts"
MAX_ARTIFACT_BYTES=536_870_912
PATH_RE=re.compile(r"^canonical/astra_runtime/artifacts/[A-Za-z0-9][A-Za-z0-9_.-]{0,239}$")
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

class DeclaredArtifactSemanticError(ValueError):
    pass

def _canon(v: Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _digest(document: Mapping[str,Any], binding: Mapping[str,Any])->str:
    core={"document":dict(document),"binding":{k:v for k,v in binding.items() if k!="__request__"}}
    return hashlib.sha256(_canon(core)).hexdigest()

def _request(binding: Mapping[str,Any])->dict[str,Any]:
    req=binding.get("__request__")
    if not isinstance(req,Mapping):
        raise DeclaredArtifactSemanticError("FULL_REQUEST_CONTEXT_REQUIRED")
    req=dict(req)
    verify_request(req)
    if req.get("effect_kind")!="FINAL_OUTPUT":
        raise DeclaredArtifactSemanticError("EFFECT_KIND_NOT_FINAL_OUTPUT")
    if req.get("operation")!="replace":
        raise DeclaredArtifactSemanticError("OPERATION_NOT_REPLACE")
    payload=req.get("payload")
    if not isinstance(payload,Mapping):
        raise DeclaredArtifactSemanticError("DESCRIPTOR_NOT_OBJECT")
    expected={
        "schema","destination_path","artifact_sha256","artifact_bytes",
        "expected_pre_sha256","content_type","producer_sha256","toolchain_sha256",
    }
    if set(payload)!=expected or payload.get("schema")!=DESCRIPTOR_SCHEMA:
        raise DeclaredArtifactSemanticError("DESCRIPTOR_FIELDS_OR_SCHEMA_INVALID")
    path=payload.get("destination_path")
    if not isinstance(path,str) or PATH_RE.fullmatch(path) is None:
        raise DeclaredArtifactSemanticError("DESTINATION_PATH_NOT_ALLOWED")
    if req.get("resource")!="artifact:"+path:
        raise DeclaredArtifactSemanticError("RESOURCE_DESCRIPTOR_MISMATCH")
    artifact_sha=payload.get("artifact_sha256")
    producer=payload.get("producer_sha256")
    toolchain=payload.get("toolchain_sha256")
    if any(not isinstance(x,str) or SHA256_RE.fullmatch(x) is None for x in (artifact_sha,producer,toolchain)):
        raise DeclaredArtifactSemanticError("DESCRIPTOR_SHA256_INVALID")
    n=payload.get("artifact_bytes")
    if not isinstance(n,int) or isinstance(n,bool) or not (1<=n<=MAX_ARTIFACT_BYTES):
        raise DeclaredArtifactSemanticError("ARTIFACT_BYTES_INVALID")
    pre=payload.get("expected_pre_sha256")
    if pre!="ABSENT" and (not isinstance(pre,str) or SHA256_RE.fullmatch(pre) is None):
        raise DeclaredArtifactSemanticError("EXPECTED_PRESTATE_INVALID")
    ctype=payload.get("content_type")
    if not isinstance(ctype,str) or not ctype.strip() or len(ctype)>256 or "\x00" in ctype:
        raise DeclaredArtifactSemanticError("CONTENT_TYPE_INVALID")
    return req

def _exact_doc(document: Mapping[str,Any], expected: Mapping[str,Any], label:str)->None:
    if not isinstance(document,Mapping) or dict(document)!=dict(expected):
        raise DeclaredArtifactSemanticError(label+"_RECEIPT_NOT_EXACT")

def verify_authority_receipt(document: Mapping[str,Any], binding: Mapping[str,Any])->dict[str,Any]:
    _request(binding)
    expected={
        "schema":AUTHORITY_RECEIPT_SCHEMA,
        "policy_id":POLICY_ID,
        "effect_kind":"FINAL_OUTPUT",
        "operation":"replace",
        "artifact_root":ARTIFACT_ROOT,
        "max_artifact_bytes":MAX_ARTIFACT_BYTES,
        "scope_complete":True,
        "allow_implies_zero_critical_authority_violation":True,
        "independent_or_objective":True,
    }
    _exact_doc(document,expected,"AUTHORITY")
    return {
        "verified":True,
        "role":"authority",
        "receipt_schema":AUTHORITY_RECEIPT_SCHEMA,
        **{k:v for k,v in binding.items() if k!="__request__"},
        "__request__":dict(binding["__request__"]),
        "verifier_id":"declared-artifact-authority-v1",
        "proof_digest":_digest(document,binding),
    }

def verify_composition_receipt(document: Mapping[str,Any], binding: Mapping[str,Any])->dict[str,Any]:
    _request(binding)
    expected={
        "schema":COMPOSITION_RECEIPT_SCHEMA,
        "policy_id":POLICY_ID,
        "descriptor_schema":DESCRIPTOR_SCHEMA,
        "state_and_provenance_invariants_hold":True,
        "scope_complete":True,
        "independent_or_objective":True,
    }
    _exact_doc(document,expected,"COMPOSITION")
    return {
        "verified":True,
        "role":"composition",
        "receipt_schema":COMPOSITION_RECEIPT_SCHEMA,
        **{k:v for k,v in binding.items() if k!="__request__"},
        "__request__":dict(binding["__request__"]),
        "verifier_id":"declared-artifact-composition-v1",
        "proof_digest":_digest(document,binding),
    }
