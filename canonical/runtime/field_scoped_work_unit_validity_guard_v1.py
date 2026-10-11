"""Field-scoped semantic validity guard for zero-reality work.

This is a strict sibling of work_unit_validity_guard_v2. It preserves an exact
independently verified zero-reality work product across same-file authority
churn only when:
- exact static blob dependencies remain unchanged;
- every declared RFC-6901 premise manifest remains current;
- the exact canonical verification certificate is unchanged;
- no dynamic, implicit, or external unbound dependencies remain.

It never grants execution, promotion, acceptance, capability, ownership,
fresh-reality, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from canonical.runtime.authority_epoch_guard_v1 import epoch_for_ref
from canonical.runtime.field_scoped_authority_projection_gate_v1 import (
    GateError,
    check_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_FIELD_SCOPED_WORK_UNIT_VALIDITY_GUARD_V1"
CERT_SCHEMA = "PROJECT_BRAIN_FIELD_SCOPED_WORK_UNIT_DEPENDENCY_CLOSURE_VERIFY_V1"
CERT_STATUS = "PASS__INDEPENDENTLY_VERIFIED_COMPLETE_FIELD_SCOPED_DEPENDENCY_CLOSURE"
VERIFY_SCOPE = "EXACT_WORK_PRODUCT_STATIC_BLOBS_AND_FIELD_SCOPED_AUTHORITY_PREMISES"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FieldScopedWorkUnitValidityError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise FieldScopedWorkUnitValidityError(
            "GIT_FAILED:" + " ".join(args) + ":" + proc.stderr.strip()
        )
    return proc.stdout.strip()


def _safe_repo_path(value: Any, *, verification_only: bool = False) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise FieldScopedWorkUnitValidityError("PATH_INVALID")
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(x in {"", ".", ".."} for x in p.parts):
        raise FieldScopedWorkUnitValidityError("PATH_NOT_CANONICAL_RELATIVE:" + value)
    out = p.as_posix()
    if verification_only and not (
        out.startswith("canonical/verification/") and out.endswith(".json")
    ):
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_MUST_BE_CANONICAL_VERIFICATION_JSON"
        )
    return out


def git_blob_sha(root: Path, path: str, ref: str = "HEAD") -> str:
    safe = _safe_repo_path(path)
    out = _git(root, "rev-parse", f"{ref}:{safe}")
    if SHA40_RE.fullmatch(out) is None:
        raise FieldScopedWorkUnitValidityError(
            f"INVALID_GIT_BLOB_SHA:{safe}:{out}"
        )
    return out


def _json_at_ref(root: Path, *, path: str, ref: str) -> dict[str, Any]:
    safe = _safe_repo_path(path)
    raw = _git(root, "show", f"{ref}:{safe}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FieldScopedWorkUnitValidityError(
            "SOURCE_JSON_INVALID:" + safe
        ) from exc
    if not isinstance(value, dict):
        raise FieldScopedWorkUnitValidityError("SOURCE_JSON_NOT_OBJECT:" + safe)
    return value


def _load_certificate(
    root: Path,
    *,
    path: str,
    expected_blob_sha: str,
    ref: str,
) -> dict[str, Any]:
    safe = _safe_repo_path(path, verification_only=True)
    if SHA40_RE.fullmatch(str(expected_blob_sha)) is None:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_BLOB_SHA_INVALID"
        )
    actual = git_blob_sha(root, safe, ref)
    if actual != expected_blob_sha:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_BLOB_DRIFT:"
            + str(expected_blob_sha)
            + ":"
            + actual
        )
    raw = _git(root, "show", f"{ref}:{safe}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_JSON_INVALID"
        ) from exc
    if not isinstance(value, dict):
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_NOT_OBJECT"
        )
    return value


def _component_digest(blob_map: Mapping[str, str]) -> str:
    if not isinstance(blob_map, Mapping) or not blob_map:
        raise FieldScopedWorkUnitValidityError(
            "STATIC_DEPENDENCY_SET_REQUIRED"
        )
    rows = []
    for raw_path, raw_sha in sorted(blob_map.items()):
        path = _safe_repo_path(str(raw_path))
        sha = str(raw_sha)
        if SHA40_RE.fullmatch(sha) is None:
            raise FieldScopedWorkUnitValidityError(
                "STATIC_DEPENDENCY_SHA_INVALID:" + path
            )
        rows.append(path + "=" + sha + "\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def _normalize_static_dependencies(
    value: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise FieldScopedWorkUnitValidityError(
            "STATIC_DEPENDENCIES_REQUIRED"
        )
    out = {
        _safe_repo_path(str(path)): str(sha)
        for path, sha in value.items()
    }
    _component_digest(out)
    return dict(sorted(out.items()))


def _normalize_field_manifests(
    value: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or not value
    ):
        raise FieldScopedWorkUnitValidityError(
            "FIELD_DEPENDENCY_MANIFESTS_REQUIRED"
        )
    out = []
    seen: set[str] = set()
    for i, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise FieldScopedWorkUnitValidityError(
                f"FIELD_DEPENDENCY_ROW_INVALID:{i}"
            )
        path = _safe_repo_path(row.get("source_path"))
        if path in seen:
            raise FieldScopedWorkUnitValidityError(
                "DUPLICATE_FIELD_SOURCE_PATH:" + path
            )
        seen.add(path)
        manifest = row.get("manifest")
        if not isinstance(manifest, Mapping):
            raise FieldScopedWorkUnitValidityError(
                "FIELD_MANIFEST_REQUIRED:" + path
            )
        if manifest.get("source_path") != path:
            raise FieldScopedWorkUnitValidityError(
                "FIELD_MANIFEST_SOURCE_PATH_MISMATCH:" + path
            )
        manifest_sha = manifest.get("manifest_sha256")
        projection_sha = manifest.get("projection_sha256")
        if (
            not isinstance(manifest_sha, str)
            or SHA256_RE.fullmatch(manifest_sha) is None
            or not isinstance(projection_sha, str)
            or SHA256_RE.fullmatch(projection_sha) is None
        ):
            raise FieldScopedWorkUnitValidityError(
                "FIELD_MANIFEST_DIGEST_INVALID:" + path
            )
        out.append({"source_path": path, "manifest": dict(manifest)})
    return sorted(out, key=lambda x: x["source_path"])


def validate_certificate(
    certificate: Mapping[str, Any],
    *,
    expected_work_product: Mapping[str, str],
    expected_static_dependencies: Mapping[str, str],
    expected_field_manifests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        raise FieldScopedWorkUnitValidityError("CLOSURE_CERTIFICATE_REQUIRED")
    if certificate.get("schema") != CERT_SCHEMA:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_SCHEMA_INVALID"
        )
    if certificate.get("status") != CERT_STATUS:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_STATUS_NOT_PASS"
        )
    if certificate.get("independent_verified") is not True:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_NOT_INDEPENDENT"
        )
    if certificate.get("dependency_closure_complete") is not True:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_NOT_COMPLETE"
        )
    if certificate.get("verification_scope") != VERIFY_SCOPE:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_SCOPE_INVALID"
        )
    if certificate.get("external_unbound_dependencies") != []:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_EXTERNAL_DEPENDENCIES_OPEN"
        )
    if certificate.get("dynamic_or_implicit_dependencies") != []:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_DYNAMIC_DEPENDENCIES_OPEN"
        )

    cert_product = certificate.get("work_product")
    if not isinstance(cert_product, Mapping):
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_WORK_PRODUCT_MISSING"
        )
    product = {
        "path": _safe_repo_path(cert_product.get("path")),
        "git_blob_sha": str(cert_product.get("git_blob_sha") or ""),
    }
    expected_product = {
        "path": _safe_repo_path(expected_work_product.get("path")),
        "git_blob_sha": str(expected_work_product.get("git_blob_sha") or ""),
    }
    if (
        SHA40_RE.fullmatch(product["git_blob_sha"]) is None
        or SHA40_RE.fullmatch(expected_product["git_blob_sha"]) is None
        or product != expected_product
    ):
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_WORK_PRODUCT_MISMATCH"
        )

    cert_static = _normalize_static_dependencies(
        certificate.get("static_dependencies")
    )
    expected_static = _normalize_static_dependencies(
        expected_static_dependencies
    )
    if cert_static != expected_static:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_STATIC_DEPENDENCY_SET_MISMATCH"
        )
    static_digest = _component_digest(cert_static)
    if certificate.get("static_dependency_digest_sha256") != static_digest:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_STATIC_DEPENDENCY_DIGEST_MISMATCH"
        )

    cert_fields = _normalize_field_manifests(
        certificate.get("field_dependency_manifests")
    )
    expected_fields = _normalize_field_manifests(expected_field_manifests)
    if cert_fields != expected_fields:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_FIELD_MANIFEST_SET_MISMATCH"
        )

    verifier = certificate.get("independent_verifier")
    if not isinstance(verifier, Mapping):
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_VERIFIER_MISSING"
        )
    if verifier.get("independent_or_objective") is not True:
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_VERIFIER_NOT_INDEPENDENT_OR_OBJECTIVE"
        )
    method = verifier.get("method")
    if not isinstance(method, str) or not method.strip():
        raise FieldScopedWorkUnitValidityError(
            "CLOSURE_CERTIFICATE_VERIFIER_METHOD_MISSING"
        )

    return {
        "certificate_valid": True,
        "work_product": expected_product,
        "static_dependencies": expected_static,
        "static_dependency_digest_sha256": static_digest,
        "field_dependency_manifests": expected_fields,
        "independent_verifier_method": method.strip(),
    }


def evaluate_currentness(
    *,
    expected_work_product_sha: str,
    current_work_product_sha: str,
    expected_static_dependencies: Mapping[str, str],
    current_static_dependencies: Mapping[str, str],
    field_manifest_checks: Sequence[Mapping[str, Any]],
    expected_scheduler_epoch_sha256: str,
    current_scheduler_epoch_sha256: str,
    certificate_verified: bool,
) -> dict[str, Any]:
    if (
        SHA40_RE.fullmatch(str(expected_work_product_sha)) is None
        or SHA40_RE.fullmatch(str(current_work_product_sha)) is None
    ):
        raise FieldScopedWorkUnitValidityError(
            "WORK_PRODUCT_SHA_INVALID"
        )
    if not certificate_verified:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__DEPENDENCY_CLOSURE_UNVERIFIED",
            "pass": False,
            "semantic_valid": False,
            "semantic_reuse_allowed": False,
            "scheduler_current": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "terminal_credit_delta": 0,
        }

    expected_static = _normalize_static_dependencies(
        expected_static_dependencies
    )
    current_static = _normalize_static_dependencies(
        current_static_dependencies
    )
    product_unchanged = expected_work_product_sha == current_work_product_sha
    static_unchanged = expected_static == current_static
    field_rows = list(field_manifest_checks)
    fields_current = bool(field_rows) and all(
        isinstance(row, Mapping) and row.get("stale") is False
        for row in field_rows
    )
    semantic_valid = (
        product_unchanged and static_unchanged and fields_current
    )
    scheduler_current = bool(expected_scheduler_epoch_sha256) and (
        expected_scheduler_epoch_sha256 == current_scheduler_epoch_sha256
    )

    if not semantic_valid:
        status = "FAIL_CLOSED__FIELD_SCOPED_SEMANTIC_DEPENDENCY_DRIFT"
        reuse = False
    elif scheduler_current:
        status = "PASS__FIELD_SCOPED_SEMANTIC_AND_SCHEDULER_CURRENT"
        reuse = True
    else:
        status = (
            "PASS__FIELD_SCOPED_SEMANTIC_RESULT_REUSABLE__"
            "SCHEDULER_REPLAN_REQUIRED"
        )
        reuse = True

    return {
        "schema": SCHEMA,
        "pass": semantic_valid,
        "status": status,
        "semantic_valid": semantic_valid,
        "semantic_reuse_allowed": reuse,
        "work_product_unchanged": product_unchanged,
        "static_dependencies_unchanged": static_unchanged,
        "field_dependency_manifests_current": fields_current,
        "field_dependency_manifest_count": len(field_rows),
        "scheduler_current": scheduler_current,
        "fresh_reality_gate_current": False,
        "rule": (
            "FIELD_SCOPED_REUSE_IS_ONLY_FOR_EXACT_INDEPENDENTLY_VERIFIED_"
            "ZERO_REALITY_WORK_PRODUCTS__STATIC_BLOBS_AND_DECLARED_FIELD_"
            "PREMISES_MUST_REMAIN_CURRENT__CONSEQUENTIAL_AUTHORITY_REQUIRES_"
            "SEPARATE_LIVE_GLOBAL_AUTHORITY"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def verify_lease(
    lease: Mapping[str, Any],
    *,
    root: str | Path = ROOT,
    ref: str = "HEAD",
) -> dict[str, Any]:
    repo_root = Path(root).resolve()

    if str(lease.get("work_class") or "") != "ZERO_REALITY_DERIVATION":
        raise FieldScopedWorkUnitValidityError(
            "FIELD_SCOPED_ROUTE_ONLY_SUPPORTS_ZERO_REALITY_DERIVATION"
        )

    product = lease.get("work_product")
    if not isinstance(product, Mapping):
        raise FieldScopedWorkUnitValidityError("LEASE_WORK_PRODUCT_MISSING")
    work_product = {
        "path": _safe_repo_path(product.get("path")),
        "git_blob_sha": str(product.get("git_blob_sha") or ""),
    }
    if SHA40_RE.fullmatch(work_product["git_blob_sha"]) is None:
        raise FieldScopedWorkUnitValidityError(
            "LEASE_WORK_PRODUCT_SHA_INVALID"
        )

    static_dependencies = _normalize_static_dependencies(
        lease.get("static_dependencies")
    )
    field_manifests = _normalize_field_manifests(
        lease.get("field_dependency_manifests")
    )

    closure = lease.get("dependency_closure")
    if not isinstance(closure, Mapping):
        raise FieldScopedWorkUnitValidityError(
            "LEASE_DEPENDENCY_CLOSURE_MISSING"
        )
    closure_path = _safe_repo_path(
        closure.get("certificate_path"),
        verification_only=True,
    )
    closure_sha = str(closure.get("git_blob_sha") or "")
    certificate = _load_certificate(
        repo_root,
        path=closure_path,
        expected_blob_sha=closure_sha,
        ref=ref,
    )
    cert = validate_certificate(
        certificate,
        expected_work_product=work_product,
        expected_static_dependencies=static_dependencies,
        expected_field_manifests=field_manifests,
    )

    scheduler = lease.get("scheduler")
    if not isinstance(scheduler, Mapping):
        raise FieldScopedWorkUnitValidityError("LEASE_SCHEDULER_MISSING")
    expected_scheduler = str(
        scheduler.get("authority_epoch_sha256") or ""
    )
    if SHA256_RE.fullmatch(expected_scheduler) is None:
        raise FieldScopedWorkUnitValidityError(
            "LEASE_SCHEDULER_EPOCH_INVALID"
        )

    current_static = {
        path: git_blob_sha(repo_root, path, ref)
        for path in sorted(static_dependencies)
    }
    current_product_sha = git_blob_sha(
        repo_root,
        work_product["path"],
        ref,
    )

    field_checks = []
    for row in field_manifests:
        doc = _json_at_ref(
            repo_root,
            path=row["source_path"],
            ref=ref,
        )
        try:
            checked = check_manifest(doc, row["manifest"])
        except GateError as exc:
            raise FieldScopedWorkUnitValidityError(
                "FIELD_MANIFEST_CHECK_FAILED:"
                + row["source_path"]
                + ":"
                + str(exc)
            ) from exc
        field_checks.append(
            {
                "source_path": row["source_path"],
                **checked,
            }
        )

    current_scheduler = epoch_for_ref(ref)["epoch_sha256"]
    out = evaluate_currentness(
        expected_work_product_sha=work_product["git_blob_sha"],
        current_work_product_sha=current_product_sha,
        expected_static_dependencies=static_dependencies,
        current_static_dependencies=current_static,
        field_manifest_checks=field_checks,
        expected_scheduler_epoch_sha256=expected_scheduler,
        current_scheduler_epoch_sha256=current_scheduler,
        certificate_verified=cert["certificate_valid"],
    )
    out.update(
        {
            "ref": ref,
            "work_product": work_product,
            "dependency_closure_certificate": closure_path,
            "dependency_closure_git_blob_sha": closure_sha,
            "independent_verifier_method": cert[
                "independent_verifier_method"
            ],
            "current_scheduler_epoch_sha256": current_scheduler,
            "expected_scheduler_epoch_sha256": expected_scheduler,
            "field_manifest_checks": field_checks,
        }
    )
    return out
