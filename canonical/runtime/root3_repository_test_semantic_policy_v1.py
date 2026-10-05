"""Pinned semantic policy for content-bound repository-test execution."""
from __future__ import annotations
import hashlib,json,re
from collections.abc import Mapping
from typing import Any
from canonical.runtime.effect_broker_contract_v1 import verify_request

AUTHORITY_RECEIPT_SCHEMA="PROJECT_BRAIN_REPOSITORY_TEST_EXECUTION_AUTHORITY_RECEIPT_V1"
COMPOSITION_RECEIPT_SCHEMA="PROJECT_BRAIN_REPOSITORY_TEST_EXECUTION_COMPOSITION_RECEIPT_V1"
DESCRIPTOR_SCHEMA="PROJECT_BRAIN_ROOT3_CONTENT_BOUND_PROCESS_DESCRIPTOR_V1"
MEDIATOR_SCHEMA="PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2"
POLICY_ID="ROOT3_REPOSITORY_TEST_EXECUTION_V1"
PROFILE="REPOSITORY_TEST_EXECUTION"
SNAPSHOT_MODE="GIT_COMMIT_ARCHIVE_TO_PRIVATE_NAMESPACE_TMPFS"
RESOURCE="python:subprocess.run:BOUND_CHILD_CODE_EXECUTION:REPOSITORY_TEST_EXECUTION"
OPERATION="invoke_repository_test"
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
SHA1_RE=re.compile(r"^[0-9a-f]{40}$")
SUPPORTED={
 ("canonical/runtime/astra_runtime.py",1215,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/python_test_audit.py",50,"subprocess.run"),
}

class RepositoryTestSemanticError(ValueError): pass

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha(v:Any)->str: return hashlib.sha256(_canon(v)).hexdigest()

def _binding(request:Mapping[str,Any])->dict[str,str]:
    keys=("request_sha256","mission_id","capsule_head_sha256","effect_kind","resource","operation","payload_sha256")
    out={}
    for k in keys:
        v=request.get(k)
        if not isinstance(v,str) or not v or "\x00" in v: raise RepositoryTestSemanticError("REQUEST_BINDING_INVALID:"+k)
        out[k]=v
    return out

def _verify_descriptor(desc:Mapping[str,Any],mreq:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(desc,Mapping) or desc.get("schema")!=DESCRIPTOR_SCHEMA:
        raise RepositoryTestSemanticError("DESCRIPTOR_SCHEMA_INVALID")
    required={"schema","profile","snapshot_mode","mediator_request_sha256","callsite",
      "repository_head_commit_sha1","test_path","test_sha256","test_bytes",
      "interpreter_path","interpreter_sha256","interpreter_bytes","timeout_seconds",
      "material_child_commit","network","descriptor_sha256"}
    if set(desc)!=required: raise RepositoryTestSemanticError("DESCRIPTOR_FIELDS_INVALID")
    if desc.get("profile")!=PROFILE or desc.get("snapshot_mode")!=SNAPSHOT_MODE:
        raise RepositoryTestSemanticError("DESCRIPTOR_PROFILE_OR_SNAPSHOT_INVALID")
    if desc.get("material_child_commit")!="DENY" or desc.get("network")!="PRIVATE_NAMESPACE_ONLY":
        raise RepositoryTestSemanticError("DESCRIPTOR_EFFECT_BOUNDARY_INVALID")
    if not isinstance(desc.get("repository_head_commit_sha1"),str) or not SHA1_RE.fullmatch(desc["repository_head_commit_sha1"]):
        raise RepositoryTestSemanticError("DESCRIPTOR_HEAD_INVALID")
    for key in ("test_sha256","interpreter_sha256","mediator_request_sha256","descriptor_sha256"):
        if not isinstance(desc.get(key),str) or not SHA256_RE.fullmatch(desc[key]):
            raise RepositoryTestSemanticError("DESCRIPTOR_SHA_INVALID:"+key)
    core=dict(desc); claimed=core.pop("descriptor_sha256")
    if _sha(core)!=claimed: raise RepositoryTestSemanticError("DESCRIPTOR_HASH_MISMATCH")
    if desc["mediator_request_sha256"]!=mreq.get("request_sha256"):
        raise RepositoryTestSemanticError("DESCRIPTOR_MEDIATOR_REQUEST_MISMATCH")
    cs=desc.get("callsite"); mcs=mreq.get("callsite")
    if not isinstance(cs,Mapping) or set(cs)!={"module_path","lineno","process_api"}:
        raise RepositoryTestSemanticError("DESCRIPTOR_CALLSITE_INVALID")
    key=(str(cs.get("module_path")),int(cs.get("lineno",-1)),str(cs.get("process_api")))
    if key not in SUPPORTED: raise RepositoryTestSemanticError("DESCRIPTOR_CALLSITE_UNSUPPORTED")
    if not isinstance(mcs,Mapping) or (
        str(mcs.get("module_path")),int(mcs.get("lineno",-1)),str(mcs.get("process_api"))
    )!=key or mcs.get("effect_class")!="BOUND_CHILD_CODE_EXECUTION":
        raise RepositoryTestSemanticError("MEDIATOR_CALLSITE_BINDING_MISMATCH")
    if mreq.get("api")!="subprocess.run" or mreq.get("shell") is not False:
        raise RepositoryTestSemanticError("MEDIATOR_PROCESS_SHAPE_INVALID")
    if mreq.get("capture_output") is not True or mreq.get("text") is not True:
        raise RepositoryTestSemanticError("MEDIATOR_CAPTURE_MODE_INVALID")
    if mreq.get("env") is not None or mreq.get("input") is not None:
        raise RepositoryTestSemanticError("MEDIATOR_ENV_OR_INPUT_FORBIDDEN")
    return dict(desc)

def _request(request:Mapping[str,Any])->dict[str,Any]:
    req=verify_request(request)
    if req.get("effect_kind")!="EXTERNAL_MUTATION" or req.get("resource")!=RESOURCE or req.get("operation")!=OPERATION:
        raise RepositoryTestSemanticError("REQUEST_SURFACE_INVALID")
    payload=req.get("payload")
    if not isinstance(payload,Mapping) or set(payload)!={"mediator_request","descriptor"}:
        raise RepositoryTestSemanticError("PAYLOAD_FIELDS_INVALID")
    mreq=payload.get("mediator_request")
    if not isinstance(mreq,Mapping) or mreq.get("schema")!=MEDIATOR_SCHEMA:
        raise RepositoryTestSemanticError("MEDIATOR_REQUEST_INVALID")
    msha=mreq.get("request_sha256")
    if not isinstance(msha,str) or not SHA256_RE.fullmatch(msha):
        raise RepositoryTestSemanticError("MEDIATOR_REQUEST_SHA_INVALID")
    _verify_descriptor(payload.get("descriptor"),mreq)
    return req

def _exact(document:Mapping[str,Any],expected:Mapping[str,Any],label:str)->None:
    if not isinstance(document,Mapping) or dict(document)!=dict(expected):
        raise RepositoryTestSemanticError(label+"_RECEIPT_NOT_EXACT")

def verify_authority_receipt(document:Mapping[str,Any],binding:Mapping[str,Any])->dict[str,Any]:
    _request(binding["__request__"])
    expected={
      "schema":AUTHORITY_RECEIPT_SCHEMA,"policy_id":POLICY_ID,
      "effect_kind":"EXTERNAL_MUTATION","operation":OPERATION,"resource":RESOURCE,
      "profile":PROFILE,"material_child_commit":"DENY","network":"PRIVATE_NAMESPACE_ONLY",
      "scope_complete":True,"allow_implies_zero_critical_authority_violation":True,
      "independent_or_objective":True,
    }
    _exact(document,expected,"AUTHORITY")
    b=_binding(binding["__request__"])
    return {"verified":True,"role":"authority","receipt_schema":AUTHORITY_RECEIPT_SCHEMA,
      **b,"__request__":dict(binding["__request__"]),"verifier_id":"root3-repository-test-authority-v1",
      "proof_digest":_sha({"document":dict(document),"binding":b})}

def verify_composition_receipt(document:Mapping[str,Any],binding:Mapping[str,Any])->dict[str,Any]:
    _request(binding["__request__"])
    expected={
      "schema":COMPOSITION_RECEIPT_SCHEMA,"policy_id":POLICY_ID,
      "descriptor_schema":DESCRIPTOR_SCHEMA,"snapshot_mode":SNAPSHOT_MODE,
      "state_and_provenance_invariants_hold":True,"scope_complete":True,
      "independent_or_objective":True,
    }
    _exact(document,expected,"COMPOSITION")
    b=_binding(binding["__request__"])
    return {"verified":True,"role":"composition","receipt_schema":COMPOSITION_RECEIPT_SCHEMA,
      **b,"__request__":dict(binding["__request__"]),"verifier_id":"root3-repository-test-composition-v1",
      "proof_digest":_sha({"document":dict(document),"binding":b})}
