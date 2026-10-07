"""Canonical certificate-gated selected-route runtime entrypoint.

The entrypoint computes the context digest itself, verifies the content-addressed
route and both certificates, delegates selection to the fail-closed router, and
only then imports and invokes the selected callable.

The initial registry intentionally contains only a non-creditable deployment
canary. Therefore this closes deployment mechanics, not selected-cover
completeness or terminal credit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt,
    RouterFailClosed,
    select_certified_route,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1.json"
SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1"


class RuntimeBindingFailClosed(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def context_digest(context: Mapping[str, Any]) -> str:
    if not isinstance(context, Mapping):
        raise RuntimeBindingFailClosed("CONTEXT_MAPPING_REQUIRED")
    try:
        raw = json.dumps(
            dict(context),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeBindingFailClosed("CONTEXT_NOT_CANONICAL_JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _canonical_path(raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise RuntimeBindingFailClosed("NONCANONICAL_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise RuntimeBindingFailClosed("PATH_OUTSIDE_ALLOWED_CANONICAL_SCOPE")
    full = ROOT / p
    if not full.is_file():
        raise RuntimeBindingFailClosed("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeBindingFailClosed("BOUND_JSON_INVALID:" + str(path.relative_to(ROOT))) from exc
    if not isinstance(value, Mapping):
        raise RuntimeBindingFailClosed("BOUND_JSON_NOT_OBJECT:" + str(path.relative_to(ROOT)))
    return value


def load_registry() -> Mapping[str, Any]:
    reg = _load_json(REGISTRY_PATH)
    if reg.get("schema") != REGISTRY_SCHEMA:
        raise RuntimeBindingFailClosed("REGISTRY_SCHEMA_INVALID")
    if reg.get("default") != "FAIL_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    if type(reg.get("selected_cover_complete")) is not bool:
        raise RuntimeBindingFailClosed("REGISTRY_SELECTED_COVER_FLAG_INVALID")
    routes = reg.get("routes")
    if not isinstance(routes, list):
        raise RuntimeBindingFailClosed("REGISTRY_ROUTES_NOT_LIST")
    router = reg.get("router")
    if not isinstance(router, Mapping):
        raise RuntimeBindingFailClosed("REGISTRY_ROUTER_BINDING_MISSING")
    router_path = _canonical_path(router.get("path"), prefixes=("canonical/runtime/",))
    if router.get("git_blob_sha") != git_blob_sha(router_path):
        raise RuntimeBindingFailClosed("ROUTER_BLOB_DRIFT")
    return reg


def _verified_rows(registry: Mapping[str, Any]) -> tuple[list[AdmissionReceipt], dict[tuple[str, ...], Mapping[str, Any]]]:
    receipts: list[AdmissionReceipt] = []
    rows_by_identity: dict[tuple[str, ...], Mapping[str, Any]] = {}
    for index, row in enumerate(registry.get("routes") or []):
        if not isinstance(row, Mapping):
            raise RuntimeBindingFailClosed(f"ROUTE_ROW_NOT_OBJECT:{index}")
        if type(row.get("admitted")) is not bool:
            raise RuntimeBindingFailClosed(f"ROUTE_ADMISSION_NOT_LITERAL_BOOL:{index}")
        if type(row.get("creditable")) is not bool:
            raise RuntimeBindingFailClosed(f"ROUTE_CREDITABLE_NOT_LITERAL_BOOL:{index}")

        route_path = _canonical_path(row.get("route_path"), prefixes=("canonical/runtime/",))
        adequacy_path = _canonical_path(
            row.get("adequacy_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        admission_path = _canonical_path(
            row.get("admission_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        if row.get("route_blob_sha") != git_blob_sha(route_path):
            raise RuntimeBindingFailClosed(f"ROUTE_BLOB_DRIFT:{index}")
        if row.get("adequacy_certificate_blob_sha") != git_blob_sha(adequacy_path):
            raise RuntimeBindingFailClosed(f"ADEQUACY_CERTIFICATE_BLOB_DRIFT:{index}")
        if row.get("admission_certificate_blob_sha") != git_blob_sha(admission_path):
            raise RuntimeBindingFailClosed(f"ADMISSION_CERTIFICATE_BLOB_DRIFT:{index}")

        adequacy = _load_json(adequacy_path)
        admission = _load_json(admission_path)
        for cert, name in ((adequacy, "ADEQUACY"), (admission, "ADMISSION")):
            if cert.get("cell_id") != row.get("cell_id"):
                raise RuntimeBindingFailClosed(f"{name}_CELL_ID_MISMATCH:{index}")
            if cert.get("route_id") != row.get("route_id"):
                raise RuntimeBindingFailClosed(f"{name}_ROUTE_ID_MISMATCH:{index}")
        if admission.get("context_digest_sha256") != row.get("context_digest"):
            raise RuntimeBindingFailClosed(f"ADMISSION_CONTEXT_DIGEST_MISMATCH:{index}")
        if admission.get("admitted") is not row.get("admitted"):
            raise RuntimeBindingFailClosed(f"ADMISSION_BOOLEAN_MISMATCH:{index}")
        if adequacy.get("creditable") is not row.get("creditable"):
            raise RuntimeBindingFailClosed(f"ADEQUACY_CREDITABLE_MISMATCH:{index}")
        if admission.get("creditable") is not row.get("creditable"):
            raise RuntimeBindingFailClosed(f"ADMISSION_CREDITABLE_MISMATCH:{index}")

        receipt = AdmissionReceipt(
            context_digest=str(row.get("context_digest") or ""),
            cell_id=str(row.get("cell_id") or ""),
            route_id=str(row.get("route_id") or ""),
            route_blob_sha=str(row.get("route_blob_sha") or ""),
            adequacy_certificate_blob_sha=str(row.get("adequacy_certificate_blob_sha") or ""),
            admission_certificate_blob_sha=str(row.get("admission_certificate_blob_sha") or ""),
            admitted=row.get("admitted"),
        )
        identity = (
            receipt.context_digest,
            receipt.cell_id,
            receipt.route_id,
            receipt.route_blob_sha,
            receipt.adequacy_certificate_blob_sha,
            receipt.admission_certificate_blob_sha,
        )
        if identity in rows_by_identity:
            raise RuntimeBindingFailClosed("DUPLICATE_RUNTIME_ROUTE_IDENTITY")
        rows_by_identity[identity] = row
        receipts.append(receipt)
    return receipts, rows_by_identity


def preflight() -> dict[str, Any]:
    try:
        registry = load_registry()
        receipts, _ = _verified_rows(registry)
        return {
            "schema": SCHEMA,
            "status": "PASS__CONTENT_ADDRESSED_RUNTIME_BINDING_VALID",
            "pass": True,
            "route_count": len(receipts),
            "selected_cover_complete": registry.get("selected_cover_complete") is True,
            "terminal_credit_delta": 0,
        }
    except (RuntimeBindingFailClosed, RouterFailClosed) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_credit_delta": 0,
        }


def dispatch(context: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_MAPPING_REQUIRED")
    actual_digest = context_digest(context)
    registry = load_registry()
    receipts, rows_by_identity = _verified_rows(registry)
    selected = select_certified_route(
        actual_context_digest=actual_digest,
        receipts=receipts,
    )
    identity = (
        selected.context_digest,
        selected.cell_id,
        selected.route_id,
        selected.route_blob_sha,
        selected.adequacy_certificate_blob_sha,
        selected.admission_certificate_blob_sha,
    )
    row = rows_by_identity.get(identity)
    if row is None:
        raise RuntimeBindingFailClosed("SELECTED_RECEIPT_WITHOUT_VERIFIED_RUNTIME_ROW")

    route_path = _canonical_path(row.get("route_path"), prefixes=("canonical/runtime/",))
    callable_name = str(row.get("callable") or "").strip()
    if not callable_name:
        raise RuntimeBindingFailClosed("ROUTE_CALLABLE_MISSING")

    module_name = "project_brain_selected_route_" + selected.route_blob_sha
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    if spec is None or spec.loader is None:
        raise RuntimeBindingFailClosed("ROUTE_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, callable_name, None)
    if not callable(fn):
        raise RuntimeBindingFailClosed("ROUTE_CALLABLE_INVALID")
    result = fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")

    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED",
        "actual_context_digest": actual_digest,
        "selected_cell_id": selected.cell_id,
        "selected_route_id": selected.route_id,
        "route_blob_sha": selected.route_blob_sha,
        "adequacy_certificate_blob_sha": selected.adequacy_certificate_blob_sha,
        "admission_certificate_blob_sha": selected.admission_certificate_blob_sha,
        "creditable": row.get("creditable") is True,
        "result": dict(result),
        "selected_cover_complete": registry.get("selected_cover_complete") is True,
        "terminal_credit_delta": 0,
        "rule": "NO_ROUTE_EXECUTION_BEFORE_CONTENT_ADDRESSED_CERTIFICATE_GATED_SELECTION",
    }
