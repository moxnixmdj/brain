"""Fail-closed executable-refinement gate for creditable selected routes."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.executable_refinement_verifier_v1 import verify_certificate


class RefinementGateFailClosed(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _path(root: Path, raw: Any, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts or not any(value.startswith(x) for x in prefixes):
        raise RefinementGateFailClosed("NONCANONICAL_REFINEMENT_PATH")
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise RefinementGateFailClosed("REFINEMENT_PATH_OUTSIDE_REPO") from exc
    if not full.is_file():
        raise RefinementGateFailClosed("REFINEMENT_BOUND_FILE_MISSING:" + value)
    return full


def verify_creditable_refinement_binding(
    row: Mapping[str, Any], *, repo_root: Path
) -> Mapping[str, Any]:
    required = (
        "route_path",
        "route_blob_sha",
        "refinement_certificate_path",
        "refinement_certificate_blob_sha",
    )
    if any(not row.get(k) for k in required):
        raise RefinementGateFailClosed("CREDITABLE_REFINEMENT_BINDING_MISSING")
    route_path = _path(repo_root, row.get("route_path"), ("canonical/runtime/",))
    if row.get("route_blob_sha") != git_blob_sha(route_path):
        raise RefinementGateFailClosed("REFINEMENT_SUBJECT_ROUTE_BLOB_DRIFT")
    cert_path = _path(
        repo_root,
        row.get("refinement_certificate_path"),
        ("canonical/governance/", "canonical/verification/"),
    )
    if row.get("refinement_certificate_blob_sha") != git_blob_sha(cert_path):
        raise RefinementGateFailClosed("REFINEMENT_CERTIFICATE_BLOB_DRIFT")
    try:
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RefinementGateFailClosed("REFINEMENT_CERTIFICATE_JSON_INVALID") from exc
    if not isinstance(cert, Mapping):
        raise RefinementGateFailClosed("REFINEMENT_CERTIFICATE_NOT_OBJECT")
    receipt = verify_certificate(cert, repo_root=repo_root)
    if receipt.get("pass") is not True:
        raise RefinementGateFailClosed("REFINEMENT_CERTIFICATE_INVALID")
    if receipt.get("refinement_verified") is not True:
        raise RefinementGateFailClosed("REFINEMENT_NOT_MECHANICALLY_VERIFIED")
    bound = receipt.get("concrete_implementation")
    if not isinstance(bound, list) or not any(
        isinstance(x, Mapping)
        and x.get("path") == row.get("route_path")
        and x.get("git_blob_sha") == row.get("route_blob_sha")
        for x in bound
    ):
        raise RefinementGateFailClosed("REFINEMENT_SUBJECT_ROUTE_MISMATCH")
    if row.get("refinement_liveness_required") is True and receipt.get("liveness_refinement_verified") is not True:
        raise RefinementGateFailClosed("REFINEMENT_LIVENESS_REQUIRED_BUT_UNPROVED")
    return receipt
