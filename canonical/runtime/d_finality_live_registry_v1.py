"""Canonical live activation registry for D-final certificates V1.

Structural admission and D-final ownership are separate.

Only a registry row with status == VERIFIED_D_FINAL_CURRENT may activate a D
execution epoch. The row binds the certificate path and exact certificate
self-digest. Missing, stale, malformed, or mismatched rows fail closed.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, Iterator, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch

SCHEMA="PROJECT_BRAIN_D_FINALITY_LIVE_REGISTRY_V1"
POLICY_PATH="canonical/governance/D_FINALITY_POLICY_V1.json"
REGISTRY_PATH="canonical/governance/D_FINALITY_CERTIFICATE_REGISTRY_V1.json"


class DFinalityLiveRegistryError(ValueError):
    pass


def _load_json(path: Path) -> Mapping[str, Any]:
    doc=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise DFinalityLiveRegistryError("JSON_ROOT_NOT_OBJECT:"+str(path))
    return doc


def load_policy(repo_root: str | Path) -> Mapping[str, Any]:
    root=Path(repo_root).resolve()
    policy=_load_json(root/POLICY_PATH)
    if policy.get("schema")!=d_epoch.POLICY_SCHEMA:
        raise DFinalityLiveRegistryError("D_POLICY_SCHEMA_INVALID")
    if policy.get("status")!="ACTIVE_FAIL_CLOSED":
        raise DFinalityLiveRegistryError("D_POLICY_NOT_ACTIVE")
    return policy


def load_registry(repo_root: str | Path) -> Mapping[str, Any]:
    root=Path(repo_root).resolve()
    reg=_load_json(root/REGISTRY_PATH)
    if reg.get("schema")!="PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1":
        raise DFinalityLiveRegistryError("D_REGISTRY_SCHEMA_INVALID")
    if reg.get("status")!="ACTIVE_FAIL_CLOSED":
        raise DFinalityLiveRegistryError("D_REGISTRY_NOT_ACTIVE")
    rows=reg.get("rows")
    if not isinstance(rows,list):
        raise DFinalityLiveRegistryError("D_REGISTRY_ROWS_INVALID")
    return reg


def current_row(capability_id: str, *, repo_root: str | Path) -> Mapping[str, Any] | None:
    cid=str(capability_id or "").strip()
    reg=load_registry(repo_root)
    matches=[
        row for row in reg["rows"]
        if isinstance(row, Mapping) and str(row.get("capability_id") or "")==cid
    ]
    if len(matches)>1:
        raise DFinalityLiveRegistryError("D_REGISTRY_DUPLICATE_CAPABILITY:"+cid)
    if not matches:
        return None
    row=matches[0]
    if row.get("status")!="VERIFIED_D_FINAL_CURRENT":
        return None
    certificate_path=str(row.get("certificate_path") or "").strip()
    certificate_sha=str(row.get("d_certificate_sha256") or "").strip().lower()
    if not certificate_path or len(certificate_sha)!=64:
        raise DFinalityLiveRegistryError("D_CURRENT_ROW_CERTIFICATE_BINDING_INVALID:"+cid)
    return row


@contextlib.contextmanager
def activate_if_current(
    capability_id: str,
    *,
    repo_root: str | Path,
) -> Iterator[d_epoch.DExecutionEpoch | None]:
    root=Path(repo_root).resolve()
    row=current_row(capability_id,repo_root=root)
    if row is None:
        yield None
        return
    rel=Path(str(row["certificate_path"]))
    if rel.is_absolute() or ".." in rel.parts:
        raise DFinalityLiveRegistryError("D_CERTIFICATE_PATH_INVALID")
    cert_path=(root/rel).resolve()
    try:
        cert_path.relative_to(root)
    except ValueError as exc:
        raise DFinalityLiveRegistryError("D_CERTIFICATE_PATH_ESCAPES_ROOT") from exc
    certificate=_load_json(cert_path)
    actual=d_epoch.certificate_sha256(certificate)
    if actual!=str(row["d_certificate_sha256"]).lower():
        raise DFinalityLiveRegistryError("D_CERTIFICATE_REGISTRY_DIGEST_MISMATCH")
    if certificate.get("certificate_sha256")!=actual:
        raise DFinalityLiveRegistryError("D_CERTIFICATE_SELF_DIGEST_MISMATCH")
    policy=load_policy(root)
    with d_epoch.activate(certificate,policy=policy,repo_root=root) as epoch:
        if epoch.root_capability_id!=str(capability_id):
            raise DFinalityLiveRegistryError("D_CERTIFICATE_CAPABILITY_ID_MISMATCH")
        yield epoch
