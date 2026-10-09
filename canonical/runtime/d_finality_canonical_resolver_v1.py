"""Canonical resolver for current D-final execution authority.

Caller input never supplies certificate or policy bytes. Authority is resolved
only from the canonical D-finality registry and content-bound canonical files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch

SCHEMA="PROJECT_BRAIN_D_FINALITY_CANONICAL_RESOLVER_V1"
REGISTRY_SCHEMA="PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1"
DEFAULT_REGISTRY="canonical/governance/D_FINALITY_CERTIFICATE_REGISTRY_V1.json"


class DFinalityResolutionError(ValueError):
    pass


def _git_blob(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _safe_canonical(root: Path, raw: Any, label: str) -> Path:
    rel=str(raw or "").strip()
    p=Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts or not rel.startswith("canonical/"):
        raise DFinalityResolutionError(label+"_PATH_INVALID")
    full=(root/p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise DFinalityResolutionError(label+"_PATH_ESCAPES_ROOT") from exc
    if not full.is_file():
        raise DFinalityResolutionError(label+"_FILE_MISSING")
    return full


def _load_json(path: Path, label: str) -> dict[str,Any]:
    try:
        doc=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DFinalityResolutionError(label+"_JSON_INVALID") from exc
    if not isinstance(doc,Mapping):
        raise DFinalityResolutionError(label+"_NOT_OBJECT")
    return dict(doc)


def resolve_for_capability(
    capability_id: str,
    *,
    repo_root: str|Path,
    registry_path: str|Path|None=None,
) -> dict[str,Any]:
    cid=str(capability_id or "").strip()
    if not cid:
        raise DFinalityResolutionError("CAPABILITY_ID_REQUIRED")
    root=Path(repo_root).resolve()
    reg_path=(
        _safe_canonical(root, registry_path, "REGISTRY")
        if registry_path is not None
        else _safe_canonical(root, DEFAULT_REGISTRY, "REGISTRY")
    )
    registry=_load_json(reg_path,"REGISTRY")
    if registry.get("schema")!=REGISTRY_SCHEMA:
        raise DFinalityResolutionError("REGISTRY_SCHEMA_INVALID")
    if registry.get("status")!="ACTIVE_FAIL_CLOSED":
        raise DFinalityResolutionError("REGISTRY_NOT_ACTIVE")
    if registry.get("default")!="NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW":
        raise DFinalityResolutionError("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    rows=registry.get("rows")
    if not isinstance(rows,list):
        raise DFinalityResolutionError("REGISTRY_ROWS_NOT_LIST")
    matches=[r for r in rows if isinstance(r,Mapping) and str(r.get("capability_id") or "")==cid]
    if len(matches)!=1:
        raise DFinalityResolutionError("CAPABILITY_ROW_COUNT_INVALID:"+str(len(matches)))
    row=dict(matches[0])
    if row.get("status")!="VERIFIED_D_FINAL_CURRENT":
        raise DFinalityResolutionError("CAPABILITY_NOT_CURRENT_D_FINAL:"+cid)

    cert_path=_safe_canonical(root,row.get("certificate_path"),"CERTIFICATE")
    policy_path=_safe_canonical(root,row.get("policy_path"),"POLICY")
    cert_blob=str(row.get("certificate_git_blob_sha") or "").lower()
    policy_blob=str(row.get("policy_git_blob_sha") or "").lower()
    if _git_blob(cert_path)!=cert_blob:
        raise DFinalityResolutionError("CERTIFICATE_BLOB_DRIFT")
    if _git_blob(policy_path)!=policy_blob:
        raise DFinalityResolutionError("POLICY_BLOB_DRIFT")

    cert=_load_json(cert_path,"CERTIFICATE")
    policy=_load_json(policy_path,"POLICY")
    if str(cert.get("capability_id") or "")!=cid:
        raise DFinalityResolutionError("CERTIFICATE_CAPABILITY_ID_MISMATCH")

    cert_sha=d_epoch.certificate_sha256(cert)
    if cert.get("certificate_sha256")!=cert_sha:
        raise DFinalityResolutionError("CERTIFICATE_SELF_DIGEST_MISMATCH")
    if str(row.get("d_certificate_sha256") or "")!=cert_sha:
        raise DFinalityResolutionError("REGISTRY_CERTIFICATE_DIGEST_MISMATCH")

    policy_sha=d_epoch.policy_sha256(policy)
    if str(row.get("policy_sha256") or "")!=policy_sha:
        raise DFinalityResolutionError("REGISTRY_POLICY_DIGEST_MISMATCH")

    epoch=d_epoch.verify_certificate(cert,policy=policy,repo_root=root)
    if str(row.get("execution_epoch_sha256") or "")!=epoch.epoch_sha256:
        raise DFinalityResolutionError("REGISTRY_EXECUTION_EPOCH_MISMATCH")
    if str(row.get("material_closure_root") or "")!=epoch.material_closure_root:
        raise DFinalityResolutionError("REGISTRY_MATERIAL_CLOSURE_MISMATCH")
    if row.get("fresh_replay_pass") is not True:
        raise DFinalityResolutionError("ROW_FRESH_REPLAY_NOT_PASS")
    if row.get("independent_replay_pass") is not True:
        raise DFinalityResolutionError("ROW_INDEPENDENT_REPLAY_NOT_PASS")
    if row.get("donor_authority_zero") is not True:
        raise DFinalityResolutionError("ROW_DONOR_AUTHORITY_NOT_ZERO")
    if int(row.get("undeclared_dependency_count",-1))!=0:
        raise DFinalityResolutionError("ROW_UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO")

    return {
      "schema":SCHEMA,
      "status":"PASS__CANONICAL_D_FINAL_AUTHORITY_RESOLVED",
      "pass":True,
      "capability_id":cid,
      "registry_git_blob_sha":_git_blob(reg_path),
      "certificate_path":cert_path.relative_to(root).as_posix(),
      "certificate_git_blob_sha":cert_blob,
      "policy_path":policy_path.relative_to(root).as_posix(),
      "policy_git_blob_sha":policy_blob,
      "certificate_sha256":cert_sha,
      "policy_sha256":policy_sha,
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      "registry_row":dict(row),
      "certificate":cert,
      "policy":policy,
    }
