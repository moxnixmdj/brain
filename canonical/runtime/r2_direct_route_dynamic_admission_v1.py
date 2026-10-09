"""Proof-carrying dynamic admission contract for R2 direct routes V1.

This module normalizes the seam between heterogeneous route-specific verification
and default-live deployment. It grants no semantic or verification authority.

A route may enter the dynamic admission manifest only when:
- a content-addressed deployment candidate binds its exact runtime and route-specific
  verification artifact;
- an independent deployment receipt binds the exact candidate bytes and repeats
  the exact runtime / verification identities;
- the receipt proves the direct-route invariants required for safe default use.

Dynamic routes always enter as UNIQUE_MATCH_REQUIRED. The live dispatcher fails
closed on overlap with any other dynamic or legacy route unless a future explicit
equivalence/dominance authority is added.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSION_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_INDEPENDENT_RECEIPT_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_POINTER_V1"
SELECTION_CLASS = "UNIQUE_MATCH_REQUIRED"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_CALLABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


class DynamicAdmissionError(ValueError):
    pass


def git_blob_sha_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git_blob_sha(path: Path) -> str:
    return git_blob_sha_bytes(path.read_bytes())


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(
        dict(value),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n").encode("utf-8")


def _inside(root: Path, raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise DynamicAdmissionError("NONCANONICAL_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise DynamicAdmissionError("PATH_OUTSIDE_ALLOWED_SCOPE:" + value)
    full = (root / p).resolve()
    resolved = root.resolve()
    if full != resolved and resolved not in full.parents:
        raise DynamicAdmissionError("PATH_OUTSIDE_REPOSITORY:" + value)
    if not full.is_file():
        raise DynamicAdmissionError("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DynamicAdmissionError("JSON_INVALID:" + str(path)) from exc
    if not isinstance(value, Mapping):
        raise DynamicAdmissionError("JSON_OBJECT_REQUIRED:" + str(path))
    return dict(value)


def _sha40(value: Any, *, field: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA40.fullmatch(text):
        raise DynamicAdmissionError(field + "_INVALID")
    return text


def _callable(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not _CALLABLE.fullmatch(text):
        raise DynamicAdmissionError(field + "_INVALID")
    return text


def _verify_bound_file(
    root: Path,
    rel: Any,
    expected_sha: Any,
    *,
    prefixes: tuple[str, ...],
    label: str,
) -> tuple[str, str]:
    path_text = str(rel or "").strip()
    path = _inside(root, path_text, prefixes=prefixes)
    expected = _sha40(expected_sha, field=label + "_GIT_BLOB_SHA")
    actual = git_blob_sha(path)
    if actual != expected:
        raise DynamicAdmissionError(
            label + "_BLOB_MISMATCH:" + expected + "!=" + actual
        )
    return path_text, actual


def validate_candidate(
    root: Path,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise DynamicAdmissionError("CANDIDATE_OBJECT_REQUIRED")
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise DynamicAdmissionError("CANDIDATE_SCHEMA_INVALID")
    route_id = str(candidate.get("route_id") or "").strip()
    if not route_id:
        raise DynamicAdmissionError("ROUTE_ID_REQUIRED")
    if candidate.get("deployment_requested") is not True:
        raise DynamicAdmissionError("DEPLOYMENT_NOT_REQUESTED")
    if candidate.get("selection_class") != SELECTION_CLASS:
        raise DynamicAdmissionError("SELECTION_CLASS_MUST_BE_UNIQUE_MATCH_REQUIRED")
    if candidate.get("incremental_spend_usd") != 0:
        raise DynamicAdmissionError("INCREMENTAL_SPEND_NOT_ZERO")
    if candidate.get("terminal_authority") is not False:
        raise DynamicAdmissionError("CANDIDATE_TERMINAL_AUTHORITY_FORBIDDEN")

    runtime_path, runtime_sha = _verify_bound_file(
        root,
        candidate.get("runtime_path"),
        candidate.get("runtime_git_blob_sha"),
        prefixes=("canonical/runtime/",),
        label="RUNTIME",
    )
    verification_path, verification_sha = _verify_bound_file(
        root,
        candidate.get("route_verification_path"),
        candidate.get("route_verification_git_blob_sha"),
        prefixes=("canonical/verification/",),
        label="ROUTE_VERIFICATION",
    )
    preflight = _callable(candidate.get("preflight_callable"), field="PREFLIGHT_CALLABLE")
    run = _callable(candidate.get("run_callable"), field="RUN_CALLABLE")
    scope = str(candidate.get("scope") or "").strip()
    if not scope:
        raise DynamicAdmissionError("SCOPE_REQUIRED")
    capability_id = candidate.get("capability_id")
    if capability_id is not None and not isinstance(capability_id, str):
        raise DynamicAdmissionError("CAPABILITY_ID_INVALID")
    return {
        "route_id": route_id,
        "capability_id": capability_id,
        "runtime_path": runtime_path,
        "runtime_git_blob_sha": runtime_sha,
        "preflight_callable": preflight,
        "run_callable": run,
        "route_verification_path": verification_path,
        "route_verification_git_blob_sha": verification_sha,
        "scope": scope,
        "selection_class": SELECTION_CLASS,
    }


def validate_receipt(
    root: Path,
    receipt: Mapping[str, Any],
    *,
    candidate_path: str,
    candidate_blob_sha: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise DynamicAdmissionError("RECEIPT_OBJECT_REQUIRED")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise DynamicAdmissionError("RECEIPT_SCHEMA_INVALID")
    if receipt.get("status") != "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT":
        raise DynamicAdmissionError("RECEIPT_NOT_INDEPENDENT_DEPLOYMENT_PASS")
    expected = {
        "candidate_path": candidate_path,
        "candidate_git_blob_sha": candidate_blob_sha,
        "route_id": candidate["route_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "route_verification_path": candidate["route_verification_path"],
        "route_verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
        "selection_class": SELECTION_CLASS,
        "independent_verified": True,
        "preflight_pure_no_effect": True,
        "matched_route_failure_no_fallthrough": True,
        "producer_independent_acceptance": True,
        "exact_raw_obligation_acceptance": True,
        "deployment_eligible": True,
        "verification_authority_mutated": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise DynamicAdmissionError("RECEIPT_BINDING_MISMATCH:" + key)
    return deepcopy(dict(receipt))


def validate_admission_row(root: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise DynamicAdmissionError("ADMISSION_ROW_OBJECT_REQUIRED")
    candidate_path = str(row.get("candidate_path") or "").strip()
    receipt_path = str(row.get("independent_receipt_path") or "").strip()
    candidate_file = _inside(
        root,
        candidate_path,
        prefixes=("canonical/governance/", "canonical/verification/"),
    )
    receipt_file = _inside(
        root,
        receipt_path,
        prefixes=("canonical/verification/",),
    )
    candidate_blob = git_blob_sha(candidate_file)
    receipt_blob = git_blob_sha(receipt_file)
    if candidate_blob != _sha40(
        row.get("candidate_git_blob_sha"), field="CANDIDATE_GIT_BLOB_SHA"
    ):
        raise DynamicAdmissionError("ADMISSION_CANDIDATE_BLOB_MISMATCH")
    if receipt_blob != _sha40(
        row.get("independent_receipt_git_blob_sha"),
        field="INDEPENDENT_RECEIPT_GIT_BLOB_SHA",
    ):
        raise DynamicAdmissionError("ADMISSION_RECEIPT_BLOB_MISMATCH")
    candidate = validate_candidate(root, _load_json(candidate_file))
    validate_receipt(
        root,
        _load_json(receipt_file),
        candidate_path=candidate_path,
        candidate_blob_sha=candidate_blob,
        candidate=candidate,
    )
    expected = {
        "route_id": candidate["route_id"],
        "capability_id": candidate["capability_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "preflight_callable": candidate["preflight_callable"],
        "run_callable": candidate["run_callable"],
        "verification_path": candidate["route_verification_path"],
        "verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
        "scope": candidate["scope"],
        "selection_class": SELECTION_CLASS,
        "active": True,
        "automatic_live_admission": True,
    }
    for key, value in expected.items():
        if row.get(key) != value:
            raise DynamicAdmissionError("ADMISSION_ROW_BINDING_MISMATCH:" + key)
    return deepcopy(dict(row))


def validate_manifest(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise DynamicAdmissionError("MANIFEST_OBJECT_REQUIRED")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise DynamicAdmissionError("MANIFEST_SCHEMA_INVALID")
    if not str(manifest.get("status") or "").startswith("ACTIVE_DYNAMIC_ADMISSIONS"):
        raise DynamicAdmissionError("MANIFEST_NOT_ACTIVE")
    if manifest.get("selection_class") != SELECTION_CLASS:
        raise DynamicAdmissionError("MANIFEST_SELECTION_CLASS_INVALID")
    if manifest.get("collision_policy") != (
        "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH"
    ):
        raise DynamicAdmissionError("MANIFEST_COLLISION_POLICY_INVALID")
    rows = manifest.get("admissions")
    if not isinstance(rows, list):
        raise DynamicAdmissionError("MANIFEST_ADMISSIONS_NOT_LIST")
    if manifest.get("admission_count") != len(rows):
        raise DynamicAdmissionError("MANIFEST_ADMISSION_COUNT_MISMATCH")
    validated = [validate_admission_row(root, row) for row in rows]
    ids = [str(row["route_id"]) for row in validated]
    if len(ids) != len(set(ids)):
        raise DynamicAdmissionError("MANIFEST_DUPLICATE_ROUTE_ID")
    return {
        **deepcopy(dict(manifest)),
        "admissions": validated,
    }


def load_current_admissions(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    pointer = Path(pointer_path).resolve() if pointer_path is not None else (
        root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
    )
    doc = _load_json(pointer)
    if doc.get("schema") != POINTER_SCHEMA:
        raise DynamicAdmissionError("CURRENT_ADMISSION_POINTER_SCHEMA_INVALID")
    if doc.get("status") != "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER":
        raise DynamicAdmissionError("CURRENT_ADMISSION_POINTER_NOT_ACTIVE")
    if doc.get("binding_semantics") != (
        "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
    ):
        raise DynamicAdmissionError("CURRENT_ADMISSION_POINTER_BINDING_INVALID")
    target = doc.get("target")
    if not isinstance(target, Mapping):
        raise DynamicAdmissionError("CURRENT_ADMISSION_POINTER_TARGET_INVALID")
    target_path, actual_sha = _verify_bound_file(
        root,
        target.get("path"),
        target.get("git_blob_sha"),
        prefixes=("canonical/governance/",),
        label="CURRENT_DYNAMIC_ADMISSIONS",
    )
    manifest = validate_manifest(root, _load_json(root / target_path))
    return {
        "pointer": doc,
        "target_path": target_path,
        "target_git_blob_sha": actual_sha,
        "manifest": manifest,
        "admissions": deepcopy(manifest["admissions"]),
    }


def compile_admission(
    *,
    repo_root: str | Path = ROOT,
    current_manifest: Mapping[str, Any],
    candidate_path: str,
    receipt_path: str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    manifest = validate_manifest(root, current_manifest)
    candidate_file = _inside(
        root,
        candidate_path,
        prefixes=("canonical/governance/", "canonical/verification/"),
    )
    receipt_file = _inside(
        root,
        receipt_path,
        prefixes=("canonical/verification/",),
    )
    candidate_blob = git_blob_sha(candidate_file)
    receipt_blob = git_blob_sha(receipt_file)
    candidate = validate_candidate(root, _load_json(candidate_file))
    validate_receipt(
        root,
        _load_json(receipt_file),
        candidate_path=candidate_path,
        candidate_blob_sha=candidate_blob,
        candidate=candidate,
    )

    existing = {
        str(row["route_id"]): row for row in manifest["admissions"]
    }
    route_id = candidate["route_id"]
    if route_id in existing:
        old = existing[route_id]
        same = (
            old.get("runtime_git_blob_sha") == candidate["runtime_git_blob_sha"]
            and old.get("verification_git_blob_sha")
            == candidate["route_verification_git_blob_sha"]
            and old.get("candidate_git_blob_sha") == candidate_blob
            and old.get("independent_receipt_git_blob_sha") == receipt_blob
        )
        if not same:
            raise DynamicAdmissionError("ROUTE_ID_ALREADY_ADMITTED_WITH_DIFFERENT_BINDING")
        return {
            "schema": SCHEMA,
            "status": "ALREADY_ADMITTED_EXACT_BINDING",
            "pass": True,
            "frontier_changed": False,
            "route_id": route_id,
            "manifest": manifest,
            "verification_authority_mutated": False,
            "terminal_authority": False,
        }

    row = {
        "route_id": route_id,
        "capability_id": candidate["capability_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "preflight_callable": candidate["preflight_callable"],
        "run_callable": candidate["run_callable"],
        "verification_path": candidate["route_verification_path"],
        "verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
        "candidate_path": candidate_path,
        "candidate_git_blob_sha": candidate_blob,
        "independent_receipt_path": receipt_path,
        "independent_receipt_git_blob_sha": receipt_blob,
        "scope": candidate["scope"],
        "selection_class": SELECTION_CLASS,
        "active": True,
        "automatic_live_admission": True,
        "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
    }
    rows = [deepcopy(dict(x)) for x in manifest["admissions"]] + [row]
    rows.sort(key=lambda x: str(x["route_id"]))
    new_manifest = {
        **deepcopy(dict(manifest)),
        "status": "ACTIVE_DYNAMIC_ADMISSIONS__NONEMPTY",
        "admissions": rows,
        "admission_count": len(rows),
    }
    raw = _json_bytes(new_manifest)
    return {
        "schema": SCHEMA,
        "status": "PROMOTION_READY__R2_DIRECT_ROUTE_DYNAMIC_ADMISSION",
        "pass": True,
        "frontier_changed": True,
        "route_id": route_id,
        "admission_row": row,
        "manifest": new_manifest,
        "manifest_bytes": raw,
        "manifest_git_blob_sha": git_blob_sha_bytes(raw),
        "verification_authority_mutated": False,
        "terminal_authority": False,
    }
