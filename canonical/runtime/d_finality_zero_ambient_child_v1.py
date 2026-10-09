"""Zero-ambient D-final child bootstrap V1.

Runs only inside zero_ambient_namespace_launcher_v1. It reconstructs the exact
certified material closure in private /work, activates the supplied canonical
D epoch, dispatches one already-resolved fabric request, and emits exactly one
JSON receipt through the inherited broker FD.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sys
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_D_FINALITY_ZERO_AMBIENT_CHILD_V1"


class ChildError(ValueError):
    pass


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _safe_rel(raw: Any) -> pathlib.PurePosixPath:
    text=str(raw or "").strip()
    p=pathlib.PurePosixPath(text)
    if not text or p.is_absolute() or ".." in p.parts:
        raise ChildError("MATERIAL_PATH_INVALID")
    return p


def _load(path: pathlib.Path, label: str) -> dict[str,Any]:
    try:
        doc=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChildError(label+"_JSON_INVALID") from exc
    if not isinstance(doc,Mapping):
        raise ChildError(label+"_NOT_OBJECT")
    return dict(doc)


def _emit(value: Mapping[str,Any]) -> None:
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")
    fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
    offset=0
    while offset<len(raw):
        offset+=os.write(fd,raw[offset:])


def main() -> int:
    try:
        input_root=pathlib.Path("/input")
        capsule=input_root/"capsule"
        manifest=_load(input_root/"manifest.json","MANIFEST")
        authority=_load(input_root/"authority.json","AUTHORITY")
        request=_load(input_root/"request.json","REQUEST")
        if manifest.get("schema")!="PROJECT_BRAIN_D_FINALITY_ZERO_AMBIENT_MANIFEST_V1":
            raise ChildError("MANIFEST_SCHEMA_INVALID")
        materials=manifest.get("materials")
        if not isinstance(materials,list) or not materials:
            raise ChildError("MATERIALS_INVALID")

        work_root=pathlib.Path("/work/repo")
        work_root.mkdir(parents=True,exist_ok=True)
        copied=[]
        for row in materials:
            if not isinstance(row,Mapping):
                raise ChildError("MATERIAL_ROW_INVALID")
            rel=_safe_rel(row.get("path"))
            expected=str(row.get("git_blob_sha") or "").lower()
            src=capsule/pathlib.Path(*rel.parts)
            dst=work_root/pathlib.Path(*rel.parts)
            if not src.is_file():
                raise ChildError("MATERIAL_SOURCE_MISSING:"+str(rel))
            raw=src.read_bytes()
            if _git_blob(raw)!=expected:
                raise ChildError("MATERIAL_INPUT_BLOB_MISMATCH:"+str(rel))
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(raw)
            if _git_blob(dst.read_bytes())!=expected:
                raise ChildError("MATERIAL_COPY_BLOB_MISMATCH:"+str(rel))
            copied.append({"path":str(rel),"git_blob_sha":expected})

        dynamic=manifest.get("dynamic_inputs") or []
        if not isinstance(dynamic,list):
            raise ChildError("DYNAMIC_INPUTS_INVALID")
        material_paths={row["path"] for row in copied}
        dynamic_receipts=[]
        for row in dynamic:
            if not isinstance(row,Mapping):
                raise ChildError("DYNAMIC_INPUT_ROW_INVALID")
            rel=_safe_rel(row.get("path"))
            rel_text=str(rel)
            if rel_text in material_paths:
                raise ChildError("DYNAMIC_INPUT_COLLIDES_WITH_MATERIAL:"+rel_text)
            expected=str(row.get("sha256") or "").lower()
            src=input_root/"dynamic"/pathlib.Path(*rel.parts)
            dst=work_root/pathlib.Path(*rel.parts)
            if not src.is_file():
                raise ChildError("DYNAMIC_INPUT_SOURCE_MISSING:"+rel_text)
            raw=src.read_bytes()
            actual=hashlib.sha256(raw).hexdigest()
            if actual!=expected:
                raise ChildError("DYNAMIC_INPUT_HASH_MISMATCH:"+rel_text)
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(raw)
            if hashlib.sha256(dst.read_bytes()).hexdigest()!=expected:
                raise ChildError("DYNAMIC_INPUT_COPY_HASH_MISMATCH:"+rel_text)
            dynamic_receipts.append({
                "path":rel_text,
                "sha256":expected,
                "bytes":len(raw),
            })

        # Certified code wins import precedence. Python is launched with -S, so
        # ambient third-party site-packages are not admitted by default.
        sys.path.insert(0,str(work_root))
        from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch

        cert=authority.get("certificate")
        policy=authority.get("policy")
        cid=str(manifest.get("capability_id") or "").strip()
        dispatch_kind=str(manifest.get("physical_dispatch_kind") or "").strip()
        if not isinstance(cert,Mapping) or not isinstance(policy,Mapping) or not cid:
            raise ChildError("AUTHORITY_INCOMPLETE")
        if dispatch_kind not in {
            "UNIFIED_FABRIC_V1",
            "D_FINAL_STDLIB_BOUND_EXECUTOR_V1",
        }:
            raise ChildError("PHYSICAL_DISPATCH_KIND_UNSUPPORTED:"+dispatch_kind)

        with d_epoch.activate(cert,policy=policy,repo_root=work_root) as epoch:
            if epoch.root_capability_id!=cid:
                raise ChildError("ROOT_CAPABILITY_ID_MISMATCH")
            if str(manifest.get("execution_epoch_sha256") or "")!=epoch.epoch_sha256:
                raise ChildError("MANIFEST_EXECUTION_EPOCH_MISMATCH")
            if str(manifest.get("material_closure_root") or "")!=epoch.material_closure_root:
                raise ChildError("MANIFEST_MATERIAL_CLOSURE_MISMATCH")
            d_epoch.require_capability(cid)

            if dispatch_kind=="UNIFIED_FABRIC_V1":
                from canonical.runtime import unified_cognitive_fabric_v1 as fabric
                result=fabric.run(request)
            else:
                if not cid.startswith("bound:") or not cid[6:]:
                    raise ChildError("STDLIB_BOUND_CAPABILITY_ID_REQUIRED")
                from canonical.runtime import d_final_stdlib_bound_executor_v1 as executor
                operative=cid[6:]
                prepared=executor.prepare(operative,inputs=request)
                result=executor.execute(
                    operative,
                    inputs=request,
                    expected_registry_file_sha256=prepared["registry_file_sha256"],
                    expected_registry_entry_sha256=prepared["registry_entry_sha256"],
                    expected_rendered_action_sha256=prepared["rendered_action_sha256"],
                )
                if result.get("pass") is not True:
                    raise ChildError(
                        "STDLIB_BOUND_EXECUTION_FAILED:"
                        +"|".join(str(x) for x in result.get("errors") or ["UNKNOWN"])
                    )

        if not isinstance(result,Mapping):
            raise ChildError("DISPATCH_RESULT_NOT_OBJECT")

        # The authority set may not mutate itself during the epoch. Re-hash every
        # certified material and every staged dynamic input after execution.
        post_material_checks=[]
        for row in copied:
            rel=row["path"]
            expected=row["git_blob_sha"]
            path=work_root/pathlib.PurePosixPath(rel)
            actual=_git_blob(path.read_bytes()) if path.is_file() else None
            if actual!=expected:
                raise ChildError("MATERIAL_CHANGED_DURING_EXECUTION:"+rel)
            post_material_checks.append({"path":rel,"git_blob_sha":actual})

        post_dynamic_checks=[]
        for row in dynamic_receipts:
            rel=row["path"]
            expected=row["sha256"]
            path=work_root/pathlib.PurePosixPath(rel)
            actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if actual!=expected:
                raise ChildError("DYNAMIC_INPUT_CHANGED_DURING_EXECUTION:"+rel)
            post_dynamic_checks.append({"path":rel,"sha256":actual})

        receipt={
          "schema":SCHEMA,
          "status":"PASS__ZERO_AMBIENT_D_FINAL_DISPATCH_COMPLETE",
          "pass":True,
          "capability_id":cid,
          "physical_dispatch_kind":dispatch_kind,
          "execution_epoch_sha256":epoch.epoch_sha256,
          "material_closure_root":epoch.material_closure_root,
          "copied_material_count":len(copied),
          "dynamic_input_count":len(dynamic_receipts),
          "dynamic_inputs":dynamic_receipts,
          "post_execution_material_rehash_pass":True,
          "post_execution_materials":post_material_checks,
          "post_execution_dynamic_input_rehash_pass":True,
          "post_execution_dynamic_inputs":post_dynamic_checks,
          "result":dict(result),
        }
        _emit(receipt)
        return 0
    except Exception as exc:
        _emit({
          "schema":SCHEMA,
          "status":"FAIL_CLOSED__ZERO_AMBIENT_D_FINAL_CHILD",
          "pass":False,
          "reason":type(exc).__name__+":"+str(exc),
        })
        return 1


if __name__=="__main__":
    raise SystemExit(main())
