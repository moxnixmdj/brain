"""Certificate-gated selected-route runtime entrypoint v2.

V2 preserves v1 selection mechanics and adds a mandatory content-addressed
payload-admission validator for every creditable real route. Non-creditable
deployment canaries may remain context-only.

A creditable route cannot execute until the validator attests the exact cell,
context digest, and canonical payload digest. The entrypoint recomputes all
digests itself and rejects any mismatch.
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
SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V2"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1"


class RuntimeBindingFailClosed(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _canonical_json_digest(value: Mapping[str, Any], *, label: str) -> str:
    if not isinstance(value, Mapping):
        raise RuntimeBindingFailClosed(label + "_MAPPING_REQUIRED")
    try:
        raw = json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeBindingFailClosed(label + "_NOT_CANONICAL_JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def context_digest(context: Mapping[str, Any]) -> str:
    return _canonical_json_digest(context, label="CONTEXT")


def payload_digest(payload: Mapping[str, Any]) -> str:
    return _canonical_json_digest(payload, label="PAYLOAD")


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
        raise RuntimeBindingFailClosed(
            "BOUND_JSON_INVALID:" + str(path.relative_to(ROOT))
        ) from exc
    if not isinstance(value, Mapping):
        raise RuntimeBindingFailClosed(
            "BOUND_JSON_NOT_OBJECT:" + str(path.relative_to(ROOT))
        )
    return value


def _load_callable(path: Path, callable_name: str, *, module_prefix: str):
    if not callable_name:
        raise RuntimeBindingFailClosed("CALLABLE_MISSING")
    blob = git_blob_sha(path)
    module_name = module_prefix + blob
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeBindingFailClosed("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, callable_name, None)
    if not callable(fn):
        raise RuntimeBindingFailClosed("CALLABLE_INVALID")
    return fn


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


def _verified_rows(
    registry: Mapping[str, Any],
) -> tuple[list[AdmissionReceipt], dict[tuple[str, ...], Mapping[str, Any]]]:
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
            raise RuntimeBindingFailClosed(
                f"ADMISSION_CONTEXT_DIGEST_MISMATCH:{index}"
            )
        if admission.get("admitted") is not row.get("admitted"):
            raise RuntimeBindingFailClosed(f"ADMISSION_BOOLEAN_MISMATCH:{index}")
        if adequacy.get("creditable") is not row.get("creditable"):
            raise RuntimeBindingFailClosed(f"ADEQUACY_CREDITABLE_MISMATCH:{index}")
        if admission.get("creditable") is not row.get("creditable"):
            raise RuntimeBindingFailClosed(f"ADMISSION_CREDITABLE_MISMATCH:{index}")

        if row.get("creditable") is True:
            required = (
                "payload_validator_path",
                "payload_validator_blob_sha",
                "payload_validator_callable",
            )
            if any(not row.get(k) for k in required):
                raise RuntimeBindingFailClosed(
                    f"CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING:{index}"
                )
            validator_path = _canonical_path(
                row.get("payload_validator_path"),
                prefixes=("canonical/runtime/",),
            )
            if row.get("payload_validator_blob_sha") != git_blob_sha(validator_path):
                raise RuntimeBindingFailClosed(
                    f"PAYLOAD_VALIDATOR_BLOB_DRIFT:{index}"
                )
            for key in required:
                if admission.get(key) != row.get(key):
                    raise RuntimeBindingFailClosed(
                        f"ADMISSION_PAYLOAD_VALIDATOR_BINDING_MISMATCH:{index}:{key}"
                    )

        receipt = AdmissionReceipt(
            context_digest=str(row.get("context_digest") or ""),
            cell_id=str(row.get("cell_id") or ""),
            route_id=str(row.get("route_id") or ""),
            route_blob_sha=str(row.get("route_blob_sha") or ""),
            adequacy_certificate_blob_sha=str(
                row.get("adequacy_certificate_blob_sha") or ""
            ),
            admission_certificate_blob_sha=str(
                row.get("admission_certificate_blob_sha") or ""
            ),
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


def _verify_payload_attestation(
    attestation: Mapping[str, Any],
    *,
    cell_id: str,
    actual_context_digest: str,
    actual_payload_digest: str,
) -> None:
    if not isinstance(attestation, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_NOT_MAPPING")
    if attestation.get("admitted") is not True:
        raise RuntimeBindingFailClosed("PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL")
    if attestation.get("cell_id") != cell_id:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CELL_MISMATCH")
    if attestation.get("context_digest_sha256") != actual_context_digest:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CONTEXT_MISMATCH")
    if attestation.get("payload_sha256") != actual_payload_digest:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_DIGEST_MISMATCH")


def _validate_creditable_payload(
    row: Mapping[str, Any],
    *,
    cell_id: str,
    context: Mapping[str, Any],
    payload: Mapping[str, Any],
    actual_context_digest: str,
) -> str:
    validator_path = _canonical_path(
        row.get("payload_validator_path"),
        prefixes=("canonical/runtime/",),
    )
    expected_blob = str(row.get("payload_validator_blob_sha") or "")
    actual_blob = git_blob_sha(validator_path)
    if actual_blob != expected_blob:
        raise RuntimeBindingFailClosed("PAYLOAD_VALIDATOR_BLOB_DRIFT")
    fn = _load_callable(
        validator_path,
        str(row.get("payload_validator_callable") or ""),
        module_prefix="project_brain_payload_validator_",
    )
    actual_payload_digest = payload_digest(payload)
    attestation = fn(dict(context), dict(payload))
    _verify_payload_attestation(
        attestation,
        cell_id=cell_id,
        actual_context_digest=actual_context_digest,
        actual_payload_digest=actual_payload_digest,
    )
    return actual_payload_digest


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
    actual_context_digest = context_digest(context)
    registry = load_registry()
    receipts, rows_by_identity = _verified_rows(registry)
    selected = select_certified_route(
        actual_context_digest=actual_context_digest,
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

    bound_payload_digest = None
    if row.get("creditable") is True:
        bound_payload_digest = _validate_creditable_payload(
            row,
            cell_id=selected.cell_id,
            context=context,
            payload=payload,
            actual_context_digest=actual_context_digest,
        )

    route_path = _canonical_path(row.get("route_path"), prefixes=("canonical/runtime/",))
    fn = _load_callable(
        route_path,
        str(row.get("callable") or ""),
        module_prefix="project_brain_selected_route_",
    )
    result = fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")

    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED",
        "actual_context_digest": actual_context_digest,
        "payload_sha256": bound_payload_digest,
        "selected_cell_id": selected.cell_id,
        "selected_route_id": selected.route_id,
        "route_blob_sha": selected.route_blob_sha,
        "adequacy_certificate_blob_sha": selected.adequacy_certificate_blob_sha,
        "admission_certificate_blob_sha": selected.admission_certificate_blob_sha,
        "creditable": row.get("creditable") is True,
        "result": dict(result),
        "selected_cover_complete": registry.get("selected_cover_complete") is True,
        "terminal_credit_delta": 0,
        "rule": (
            "NO_CREDITABLE_ROUTE_EXECUTION_BEFORE_CONTENT_ADDRESSED_SELECTION_"
            "AND_CONTEXT_PAYLOAD_MEMBERSHIP_ATTESTATION"
        ),
    }
