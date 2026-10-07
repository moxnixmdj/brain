"""Bind certificate-gated route selection to the exact execution payload.

This module is mechanical. It does not decide whether a certificate is semantically
sound; it prevents execution of bytes or context different from those named by an
already-admitted content-addressed receipt.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt,
    RouterFailClosed,
    select_certified_route,
)

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_ROUTE_EXECUTION_BINDING_V1"

class RouteExecutionBindingError(RuntimeError):
    pass

def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RouteExecutionBindingError("NON_CANONICAL_JSON_VALUE") from exc

def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def _context_digest(mission: Mapping[str, Any]) -> str:
    context = mission.get("certificate_gated_context")
    if not isinstance(context, Mapping) or not context:
        raise RouteExecutionBindingError("CERTIFICATE_GATED_CONTEXT_MISSING")
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(context)).hexdigest()

def _operative_step(step: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(step)
    out.pop("certificate_gated_route", None)
    return out

def operative_step_git_blob_sha(step: Mapping[str, Any]) -> str:
    return _git_blob_sha1(_canonical_json_bytes(_operative_step(step)))

def _repo_file_blob_sha(root: Path, raw_path: Any, label: str) -> tuple[str, str]:
    rel = str(raw_path or "").strip().replace("\\", "/")
    if not rel or rel.startswith("/") or rel.startswith("../") or "/../" in "/" + rel:
        raise RouteExecutionBindingError(label + "_PATH_INVALID")
    base = root.resolve()
    path = (base / rel).resolve()
    if path == base or base not in path.parents:
        raise RouteExecutionBindingError(label + "_PATH_ESCAPES_ROOT")
    if not path.is_file():
        raise RouteExecutionBindingError(label + "_FILE_MISSING")
    return rel, _git_blob_sha1(path.read_bytes())

def _receipt(raw: Any, idx: int) -> AdmissionReceipt:
    if not isinstance(raw, Mapping):
        raise RouteExecutionBindingError(f"RECEIPT_NOT_OBJECT:{idx}")
    required = (
        "context_digest", "cell_id", "route_id", "route_blob_sha",
        "adequacy_certificate_blob_sha", "admission_certificate_blob_sha", "admitted",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise RouteExecutionBindingError("RECEIPT_FIELD_MISSING:" + ",".join(missing))
    return AdmissionReceipt(**{k: raw[k] for k in required})

def authorize_step(*, root: Path, mission: Mapping[str, Any], step: Mapping[str, Any]) -> dict[str, Any] | None:
    required = mission.get("certificate_gated_routing_required")
    if required not in (None, True, False) or (required is not None and type(required) is not bool):
        raise RouteExecutionBindingError("ROUTING_REQUIRED_MUST_BE_LITERAL_BOOL")
    raw = step.get("certificate_gated_route")
    if raw is None:
        if required is True:
            raise RouteExecutionBindingError("CERTIFICATE_GATED_ROUTE_REQUIRED")
        return None
    if not isinstance(raw, Mapping):
        raise RouteExecutionBindingError("CERTIFICATE_GATED_ROUTE_NOT_OBJECT")

    route_id = str(raw.get("route_id") or "").strip()
    if not route_id:
        raise RouteExecutionBindingError("EXPECTED_ROUTE_ID_MISSING")
    receipts_raw = raw.get("receipts")
    if not isinstance(receipts_raw, list) or not receipts_raw:
        raise RouteExecutionBindingError("ADMISSION_RECEIPTS_MISSING")
    receipts = [_receipt(x, i) for i, x in enumerate(receipts_raw)]

    context_digest = _context_digest(mission)
    try:
        selected = select_certified_route(actual_context_digest=context_digest, receipts=receipts)
    except RouterFailClosed as exc:
        raise RouteExecutionBindingError("ROUTER_FAIL_CLOSED:" + str(exc)) from exc

    if selected.route_id != route_id:
        raise RouteExecutionBindingError("SELECTED_ROUTE_ID_MISMATCH")
    actual_route_blob = operative_step_git_blob_sha(step)
    if selected.route_blob_sha != actual_route_blob:
        raise RouteExecutionBindingError("OPERATIVE_STEP_BLOB_MISMATCH")

    admission_path, admission_blob = _repo_file_blob_sha(
        root, raw.get("admission_certificate_path"), "ADMISSION_CERTIFICATE"
    )
    adequacy_path, adequacy_blob = _repo_file_blob_sha(
        root, raw.get("adequacy_certificate_path"), "ADEQUACY_CERTIFICATE"
    )
    if selected.admission_certificate_blob_sha != admission_blob:
        raise RouteExecutionBindingError("ADMISSION_CERTIFICATE_BLOB_MISMATCH")
    if selected.adequacy_certificate_blob_sha != adequacy_blob:
        raise RouteExecutionBindingError("ADEQUACY_CERTIFICATE_BLOB_MISMATCH")

    return {
        "schema": SCHEMA,
        "status": "AUTHORIZED__EXACT_CONTEXT_ROUTE_AND_CERTIFICATE_BLOBS_BOUND",
        "context_digest": context_digest,
        "cell_id": selected.cell_id,
        "route_id": selected.route_id,
        "route_blob_sha": selected.route_blob_sha,
        "admission_certificate_path": admission_path,
        "admission_certificate_blob_sha": admission_blob,
        "adequacy_certificate_path": adequacy_path,
        "adequacy_certificate_blob_sha": adequacy_blob,
        "admitted": True,
        "terminal_authority": False,
    }
