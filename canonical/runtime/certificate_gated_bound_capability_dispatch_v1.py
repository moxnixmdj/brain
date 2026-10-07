from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt,
    RouterFailClosed,
    select_certified_route,
)

ADMISSION_SCHEMA = "PROJECT_BRAIN_SELECTED_ROUTE_ADMISSION_CERTIFICATE_V1"
VERIFICATION_SCHEMA = "PROJECT_BRAIN_SELECTED_ROUTE_ADMISSION_INDEPENDENT_VERIFICATION_V1"


class CertifiedRouteBindingError(RuntimeError):
    pass


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except Exception as exc:
        raise CertifiedRouteBindingError(
            "ACTUAL_CONTEXT_NOT_CANONICAL_JSON:" + type(exc).__name__
        ) from exc


def context_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def git_blob_sha_bytes(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def _safe_file(root: pathlib.Path, raw_path: Any) -> tuple[pathlib.Path, str]:
    rel = str(raw_path or "").replace("\\", "/").strip()
    pure = pathlib.PurePosixPath(rel)
    if not rel or pure.is_absolute() or ".." in pure.parts:
        raise CertifiedRouteBindingError("CERTIFICATE_PATH_INVALID")
    root = root.resolve()
    path = (root / pathlib.Path(*pure.parts)).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CertifiedRouteBindingError("CERTIFICATE_PATH_OUTSIDE_ROOT") from exc
    if not path.is_file():
        raise CertifiedRouteBindingError("CERTIFICATE_PATH_MISSING:" + rel)
    return path, pure.as_posix()


def _read_json_file(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CertifiedRouteBindingError(
            label + "_JSON_INVALID:" + type(exc).__name__
        ) from exc
    if not isinstance(value, dict):
        raise CertifiedRouteBindingError(label + "_NOT_OBJECT")
    return value


def _route_path(root: pathlib.Path, route_id: str, registry: Mapping[str, Any]) -> tuple[pathlib.Path, str]:
    entry = registry.get(route_id)
    if not isinstance(entry, dict):
        raise CertifiedRouteBindingError("ROUTE_NOT_IN_BOUND_CAPABILITY_REGISTRY:" + route_id)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise CertifiedRouteBindingError("ROUTE_NOT_VERIFIED_BOUND_CAPABILITY:" + route_id)
    source = entry.get("source") or {}
    if str(source.get("type") or "") == "runtime_native":
        raise CertifiedRouteBindingError("RUNTIME_NATIVE_ROUTE_NOT_SUPPORTED_BY_BOUND_DISPATCH:" + route_id)

    raw = str(source.get("adapter_path") or "").strip()
    if not raw:
        module = str(entry.get("adapter_module") or "").strip()
        if not module or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
            for ch in module
        ):
            raise CertifiedRouteBindingError("ROUTE_ADAPTER_MODULE_INVALID:" + route_id)
        raw = "canonical/runtime/bound_capabilities/" + module + ".py"

    path, rel = _safe_file(root, raw)
    return path, rel


def _require_sha40(label: str, value: Any) -> str:
    raw = str(value or "").lower()
    if len(raw) != 40 or any(c not in "0123456789abcdef" for c in raw):
        raise CertifiedRouteBindingError(label + "_INVALID")
    return raw


def _load_receipt(
    *,
    root: pathlib.Path,
    certificate_path: Any,
    actual_context_digest: str,
    registry: Mapping[str, Any],
) -> tuple[AdmissionReceipt, dict[str, Any]]:
    admission_path, admission_rel = _safe_file(root, certificate_path)
    admission_raw = admission_path.read_bytes()
    admission_blob_sha = git_blob_sha_bytes(admission_raw)
    admission = _read_json_file(admission_path, "ADMISSION_CERTIFICATE")

    if admission.get("schema") != ADMISSION_SCHEMA:
        raise CertifiedRouteBindingError("ADMISSION_CERTIFICATE_SCHEMA_INVALID:" + admission_rel)
    if admission.get("pass") is not True:
        raise CertifiedRouteBindingError("ADMISSION_CERTIFICATE_NOT_PASS:" + admission_rel)

    cert_context = str(admission.get("context_digest") or "")
    if cert_context != actual_context_digest:
        raise CertifiedRouteBindingError("ADMISSION_CONTEXT_DIGEST_MISMATCH:" + admission_rel)

    cell_id = str(admission.get("cell_id") or "").strip()
    route_id = str(admission.get("route_id") or "").strip()
    if not cell_id or not route_id:
        raise CertifiedRouteBindingError("ADMISSION_IDENTITY_INCOMPLETE:" + admission_rel)

    route_path, route_rel = _route_path(root, route_id, registry)
    actual_route_blob_sha = git_blob_sha_bytes(route_path.read_bytes())
    expected_route_blob_sha = _require_sha40(
        "ADMISSION_ROUTE_BLOB_SHA", admission.get("route_blob_sha")
    )
    if actual_route_blob_sha != expected_route_blob_sha:
        raise CertifiedRouteBindingError("ROUTE_BLOB_SHA_MISMATCH:" + route_id)

    adequacy_path, adequacy_rel = _safe_file(root, admission.get("adequacy_certificate_path"))
    actual_adequacy_blob_sha = git_blob_sha_bytes(adequacy_path.read_bytes())
    expected_adequacy_blob_sha = _require_sha40(
        "ADEQUACY_CERTIFICATE_BLOB_SHA",
        admission.get("adequacy_certificate_blob_sha"),
    )
    if actual_adequacy_blob_sha != expected_adequacy_blob_sha:
        raise CertifiedRouteBindingError("ADEQUACY_CERTIFICATE_BLOB_SHA_MISMATCH:" + route_id)

    verification_path, verification_rel = _safe_file(
        root, admission.get("independent_verification_path")
    )
    verification = _read_json_file(
        verification_path, "ADMISSION_INDEPENDENT_VERIFICATION"
    )
    if verification.get("schema") != VERIFICATION_SCHEMA:
        raise CertifiedRouteBindingError(
            "ADMISSION_INDEPENDENT_VERIFICATION_SCHEMA_INVALID:" + verification_rel
        )
    if verification.get("pass") is not True:
        raise CertifiedRouteBindingError(
            "ADMISSION_INDEPENDENT_VERIFICATION_NOT_PASS:" + verification_rel
        )

    expected_binding = {
        "subject_path": admission_rel,
        "subject_git_blob_sha": admission_blob_sha,
        "context_digest": actual_context_digest,
        "cell_id": cell_id,
        "route_id": route_id,
        "route_path": route_rel,
        "route_blob_sha": actual_route_blob_sha,
        "adequacy_certificate_path": adequacy_rel,
        "adequacy_certificate_blob_sha": actual_adequacy_blob_sha,
    }
    for key, expected in expected_binding.items():
        if verification.get(key) != expected:
            raise CertifiedRouteBindingError(
                "ADMISSION_INDEPENDENT_VERIFICATION_BINDING_MISMATCH:"
                + key
                + ":"
                + verification_rel
            )

    receipt = AdmissionReceipt(
        context_digest=actual_context_digest,
        cell_id=cell_id,
        route_id=route_id,
        route_blob_sha=actual_route_blob_sha,
        adequacy_certificate_blob_sha=actual_adequacy_blob_sha,
        admission_certificate_blob_sha=admission_blob_sha,
        admitted=True,
    )
    metadata = {
        "admission_certificate_path": admission_rel,
        "admission_certificate_blob_sha": admission_blob_sha,
        "independent_verification_path": verification_rel,
        "route_path": route_rel,
        "adequacy_certificate_path": adequacy_rel,
    }
    return receipt, metadata


def resolve_dispatch(
    *,
    root: pathlib.Path,
    args: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise CertifiedRouteBindingError("CERTIFIED_ROUTE_ARGS_INVALID")
    allowed = {"context", "admission_certificate_paths", "route_args_by_id"}
    unknown = sorted(str(k) for k in args if str(k) not in allowed)
    if unknown:
        raise CertifiedRouteBindingError(
            "CERTIFIED_ROUTE_TOP_LEVEL_FIELD_REJECTED:" + ",".join(unknown)
        )

    actual_context = args.get("context")
    digest = context_digest(actual_context)

    paths = args.get("admission_certificate_paths")
    if (
        not isinstance(paths, list)
        or not paths
        or len(paths) > 128
        or any(not isinstance(x, str) or not x.strip() for x in paths)
    ):
        raise CertifiedRouteBindingError("ADMISSION_CERTIFICATE_PATHS_INVALID")
    if len(paths) != len(set(paths)):
        raise CertifiedRouteBindingError("ADMISSION_CERTIFICATE_PATH_DUPLICATE")

    route_args_by_id = args.get("route_args_by_id")
    if not isinstance(route_args_by_id, dict) or not route_args_by_id:
        raise CertifiedRouteBindingError("ROUTE_ARGS_BY_ID_INVALID")
    if any(not isinstance(k, str) or not k.strip() for k in route_args_by_id):
        raise CertifiedRouteBindingError("ROUTE_ARGS_ROUTE_ID_INVALID")
    if any(not isinstance(v, dict) for v in route_args_by_id.values()):
        raise CertifiedRouteBindingError("ROUTE_ARGS_VALUE_INVALID")

    receipts: list[AdmissionReceipt] = []
    metadata_by_admission_sha: dict[str, dict[str, Any]] = {}
    for path in paths:
        receipt, metadata = _load_receipt(
            root=root,
            certificate_path=path,
            actual_context_digest=digest,
            registry=registry,
        )
        receipts.append(receipt)
        metadata_by_admission_sha[receipt.admission_certificate_blob_sha] = metadata

    try:
        selected = select_certified_route(
            actual_context_digest=digest,
            receipts=receipts,
        )
    except RouterFailClosed as exc:
        raise CertifiedRouteBindingError(
            "CERTIFICATE_GATED_ROUTER_FAIL_CLOSED:" + str(exc)
        ) from exc

    route_args = route_args_by_id.get(selected.route_id)
    if not isinstance(route_args, dict):
        raise CertifiedRouteBindingError(
            "SELECTED_ROUTE_ARGS_MISSING:" + selected.route_id
        )
    if "capability_id" in route_args:
        raise CertifiedRouteBindingError(
            "SELECTED_ROUTE_ARGS_MUST_NOT_OVERRIDE_CAPABILITY_ID"
        )

    metadata = metadata_by_admission_sha[selected.admission_certificate_blob_sha]
    return {
        "schema": "PROJECT_BRAIN_CERTIFICATE_GATED_BOUND_CAPABILITY_DISPATCH_V1",
        "status": "PASS__CERTIFICATE_GATED_ROUTE_SELECTED_AND_CONTENT_BOUND",
        "actual_context_digest": digest,
        "cell_id": selected.cell_id,
        "route_id": selected.route_id,
        "route_blob_sha": selected.route_blob_sha,
        "adequacy_certificate_blob_sha": selected.adequacy_certificate_blob_sha,
        "admission_certificate_blob_sha": selected.admission_certificate_blob_sha,
        "admission_certificate_path": metadata["admission_certificate_path"],
        "independent_verification_path": metadata["independent_verification_path"],
        "route_path": metadata["route_path"],
        "adequacy_certificate_path": metadata["adequacy_certificate_path"],
        "route_args": dict(route_args),
    }
