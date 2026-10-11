"""Two-clock semantic validity guard V2 for Project Brain.

Separates:
1) semantic validity of an exact zero-reality work product, from
2) live scheduler / execution authority.

Semantic reuse is allowed across scheduler churn only when a canonical
verification receipt independently binds the exact work product and a complete,
content-addressed semantic dependency cone with no open dynamic/external
dependencies.

This module never grants execution, promotion, acceptance, capability,
ownership, or fresh-reality authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from canonical.runtime.authority_epoch_guard_v1 import epoch_for_ref

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TWO_CLOCK_WORK_UNIT_VALIDITY_GUARD_V2"
CERT_SCHEMA = "PROJECT_BRAIN_WORK_UNIT_DEPENDENCY_CLOSURE_VERIFY_V1"
CERT_STATUS = "PASS__INDEPENDENTLY_VERIFIED_COMPLETE_DEPENDENCY_CLOSURE"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class WorkUnitValidityError(RuntimeError):
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
        raise WorkUnitValidityError(
            "GIT_FAILED:" + " ".join(args) + ":" + proc.stderr.strip()
        )
    return proc.stdout.strip()


def _safe_repo_path(value: Any, *, verification_only: bool = False) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise WorkUnitValidityError("PATH_INVALID")
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(x in {"", ".", ".."} for x in p.parts):
        raise WorkUnitValidityError("PATH_NOT_CANONICAL_RELATIVE:" + value)
    out = p.as_posix()
    if verification_only and not (
        out.startswith("canonical/verification/") and out.endswith(".json")
    ):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_MUST_BE_CANONICAL_VERIFICATION_JSON")
    return out


def git_blob_sha(root: Path, path: str, ref: str = "HEAD") -> str:
    safe = _safe_repo_path(path)
    out = _git(root, "rev-parse", f"{ref}:{safe}")
    if not SHA40_RE.fullmatch(out):
        raise WorkUnitValidityError(f"INVALID_GIT_BLOB_SHA:{safe}:{out}")
    return out


def compute_component_digest(blob_map: Mapping[str, str]) -> str:
    if not isinstance(blob_map, Mapping) or not blob_map:
        raise WorkUnitValidityError("EMPTY_SEMANTIC_DEPENDENCY_SET")
    lines: list[str] = []
    for path, sha in sorted((str(k), str(v)) for k, v in blob_map.items()):
        safe = _safe_repo_path(path)
        if not SHA40_RE.fullmatch(sha):
            raise WorkUnitValidityError(f"INVALID_SEMANTIC_COMPONENT:{safe}:{sha}")
        lines.append(f"{safe}={sha}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def current_semantic_components(
    root: Path,
    expected_components: Mapping[str, str],
    ref: str = "HEAD",
) -> dict[str, str]:
    if not expected_components:
        raise WorkUnitValidityError("EMPTY_SEMANTIC_DEPENDENCY_SET")
    return {
        path: git_blob_sha(root, path, ref)
        for path in sorted(str(x) for x in expected_components)
    }


def _load_json_at_ref(
    root: Path,
    *,
    ref: str,
    path: str,
    expected_blob_sha: str,
) -> dict[str, Any]:
    safe = _safe_repo_path(path, verification_only=True)
    if not SHA40_RE.fullmatch(str(expected_blob_sha)):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_BLOB_SHA_INVALID")
    actual = git_blob_sha(root, safe, ref)
    if actual != expected_blob_sha:
        raise WorkUnitValidityError(
            f"CLOSURE_CERTIFICATE_BLOB_DRIFT:{expected_blob_sha}:{actual}"
        )
    raw = _git(root, "show", f"{ref}:{safe}")
    try:
        doc = json.loads(raw)
    except Exception as exc:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_JSON_INVALID") from exc
    if not isinstance(doc, dict):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_NOT_OBJECT")
    return doc


def validate_dependency_closure_certificate(
    certificate: Mapping[str, Any],
    *,
    expected_work_product: Mapping[str, str],
    expected_semantic_dependencies: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_REQUIRED")
    if certificate.get("schema") != CERT_SCHEMA:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("status") != CERT_STATUS:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_STATUS_NOT_PASS")
    if certificate.get("independent_verified") is not True:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_NOT_INDEPENDENT")
    if certificate.get("dependency_closure_complete") is not True:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_NOT_COMPLETE")
    if certificate.get("verification_scope") != (
        "EXACT_WORK_PRODUCT_TRANSITIVE_SEMANTIC_DEPENDENCY_CONE"
    ):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_SCOPE_INVALID")

    external = certificate.get("external_unbound_dependencies")
    dynamic = certificate.get("dynamic_or_implicit_dependencies")
    if external != []:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_EXTERNAL_DEPENDENCIES_OPEN")
    if dynamic != []:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_DYNAMIC_DEPENDENCIES_OPEN")

    cert_product = certificate.get("work_product")
    if not isinstance(cert_product, Mapping):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_WORK_PRODUCT_MISSING")
    normalized_product = {
        "path": _safe_repo_path(cert_product.get("path")),
        "git_blob_sha": str(cert_product.get("git_blob_sha") or ""),
    }
    if not SHA40_RE.fullmatch(normalized_product["git_blob_sha"]):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_WORK_PRODUCT_SHA_INVALID")

    expected_product = {
        "path": _safe_repo_path(expected_work_product.get("path")),
        "git_blob_sha": str(expected_work_product.get("git_blob_sha") or ""),
    }
    if not SHA40_RE.fullmatch(expected_product["git_blob_sha"]):
        raise WorkUnitValidityError("LEASE_WORK_PRODUCT_SHA_INVALID")
    if normalized_product != expected_product:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_WORK_PRODUCT_MISMATCH")

    cert_deps = certificate.get("semantic_dependencies")
    if not isinstance(cert_deps, Mapping):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_DEPENDENCIES_MISSING")
    normalized_deps = {
        _safe_repo_path(str(k)): str(v)
        for k, v in cert_deps.items()
    }
    expected_deps = {
        _safe_repo_path(str(k)): str(v)
        for k, v in expected_semantic_dependencies.items()
    }
    for path, sha in normalized_deps.items():
        if not SHA40_RE.fullmatch(sha):
            raise WorkUnitValidityError(
                f"CLOSURE_CERTIFICATE_DEPENDENCY_SHA_INVALID:{path}"
            )
    for path, sha in expected_deps.items():
        if not SHA40_RE.fullmatch(sha):
            raise WorkUnitValidityError(
                f"LEASE_SEMANTIC_DEPENDENCY_SHA_INVALID:{path}"
            )
    if normalized_deps != expected_deps:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_DEPENDENCY_SET_MISMATCH")

    digest = compute_component_digest(normalized_deps)
    if certificate.get("semantic_dependency_digest_sha256") != digest:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_DEPENDENCY_DIGEST_MISMATCH")

    verifier = certificate.get("independent_verifier")
    if not isinstance(verifier, Mapping):
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_VERIFIER_MISSING")
    if verifier.get("independent_or_objective") is not True:
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_VERIFIER_NOT_INDEPENDENT_OR_OBJECTIVE")
    method = verifier.get("method")
    if not isinstance(method, str) or not method.strip():
        raise WorkUnitValidityError("CLOSURE_CERTIFICATE_VERIFIER_METHOD_MISSING")

    return {
        "certificate_valid": True,
        "work_product": expected_product,
        "semantic_dependencies": expected_deps,
        "semantic_dependency_digest_sha256": digest,
        "independent_verifier_method": method.strip(),
    }


def evaluate_two_clock_lease(
    *,
    expected_work_product_sha: str,
    current_work_product_sha: str,
    expected_semantic_components: Mapping[str, str],
    current_semantic_components_map: Mapping[str, str],
    expected_scheduler_epoch_sha256: str,
    current_scheduler_epoch_sha256: str,
    dependency_closure_verified: bool,
    work_class: str,
) -> dict[str, Any]:
    if work_class not in {"ZERO_REALITY_DERIVATION", "FRESH_REALITY_ACTION"}:
        raise WorkUnitValidityError(f"INVALID_WORK_CLASS:{work_class}")
    if not SHA40_RE.fullmatch(str(expected_work_product_sha)):
        raise WorkUnitValidityError("EXPECTED_WORK_PRODUCT_SHA_INVALID")
    if not SHA40_RE.fullmatch(str(current_work_product_sha)):
        raise WorkUnitValidityError("CURRENT_WORK_PRODUCT_SHA_INVALID")

    if not dependency_closure_verified:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__DEPENDENCY_CLOSURE_UNVERIFIED",
            "semantic_valid": False,
            "semantic_reuse_allowed": False,
            "scheduler_current": False,
            "fresh_reality_gate_current": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    expected_digest = compute_component_digest(expected_semantic_components)
    current_digest = compute_component_digest(current_semantic_components_map)
    product_unchanged = expected_work_product_sha == current_work_product_sha
    semantic_valid = (
        product_unchanged
        and dict(expected_semantic_components) == dict(current_semantic_components_map)
        and expected_digest == current_digest
    )
    scheduler_current = bool(expected_scheduler_epoch_sha256) and (
        expected_scheduler_epoch_sha256 == current_scheduler_epoch_sha256
    )

    if not semantic_valid:
        status = "FAIL_CLOSED__SEMANTIC_DEPENDENCY_OR_WORK_PRODUCT_DRIFT"
        reuse = False
    elif scheduler_current:
        status = "PASS__SEMANTIC_AND_SCHEDULER_CURRENT"
        reuse = True
    elif work_class == "ZERO_REALITY_DERIVATION":
        status = "PASS__SEMANTIC_RESULT_REUSABLE__SCHEDULER_REPLAN_REQUIRED"
        reuse = True
    else:
        status = "FAIL_CLOSED__SCHEDULER_STALE_FOR_FRESH_REALITY"
        reuse = True

    return {
        "schema": SCHEMA,
        "status": status,
        "work_class": work_class,
        "work_product_unchanged": product_unchanged,
        "semantic_valid": semantic_valid,
        "semantic_reuse_allowed": reuse,
        "semantic_dependency_digest_expected": expected_digest,
        "semantic_dependency_digest_current": current_digest,
        "scheduler_current": scheduler_current,
        "fresh_reality_gate_current": semantic_valid and scheduler_current,
        "rule": (
            "SEMANTIC_VALIDITY_DEPENDS_ON_EXACT_WORK_PRODUCT_AND_INDEPENDENTLY_"
            "VERIFIED_COMPLETE_TRANSITIVE_DEPENDENCY_CONE__SCHEDULER_CHURN_MAY_"
            "REPLAN_BUT_NOT_ERASE_UNCHANGED_ZERO_REALITY_TRUTH__FRESH_REALITY_"
            "OR_PROMOTION_STILL_REQUIRES_CURRENT_GLOBAL_AUTHORITY"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def load_lease(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkUnitValidityError(f"INVALID_LEASE:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise WorkUnitValidityError("LEASE_NOT_JSON_OBJECT")
    return value


def verify_lease(
    lease: Mapping[str, Any],
    *,
    root: str | Path = ROOT,
    ref: str = "HEAD",
) -> dict[str, Any]:
    repo_root = Path(root).resolve()

    expected = lease.get("semantic_dependencies")
    if not isinstance(expected, Mapping) or not expected:
        raise WorkUnitValidityError("LEASE_SEMANTIC_DEPENDENCIES_MISSING")
    expected_map = {
        _safe_repo_path(str(k)): str(v)
        for k, v in expected.items()
    }

    product = lease.get("work_product")
    if not isinstance(product, Mapping):
        raise WorkUnitValidityError("LEASE_WORK_PRODUCT_MISSING")
    work_product = {
        "path": _safe_repo_path(product.get("path")),
        "git_blob_sha": str(product.get("git_blob_sha") or ""),
    }
    if not SHA40_RE.fullmatch(work_product["git_blob_sha"]):
        raise WorkUnitValidityError("LEASE_WORK_PRODUCT_SHA_INVALID")

    closure = lease.get("dependency_closure")
    if not isinstance(closure, Mapping):
        raise WorkUnitValidityError("LEASE_DEPENDENCY_CLOSURE_MISSING")
    closure_path = _safe_repo_path(
        closure.get("certificate_path"),
        verification_only=True,
    )
    closure_sha = str(closure.get("git_blob_sha") or "")
    certificate = _load_json_at_ref(
        repo_root,
        ref=ref,
        path=closure_path,
        expected_blob_sha=closure_sha,
    )
    cert = validate_dependency_closure_certificate(
        certificate,
        expected_work_product=work_product,
        expected_semantic_dependencies=expected_map,
    )

    scheduler = lease.get("scheduler")
    if not isinstance(scheduler, Mapping):
        raise WorkUnitValidityError("LEASE_SCHEDULER_MISSING")
    expected_scheduler = str(scheduler.get("authority_epoch_sha256") or "")
    if not SHA256_RE.fullmatch(expected_scheduler):
        raise WorkUnitValidityError("LEASE_SCHEDULER_EPOCH_INVALID")

    work_class = str(lease.get("work_class") or "")
    current_components = current_semantic_components(repo_root, expected_map, ref)
    current_product_sha = git_blob_sha(repo_root, work_product["path"], ref)
    current_scheduler = epoch_for_ref(ref)["epoch_sha256"]

    result = evaluate_two_clock_lease(
        expected_work_product_sha=work_product["git_blob_sha"],
        current_work_product_sha=current_product_sha,
        expected_semantic_components=expected_map,
        current_semantic_components_map=current_components,
        expected_scheduler_epoch_sha256=expected_scheduler,
        current_scheduler_epoch_sha256=current_scheduler,
        dependency_closure_verified=cert["certificate_valid"],
        work_class=work_class,
    )
    result.update(
        {
            "ref": ref,
            "work_product": work_product,
            "dependency_closure_certificate": closure_path,
            "dependency_closure_git_blob_sha": closure_sha,
            "independent_verifier_method": cert["independent_verifier_method"],
            "current_scheduler_epoch_sha256": current_scheduler,
            "expected_scheduler_epoch_sha256": expected_scheduler,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lease", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    try:
        out = verify_lease(
            load_lease(args.lease),
            root=args.root,
            ref=args.ref,
        )
        print(json.dumps(out, indent=2, sort_keys=True))
        return 42 if out["status"].startswith("FAIL_CLOSED") else 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__WORK_UNIT_VALIDITY_ERROR",
                    "error": f"{type(exc).__name__}:{exc}",
                    "execution_authority": False,
                    "promotion_authority": False,
                    "fresh_reality_authority": False,
                    "acceptance_credit_delta": 0,
                    "terminal_credit_delta": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
