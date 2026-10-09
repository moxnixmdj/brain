"""Minimal physical D-final front door for pure stdlib bound capabilities.

This path deliberately excludes the unified fabric, Astra, package acquisition,
world I/O, and arbitrary effect channels. It resolves one exact current D-final
row, stages only the certificate-bound material closure plus typed JSON inputs,
and executes the sealed stdlib capability inside the zero-ambient namespace.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import tempfile
from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch
from canonical.runtime import zero_ambient_namespace_launcher_v1 as zero_ambient

SCHEMA="PROJECT_BRAIN_D_FINAL_PURE_STDLIB_FRONTDOOR_V1"
PROFILE="ZERO_AMBIENT_PURE_STDLIB_V1"
DISPATCH_KIND="D_FINAL_STDLIB_BOUND_EXECUTOR_V1"
CONTRACT_SCHEMA="PROJECT_BRAIN_D_CAPABILITY_CONTRACT_V2"
DYNAMIC_INPUT_SCHEMA="PROJECT_BRAIN_D_DYNAMIC_INPUT_POLICY_V1"
REGISTRY_SCHEMA="PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1"
DEFAULT_REGISTRY="canonical/governance/D_FINALITY_CERTIFICATE_REGISTRY_V1.json"
CHILD_PATH="canonical/runtime/d_final_pure_stdlib_child_v1.py"
EPOCH_PATH="canonical/runtime/d_finality_execution_epoch_v1.py"
EXECUTOR_PATH="canonical/runtime/d_final_stdlib_bound_executor_v1.py"
BOUND_REGISTRY_PATH="canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
VERIFIER_PATH="canonical/runtime/bound_capability_execution_verifier_v1.py"
PLANNER_PATH="canonical/runtime/capability_planner.py"
TRACE_PATH="canonical/runtime/capability_execution_trace_capsule_v1.py"
STATE_CAPSULE_PATH="canonical/runtime/composition_state_capsule_v1.py"
CORE_MATERIALS=(
    CHILD_PATH,
    EPOCH_PATH,
    EXECUTOR_PATH,
    BOUND_REGISTRY_PATH,
    VERIFIER_PATH,
    PLANNER_PATH,
    TRACE_PATH,
    STATE_CAPSULE_PATH,
)


class PureStdlibDFinalError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",",":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except Exception as exc:
        raise PureStdlibDFinalError("NON_CANONICAL_JSON") from exc


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _write_json(path: pathlib.Path, value: Mapping[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(_canon(value))
    path.chmod(0o644)


def _safe_canonical(root: pathlib.Path, raw: Any, label: str) -> pathlib.Path:
    rel=str(raw or "").strip().replace("\\","/")
    p=pathlib.PurePosixPath(rel)
    if not rel or p.is_absolute() or ".." in p.parts or not rel.startswith("canonical/"):
        raise PureStdlibDFinalError(label+"_PATH_INVALID")
    full=(root/pathlib.Path(*p.parts)).resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise PureStdlibDFinalError(label+"_PATH_ESCAPES_ROOT") from exc
    if not full.is_file():
        raise PureStdlibDFinalError(label+"_FILE_MISSING:"+rel)
    return full


def _load_json(path: pathlib.Path, label: str) -> dict[str,Any]:
    try:
        doc=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PureStdlibDFinalError(label+"_JSON_INVALID") from exc
    if not isinstance(doc,Mapping):
        raise PureStdlibDFinalError(label+"_NOT_OBJECT")
    return dict(doc)


def _hex(value: Any, length: int, label: str) -> str:
    text=str(value or "").lower()
    if len(text)!=length or any(ch not in "0123456789abcdef" for ch in text):
        raise PureStdlibDFinalError(label+"_INVALID")
    return text


def _dynamic_policy(row: Mapping[str,Any]) -> dict[str,Any]:
    raw=row.get("dynamic_input_policy")
    if not isinstance(raw,Mapping) or raw.get("schema")!=DYNAMIC_INPUT_SCHEMA:
        raise PureStdlibDFinalError("DYNAMIC_INPUT_POLICY_INVALID")
    prefixes=raw.get("allowed_prefixes")
    extensions=raw.get("allowed_extensions")
    if not isinstance(prefixes,list) or not isinstance(extensions,list):
        raise PureStdlibDFinalError("DYNAMIC_INPUT_POLICY_LISTS_INVALID")
    clean_prefixes=[]
    for raw_prefix in prefixes:
        prefix=str(raw_prefix or "").strip().replace("\\","/")
        p=pathlib.PurePosixPath(prefix)
        if not prefix or p.is_absolute() or ".." in p.parts or not prefix.endswith("/"):
            raise PureStdlibDFinalError("DYNAMIC_INPUT_PREFIX_INVALID")
        clean_prefixes.append(prefix)
    clean_extensions=[]
    for raw_extension in extensions:
        extension=str(raw_extension or "").strip().lower()
        if not extension.startswith(".") or "/" in extension or "\\" in extension:
            raise PureStdlibDFinalError("DYNAMIC_INPUT_EXTENSION_INVALID")
        clean_extensions.append(extension)
    max_files=int(raw.get("max_files",0))
    max_total=int(raw.get("max_total_bytes",0))
    max_file=int(raw.get("max_file_bytes",0))
    if not (0<=max_files<=64):
        raise PureStdlibDFinalError("DYNAMIC_INPUT_MAX_FILES_INVALID")
    if not (0<=max_total<=8_000_000):
        raise PureStdlibDFinalError("DYNAMIC_INPUT_MAX_TOTAL_INVALID")
    if not (0<=max_file<=4_000_000):
        raise PureStdlibDFinalError("DYNAMIC_INPUT_MAX_FILE_INVALID")
    return {
      "schema":DYNAMIC_INPUT_SCHEMA,
      "allowed_prefixes":sorted(set(clean_prefixes)),
      "allowed_extensions":sorted(set(clean_extensions)),
      "max_files":max_files,
      "max_total_bytes":max_total,
      "max_file_bytes":max_file,
      "encoding":"CANONICAL_JSON_UTF8",
    }


def _request_contract(row: Mapping[str,Any]) -> dict[str,Any]:
    raw_keys=row.get("allowed_request_keys")
    raw_paths=row.get("request_path_fields")
    if not isinstance(raw_keys,list) or not raw_keys:
        raise PureStdlibDFinalError("ALLOWED_REQUEST_KEYS_INVALID")
    if not isinstance(raw_paths,list):
        raise PureStdlibDFinalError("REQUEST_PATH_FIELDS_INVALID")
    keys=[str(x or "").strip() for x in raw_keys]
    paths=[str(x or "").strip() for x in raw_paths]
    if any(not x for x in keys) or len(keys)!=len(set(keys)):
        raise PureStdlibDFinalError("ALLOWED_REQUEST_KEYS_INVALID")
    if any(not x for x in paths) or len(paths)!=len(set(paths)):
        raise PureStdlibDFinalError("REQUEST_PATH_FIELDS_INVALID")
    if not set(paths).issubset(set(keys)):
        raise PureStdlibDFinalError("REQUEST_PATH_FIELD_NOT_ALLOWED")
    return {
      "allowed_request_keys":sorted(keys),
      "request_path_fields":sorted(paths),
    }


def capability_contract(capability_id: str, row: Mapping[str,Any]) -> dict[str,Any]:
    adapter_blob=_hex(row.get("adapter_git_blob_sha"),40,"ADAPTER_GIT_BLOB_SHA")
    registry_blob=_hex(
        row.get("bound_registry_git_blob_sha"),40,"BOUND_REGISTRY_GIT_BLOB_SHA"
    )
    return {
      "schema":CONTRACT_SCHEMA,
      "capability_id":str(capability_id),
      "physical_profile":PROFILE,
      "physical_dispatch_kind":DISPATCH_KIND,
      "adapter_git_blob_sha":adapter_blob,
      "bound_registry_git_blob_sha":registry_blob,
      "dynamic_input_policy":_dynamic_policy(row),
      "request_contract":_request_contract(row),
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":[],
    }


def _resolve(
    capability_id: str,
    *,
    root: pathlib.Path,
    registry_path: str=DEFAULT_REGISTRY,
) -> dict[str,Any]:
    cid=str(capability_id or "").strip()
    if not cid.startswith("bound:") or not cid[6:]:
        raise PureStdlibDFinalError("BOUND_CAPABILITY_ID_REQUIRED")
    reg_path=_safe_canonical(root,registry_path,"D_REGISTRY")
    registry=_load_json(reg_path,"D_REGISTRY")
    if registry.get("schema")!=REGISTRY_SCHEMA:
        raise PureStdlibDFinalError("D_REGISTRY_SCHEMA_INVALID")
    if registry.get("status")!="ACTIVE_FAIL_CLOSED":
        raise PureStdlibDFinalError("D_REGISTRY_NOT_ACTIVE")
    if registry.get("default")!="NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW":
        raise PureStdlibDFinalError("D_REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    rows=registry.get("rows")
    if not isinstance(rows,list):
        raise PureStdlibDFinalError("D_REGISTRY_ROWS_INVALID")
    matches=[
        dict(row) for row in rows
        if isinstance(row,Mapping) and str(row.get("capability_id") or "")==cid
    ]
    if len(matches)!=1:
        raise PureStdlibDFinalError("D_CAPABILITY_ROW_COUNT_INVALID:"+str(len(matches)))
    row=matches[0]
    if row.get("status")!="VERIFIED_D_FINAL_CURRENT":
        raise PureStdlibDFinalError("CAPABILITY_NOT_CURRENT_D_FINAL")
    if row.get("physical_profile")!=PROFILE:
        raise PureStdlibDFinalError("PHYSICAL_PROFILE_INVALID")
    if row.get("physical_dispatch_kind")!=DISPATCH_KIND:
        raise PureStdlibDFinalError("PHYSICAL_DISPATCH_KIND_INVALID")

    cert_path=_safe_canonical(root,row.get("certificate_path"),"CERTIFICATE")
    policy_path=_safe_canonical(root,row.get("policy_path"),"POLICY")
    if d_epoch.git_blob_sha_file(cert_path)!=_hex(
        row.get("certificate_git_blob_sha"),40,"CERTIFICATE_GIT_BLOB_SHA"
    ):
        raise PureStdlibDFinalError("CERTIFICATE_BLOB_DRIFT")
    if d_epoch.git_blob_sha_file(policy_path)!=_hex(
        row.get("policy_git_blob_sha"),40,"POLICY_GIT_BLOB_SHA"
    ):
        raise PureStdlibDFinalError("POLICY_BLOB_DRIFT")

    cert=_load_json(cert_path,"CERTIFICATE")
    policy=_load_json(policy_path,"POLICY")
    if str(cert.get("capability_id") or "")!=cid:
        raise PureStdlibDFinalError("CERTIFICATE_CAPABILITY_MISMATCH")
    cert_sha=d_epoch.certificate_sha256(cert)
    if cert.get("certificate_sha256")!=cert_sha:
        raise PureStdlibDFinalError("CERTIFICATE_SELF_DIGEST_MISMATCH")
    if _hex(row.get("d_certificate_sha256"),64,"D_CERTIFICATE_SHA256")!=cert_sha:
        raise PureStdlibDFinalError("REGISTRY_CERTIFICATE_DIGEST_MISMATCH")
    policy_sha=d_epoch.policy_sha256(policy)
    if _hex(row.get("policy_sha256"),64,"POLICY_SHA256")!=policy_sha:
        raise PureStdlibDFinalError("REGISTRY_POLICY_DIGEST_MISMATCH")

    epoch=d_epoch.verify_certificate(cert,policy=policy,repo_root=root)
    if _hex(row.get("execution_epoch_sha256"),64,"EXECUTION_EPOCH_SHA256")!=epoch.epoch_sha256:
        raise PureStdlibDFinalError("REGISTRY_EXECUTION_EPOCH_MISMATCH")
    if _hex(row.get("material_closure_root"),64,"MATERIAL_CLOSURE_ROOT")!=epoch.material_closure_root:
        raise PureStdlibDFinalError("REGISTRY_MATERIAL_CLOSURE_MISMATCH")
    if row.get("fresh_replay_pass") is not True:
        raise PureStdlibDFinalError("ROW_FRESH_REPLAY_NOT_PASS")
    if row.get("independent_replay_pass") is not True:
        raise PureStdlibDFinalError("ROW_INDEPENDENT_REPLAY_NOT_PASS")
    if row.get("donor_authority_zero") is not True:
        raise PureStdlibDFinalError("ROW_DONOR_AUTHORITY_NOT_ZERO")
    if int(row.get("undeclared_dependency_count",-1))!=0:
        raise PureStdlibDFinalError("ROW_UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO")
    _hex(row.get("provider_theorem_sha256"),64,"PROVIDER_THEOREM_SHA256")
    _hex(row.get("material_certificate_sha256"),64,"MATERIAL_CERTIFICATE_SHA256")

    if list(cert.get("allowed_knowledge_channels") or []):
        raise PureStdlibDFinalError("KNOWLEDGE_CHANNEL_NOT_EMPTY")
    if list(cert.get("allowed_effect_channels") or []):
        raise PureStdlibDFinalError("EFFECT_CHANNEL_NOT_EMPTY")
    contract=capability_contract(cid,row)
    if cert.get("capability_contract_sha256")!=d_epoch.sha256_json(contract):
        raise PureStdlibDFinalError("CAPABILITY_CONTRACT_HASH_MISMATCH")

    launcher_blob=d_epoch.git_blob_sha_file(pathlib.Path(zero_ambient.__file__).resolve())
    if _hex(row.get("zero_ambient_launcher_git_blob_sha"),40,"LAUNCHER_GIT_BLOB_SHA")!=launcher_blob:
        raise PureStdlibDFinalError("ZERO_AMBIENT_LAUNCHER_BLOB_MISMATCH")
    child_path=_safe_canonical(root,CHILD_PATH,"CHILD")
    child_blob=d_epoch.git_blob_sha_file(child_path)
    if _hex(row.get("zero_ambient_child_git_blob_sha"),40,"CHILD_GIT_BLOB_SHA")!=child_blob:
        raise PureStdlibDFinalError("ZERO_AMBIENT_CHILD_BLOB_MISMATCH")

    return {
      "row":row,
      "certificate":cert,
      "policy":policy,
      "certificate_sha256":cert_sha,
      "policy_sha256":policy_sha,
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      "launcher_git_blob_sha":launcher_blob,
      "child_git_blob_sha":child_blob,
    }


def _stage(
    root: pathlib.Path,
    request: Mapping[str,Any],
    *,
    capability_id: str,
    authority: Mapping[str,Any],
) -> pathlib.Path:
    row=authority["row"]
    cert=authority["certificate"]
    materials=cert.get("materials")
    if not isinstance(materials,list) or not materials:
        raise PureStdlibDFinalError("CERTIFICATE_MATERIALS_INVALID")
    bindings={}
    for item in materials:
        if not isinstance(item,Mapping):
            raise PureStdlibDFinalError("MATERIAL_ROW_INVALID")
        rel=str(item.get("path") or "").strip().replace("\\","/")
        expected=_hex(item.get("git_blob_sha"),40,"MATERIAL_GIT_BLOB_SHA")
        path=_safe_canonical(root,rel,"MATERIAL")
        if d_epoch.git_blob_sha_file(path)!=expected:
            raise PureStdlibDFinalError("MATERIAL_BLOB_DRIFT:"+rel)
        if rel in bindings:
            raise PureStdlibDFinalError("MATERIAL_DUPLICATE:"+rel)
        bindings[rel]=expected
    for rel in CORE_MATERIALS:
        if rel not in bindings:
            raise PureStdlibDFinalError("CORE_MATERIAL_MISSING:"+rel)

    bound_registry=_load_json(root/BOUND_REGISTRY_PATH,"BOUND_REGISTRY")
    caps=bound_registry.get("capabilities")
    if not isinstance(caps,Mapping):
        raise PureStdlibDFinalError("BOUND_REGISTRY_CAPABILITIES_INVALID")
    operative=capability_id[6:]
    entry=caps.get(operative)
    if not isinstance(entry,Mapping):
        raise PureStdlibDFinalError("BOUND_CAPABILITY_UNKNOWN")
    source=entry.get("source")
    if not isinstance(source,Mapping) or source.get("type")!="python_stdlib":
        raise PureStdlibDFinalError("BOUND_CAPABILITY_NOT_STDLIB")
    adapter_module=str(entry.get("adapter_module") or "").strip()
    if not adapter_module or not adapter_module.replace("_","").isalnum():
        raise PureStdlibDFinalError("ADAPTER_MODULE_INVALID")
    adapter_rel="canonical/runtime/bound_capabilities/"+adapter_module+".py"
    if adapter_rel not in bindings:
        raise PureStdlibDFinalError("ADAPTER_NOT_CERTIFIED_MATERIAL")
    if bindings[adapter_rel]!=_hex(row.get("adapter_git_blob_sha"),40,"ADAPTER_GIT_BLOB_SHA"):
        raise PureStdlibDFinalError("ADAPTER_ROW_MATERIAL_MISMATCH")
    if bindings[BOUND_REGISTRY_PATH]!=_hex(
        row.get("bound_registry_git_blob_sha"),40,"BOUND_REGISTRY_GIT_BLOB_SHA"
    ):
        raise PureStdlibDFinalError("BOUND_REGISTRY_ROW_MATERIAL_MISMATCH")

    base=pathlib.Path(tempfile.mkdtemp(prefix="brain-d-final-pure-stdlib-"))
    base.chmod(0o755)
    capsule=base/"capsule"
    capsule.mkdir(mode=0o755)
    for rel,expected in sorted(bindings.items()):
        src=root/rel
        dst=capsule/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        current=dst.parent
        while current!=base and base in current.parents:
            current.chmod(0o755)
            current=current.parent
        dst.write_bytes(src.read_bytes())
        dst.chmod(0o644)
        if d_epoch.git_blob_sha_file(dst)!=expected:
            raise PureStdlibDFinalError("STAGED_MATERIAL_BLOB_MISMATCH:"+rel)

    policy=_dynamic_policy(row)
    raw_inputs=request.get("d_input_files") or []
    if not isinstance(raw_inputs,list) or len(raw_inputs)>policy["max_files"]:
        raise PureStdlibDFinalError("D_INPUT_FILES_INVALID")
    dynamic_root=base/"dynamic"
    dynamic_root.mkdir(mode=0o755)
    receipts=[]
    seen=set()
    total=0
    for item in raw_inputs:
        if not isinstance(item,Mapping) or set(item)!={"path","json"}:
            raise PureStdlibDFinalError("D_INPUT_ROW_INVALID")
        rel=str(item.get("path") or "").strip().replace("\\","/")
        p=pathlib.PurePosixPath(rel)
        if not rel or p.is_absolute() or ".." in p.parts or rel in seen:
            raise PureStdlibDFinalError("D_INPUT_PATH_INVALID")
        seen.add(rel)
        if rel in bindings:
            raise PureStdlibDFinalError("D_INPUT_COLLIDES_WITH_MATERIAL")
        if not any(rel.startswith(prefix) for prefix in policy["allowed_prefixes"]):
            raise PureStdlibDFinalError("D_INPUT_PREFIX_NOT_ALLOWED:"+rel)
        if p.suffix.lower() not in policy["allowed_extensions"]:
            raise PureStdlibDFinalError("D_INPUT_EXTENSION_NOT_ALLOWED:"+rel)
        raw=_canon(item.get("json"))
        if len(raw)>policy["max_file_bytes"]:
            raise PureStdlibDFinalError("D_INPUT_FILE_TOO_LARGE")
        total+=len(raw)
        if total>policy["max_total_bytes"]:
            raise PureStdlibDFinalError("D_INPUT_TOTAL_TOO_LARGE")
        dst=dynamic_root/pathlib.Path(*p.parts)
        dst.parent.mkdir(parents=True,exist_ok=True)
        current=dst.parent
        while current!=base and base in current.parents:
            current.chmod(0o755)
            current=current.parent
        dst.write_bytes(raw)
        dst.chmod(0o644)
        receipts.append({
          "path":rel,
          "sha256":hashlib.sha256(raw).hexdigest(),
          "bytes":len(raw),
        })

    clean=dict(request)
    clean.pop("d_input_files",None)
    request_contract=_request_contract(row)
    if set(clean)!=set(request_contract["allowed_request_keys"]):
        raise PureStdlibDFinalError("REQUEST_KEYS_OUTSIDE_CERTIFIED_CONTRACT")
    dynamic_paths={item["path"] for item in receipts}
    for field in request_contract["request_path_fields"]:
        rel=str(clean.get(field) or "").strip().replace("\\","/")
        if rel not in dynamic_paths:
            raise PureStdlibDFinalError("REQUEST_PATH_NOT_STAGED:"+field)

    request_sha256=_sha_json(clean)
    manifest={
      "schema":"PROJECT_BRAIN_D_FINAL_PURE_STDLIB_MANIFEST_V1",
      "capability_id":capability_id,
      "operative_capability_id":operative,
      "materials":[dict(item) for item in materials],
      "dynamic_inputs":receipts,
      "request_contract":request_contract,
      "request_sha256":request_sha256,
      "capability_contract_sha256":authority["certificate"]["capability_contract_sha256"],
      "execution_epoch_sha256":authority["execution_epoch_sha256"],
      "material_closure_root":authority["material_closure_root"],
    }
    _write_json(base/"manifest.json",manifest)
    _write_json(base/"authority.json",{
      "certificate":authority["certificate"],
      "policy":authority["policy"],
    })
    _write_json(base/"request.json",clean)
    return base


def run(
    request: Mapping[str,Any],
    *,
    capability_id: str,
    repo_root: str|pathlib.Path,
    registry_path: str=DEFAULT_REGISTRY,
) -> dict[str,Any]:
    if not isinstance(request,Mapping):
        raise PureStdlibDFinalError("REQUEST_NOT_OBJECT")
    root=pathlib.Path(repo_root).resolve()
    authority=_resolve(capability_id,root=root,registry_path=registry_path)
    base=_stage(root,request,capability_id=capability_id,authority=authority)
    try:
        policy={
          "argv":["/usr/bin/python3","-S","/input/capsule/"+CHILD_PATH],
          "input_dir":str(base),
          "env":{
            "PYTHONDONTWRITEBYTECODE":"1",
            "PYTHONHASHSEED":"0",
            "TZ":"UTC",
            "LANG":"C.UTF-8",
          },
          "limits":{
            "pids":32,
            "memory_mb":1024,
            "cpu_seconds":60,
            "wallclock_s":90,
            "scratch_mb":256,
            "max_file_mb":128,
            "nofile":64,
            "broker_max_bytes":8_000_000,
          },
        }
        if os.geteuid()==0:
            policy["host_uid"]=65534
            policy["host_gid"]=65534
        confined=zero_ambient.run_confined(policy)
        raw=confined.get("broker_payload")
        if not isinstance(raw,(bytes,bytearray)) or not raw:
            raise PureStdlibDFinalError("CHILD_BROKER_PAYLOAD_EMPTY")
        try:
            child=json.loads(bytes(raw).decode("utf-8"))
        except Exception as exc:
            raise PureStdlibDFinalError("CHILD_BROKER_PAYLOAD_INVALID") from exc
        if not isinstance(child,Mapping):
            raise PureStdlibDFinalError("CHILD_RECEIPT_NOT_OBJECT")
        common={
          "schema":SCHEMA,
          "capability_id":capability_id,
          "certificate_sha256":authority["certificate_sha256"],
          "policy_sha256":authority["policy_sha256"],
          "execution_epoch_sha256":authority["execution_epoch_sha256"],
          "material_closure_root":authority["material_closure_root"],
          "launcher_git_blob_sha":authority["launcher_git_blob_sha"],
          "child_git_blob_sha":authority["child_git_blob_sha"],
          "launcher_policy_sha256":confined.get("policy_sha256"),
          "broker_sha256":confined.get("broker_sha256"),
          "physical_zero_ambient_enforced":True,
          "material_effects_committed":confined.get("material_effects_committed"),
          "child_receipt":dict(child),
        }
        if confined.get("returncode")!=0 or child.get("pass") is not True:
            return {
              **common,
              "status":"FAIL_CLOSED__PURE_STDLIB_CHILD_FAILED",
              "pass":False,
            }
        return {
          **common,
          "status":"PASS__PHYSICAL_D_FINAL_PURE_STDLIB",
          "pass":True,
          "dynamic_input_count":child.get("dynamic_input_count"),
          "dynamic_inputs":child.get("dynamic_inputs"),
          "result":dict(child.get("result") or {}),
        }
    finally:
        shutil.rmtree(base,ignore_errors=True)
