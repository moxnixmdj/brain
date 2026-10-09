"""Physical zero-ambient D-final front-door runner V1.

This is intentionally limited to ZERO_AMBIENT_PURE_V1:
- no external knowledge channel;
- no external effect channel;
- exact certified material closure only;
- private network namespace;
- private writable /work and /tmp;
- broker-only result egress.

Broader world-I/O capabilities require the typed broker profile and are not
silently admitted here.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch
from canonical.runtime import d_finality_canonical_resolver_v1 as resolver
from canonical.runtime import zero_ambient_namespace_launcher_v1 as zero_ambient

SCHEMA="PROJECT_BRAIN_D_FINALITY_ZERO_AMBIENT_FRONTDOOR_V1"
PROFILE="ZERO_AMBIENT_PURE_V1"
CHILD_PATH="canonical/runtime/d_finality_zero_ambient_child_v1.py"
FABRIC_PATH="canonical/runtime/unified_cognitive_fabric_v1.py"
EPOCH_PATH="canonical/runtime/d_finality_execution_epoch_v1.py"


class ZeroAmbientDFinalError(ValueError):
    pass


def _write_json(path: pathlib.Path, value: Mapping[str,Any]) -> None:
    path.write_text(
        json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False),
        encoding="utf-8",
    )
    path.chmod(0o644)


def _prepare_input(
    root: pathlib.Path,
    *,
    capability_id: str,
    request: Mapping[str,Any],
    authority: Mapping[str,Any],
) -> pathlib.Path:
    cert=authority["certificate"]
    materials=cert.get("materials")
    if not isinstance(materials,list) or not materials:
        raise ZeroAmbientDFinalError("CERTIFICATE_MATERIALS_INVALID")
    bindings={}
    for row in materials:
        if not isinstance(row,Mapping):
            raise ZeroAmbientDFinalError("MATERIAL_ROW_INVALID")
        rel=str(row.get("path") or "").strip()
        expected=str(row.get("git_blob_sha") or "").lower()
        if not rel or pathlib.PurePosixPath(rel).is_absolute() or ".." in pathlib.PurePosixPath(rel).parts:
            raise ZeroAmbientDFinalError("MATERIAL_PATH_INVALID")
        src=(root/rel).resolve()
        try:
            src.relative_to(root)
        except ValueError as exc:
            raise ZeroAmbientDFinalError("MATERIAL_PATH_ESCAPES_ROOT") from exc
        if not src.is_file():
            raise ZeroAmbientDFinalError("MATERIAL_FILE_MISSING:"+rel)
        if d_epoch.git_blob_sha_file(src)!=expected:
            raise ZeroAmbientDFinalError("MATERIAL_BLOB_DRIFT:"+rel)
        bindings[rel]=expected

    for required in (CHILD_PATH,FABRIC_PATH,EPOCH_PATH):
        if required not in bindings:
            raise ZeroAmbientDFinalError("REQUIRED_EXECUTION_MATERIAL_MISSING:"+required)

    base=pathlib.Path(tempfile.mkdtemp(prefix="brain-d-final-input-"))
    base.chmod(0o755)
    capsule=base/"capsule"
    capsule.mkdir(mode=0o755)
    for rel,expected in sorted(bindings.items()):
        src=root/rel
        dst=capsule/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        # Make the staged input readable by a non-root launcher child.
        current=dst.parent
        while current!=base and base in current.parents:
            current.chmod(0o755)
            current=current.parent
        dst.write_bytes(src.read_bytes())
        dst.chmod(0o644)
        if d_epoch.git_blob_sha_file(dst)!=expected:
            raise ZeroAmbientDFinalError("STAGED_MATERIAL_BLOB_MISMATCH:"+rel)

    manifest={
      "schema":"PROJECT_BRAIN_D_FINALITY_ZERO_AMBIENT_MANIFEST_V1",
      "capability_id":capability_id,
      "materials":[dict(x) for x in materials],
      "material_closure_root":authority["material_closure_root"],
      "execution_epoch_sha256":authority["execution_epoch_sha256"],
    }
    _write_json(base/"manifest.json",manifest)
    _write_json(base/"authority.json",{
      "certificate":authority["certificate"],
      "policy":authority["policy"],
    })
    clean_request=dict(request)
    clean_request.pop("ownership_mode",None)
    _write_json(base/"request.json",clean_request)
    return base


def run(
    request: Mapping[str,Any],
    *,
    capability_id: str,
    repo_root: str|pathlib.Path,
) -> dict[str,Any]:
    if not isinstance(request,Mapping):
        raise ZeroAmbientDFinalError("REQUEST_NOT_OBJECT")
    cid=str(capability_id or "").strip()
    if not cid:
        raise ZeroAmbientDFinalError("CAPABILITY_ID_REQUIRED")
    root=pathlib.Path(repo_root).resolve()
    authority=resolver.resolve_for_capability(cid,repo_root=root)
    row=authority.get("registry_row")
    if not isinstance(row,Mapping):
        raise ZeroAmbientDFinalError("REGISTRY_ROW_NOT_AVAILABLE")
    if row.get("physical_profile")!=PROFILE:
        raise ZeroAmbientDFinalError("PHYSICAL_PROFILE_NOT_PURE_ZERO_AMBIENT")
    cert=authority["certificate"]
    if list(cert.get("allowed_knowledge_channels") or []):
        raise ZeroAmbientDFinalError("PURE_PROFILE_KNOWLEDGE_CHANNEL_NOT_EMPTY")
    if list(cert.get("allowed_effect_channels") or []):
        raise ZeroAmbientDFinalError("PURE_PROFILE_EFFECT_CHANNEL_NOT_EMPTY")

    launcher_path=pathlib.Path(zero_ambient.__file__).resolve()
    launcher_blob=d_epoch.git_blob_sha_file(launcher_path)
    if str(row.get("zero_ambient_launcher_git_blob_sha") or "")!=launcher_blob:
        raise ZeroAmbientDFinalError("ZERO_AMBIENT_LAUNCHER_BLOB_MISMATCH")
    child_path=(root/CHILD_PATH).resolve()
    child_blob=d_epoch.git_blob_sha_file(child_path)
    if str(row.get("zero_ambient_child_git_blob_sha") or "")!=child_blob:
        raise ZeroAmbientDFinalError("ZERO_AMBIENT_CHILD_BLOB_MISMATCH")

    base=_prepare_input(
        root,
        capability_id=cid,
        request=request,
        authority=authority,
    )
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
            raise ZeroAmbientDFinalError("CHILD_BROKER_PAYLOAD_EMPTY")
        try:
            child=json.loads(bytes(raw).decode("utf-8"))
        except Exception as exc:
            raise ZeroAmbientDFinalError("CHILD_BROKER_PAYLOAD_INVALID_JSON") from exc
        if not isinstance(child,Mapping):
            raise ZeroAmbientDFinalError("CHILD_RECEIPT_NOT_OBJECT")
        if confined.get("returncode")!=0 or child.get("pass") is not True:
            return {
              "schema":SCHEMA,
              "status":"FAIL_CLOSED__PHYSICAL_D_FINAL_CHILD_FAILED",
              "pass":False,
              "capability_id":cid,
              "launcher_policy_sha256":confined.get("policy_sha256"),
              "launcher_status":confined.get("status"),
              "launcher_returncode":confined.get("returncode"),
              "broker_sha256":confined.get("broker_sha256"),
              "child_receipt":dict(child),
              "physical_zero_ambient_enforced":True,
              "material_effects_committed":confined.get("material_effects_committed"),
            }
        return {
          "schema":SCHEMA,
          "status":"PASS__PHYSICAL_D_FINAL_ZERO_AMBIENT",
          "pass":True,
          "capability_id":cid,
          "certificate_sha256":authority["certificate_sha256"],
          "policy_sha256":authority["policy_sha256"],
          "execution_epoch_sha256":authority["execution_epoch_sha256"],
          "material_closure_root":authority["material_closure_root"],
          "launcher_git_blob_sha":launcher_blob,
          "child_git_blob_sha":child_blob,
          "launcher_policy_sha256":confined.get("policy_sha256"),
          "broker_sha256":confined.get("broker_sha256"),
          "physical_zero_ambient_enforced":True,
          "material_effects_committed":confined.get("material_effects_committed"),
          "result":dict(child.get("result") or {}),
          "child_receipt":dict(child),
        }
    finally:
        shutil.rmtree(base,ignore_errors=True)
