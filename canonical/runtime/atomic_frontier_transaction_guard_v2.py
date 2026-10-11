"""Field-scoped atomic frontier transaction guard.

V2 composes the canonical V1 path-level transaction guard with the reused
field-scoped authority projection gate. It permits verification reuse across a
global authority-epoch change only for ZERO-CREDIT preparation when every
declared field dependency is unchanged and no declared mutation/coarse
dependency path conflicts.

It never grants execution, promotion, acceptance, ownership, or terminal
authority. Consequential boundaries must still recheck the outer authority
epoch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.atomic_frontier_transaction_guard_v1 import (
    _changed_paths,
    _git,
    _is_ancestor,
    _normalize_path,
    _ref_sha,
    paths_overlap,
)
from canonical.runtime.authority_epoch_guard_v1 import epoch_for_ref
from canonical.runtime.field_scoped_authority_projection_gate_v1 import (
    GateError,
    check_manifest,
    freeze_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_GUARD_V2"


class AtomicFrontierTransactionV2Error(RuntimeError):
    pass


def _parse_field_dependency(spec: str) -> tuple[str, str]:
    if not isinstance(spec, str) or "#" not in spec:
        raise AtomicFrontierTransactionV2Error(
            "FIELD_DEPENDENCY_MUST_BE_PATH_HASH_JSON_POINTER"
        )
    path, pointer = spec.split("#", 1)
    path = _normalize_path(path)
    if not path:
        raise AtomicFrontierTransactionV2Error("FIELD_DEPENDENCY_PATH_EMPTY")
    if pointer and not pointer.startswith("/"):
        raise AtomicFrontierTransactionV2Error(
            "FIELD_DEPENDENCY_POINTER_MUST_BE_RFC6901"
        )
    return path, pointer


def _group_field_dependencies(specs: Sequence[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        path, pointer = _parse_field_dependency(spec)
        key = (path, pointer)
        if key in seen:
            raise AtomicFrontierTransactionV2Error(
                "DUPLICATE_FIELD_DEPENDENCY:" + path + "#" + pointer
            )
        seen.add(key)
        grouped.setdefault(path, []).append(pointer)
    for path in grouped:
        grouped[path] = sorted(grouped[path])
    return dict(sorted(grouped.items()))


def _git_json(root: Path, ref: str, path: str) -> Mapping[str, Any]:
    try:
        raw = _git(root, "show", f"{ref}:{path}")
        value = json.loads(raw)
    except Exception as exc:
        raise AtomicFrontierTransactionV2Error(
            "FIELD_DEPENDENCY_JSON_READ_FAILED:"
            + ref
            + ":"
            + path
            + ":"
            + type(exc).__name__
        ) from exc
    if not isinstance(value, dict):
        raise AtomicFrontierTransactionV2Error(
            "FIELD_DEPENDENCY_JSON_NOT_OBJECT:" + path
        )
    return value


def _field_manifests(
    root: Path,
    base_ref: str,
    specs: Sequence[str],
) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path, pointers in _group_field_dependencies(specs).items():
        doc = _git_json(root, base_ref, path)
        blob = _git(root, "rev-parse", f"{base_ref}:{path}")
        manifests.append(
            freeze_manifest(
                doc,
                pointers,
                source_path=path,
                source_blob_sha=blob,
            )
        )
    return manifests


def _field_results(
    root: Path,
    current_ref: str,
    manifests: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for manifest in manifests:
        path = str(manifest.get("source_path") or "")
        try:
            live = _git_json(root, current_ref, path)
            result = check_manifest(live, manifest)
        except Exception as exc:
            result = {
                "schema_version": "FIELD_SCOPED_AUTHORITY_PROJECTION_GATE_V1",
                "stale": True,
                "changed_dependencies": [
                    {
                        "pointer": "",
                        "reason": "FAIL_CLOSED_CHECK_ERROR",
                        "error": type(exc).__name__ + ":" + str(exc),
                    }
                ],
                "manifest_sha256": manifest.get("manifest_sha256"),
            }
        results.append({"source_path": path, **result})
    return results


def classify_snapshot_v2(
    *,
    base_sha: str,
    current_sha: str,
    expected_authority_epoch: str,
    base_authority_epoch: str,
    current_authority_epoch: str,
    intervening_paths: Sequence[str],
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
    field_dependency_results: Sequence[Mapping[str, Any]] = (),
    allow_field_scoped_epoch_rebase: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []

    if not all(
        (
            base_sha,
            current_sha,
            expected_authority_epoch,
            base_authority_epoch,
            current_authority_epoch,
        )
    ):
        errors.append("MISSING_TRANSACTION_BINDING")

    if expected_authority_epoch != base_authority_epoch:
        errors.append("START_EPOCH_BINDING_MISMATCH")

    declared = tuple(
        sorted(
            {
                _normalize_path(p)
                for p in [*mutation_paths, *dependency_paths]
                if _normalize_path(p)
            }
        )
    )
    changed = tuple(
        sorted(
            {
                _normalize_path(p)
                for p in intervening_paths
                if _normalize_path(p)
            }
        )
    )
    conflicts = tuple(
        sorted(
            c
            for c in changed
            if any(paths_overlap(c, d) for d in declared)
        )
    )
    if conflicts:
        errors.append("INTERVENING_PATH_CONFLICT")

    stale_field_rows = [
        dict(x)
        for x in field_dependency_results
        if x.get("stale") is not False
    ]
    if stale_field_rows:
        errors.append("FIELD_SCOPED_DEPENDENCY_CHANGED")

    epoch_changed = current_authority_epoch != expected_authority_epoch
    field_scoped_epoch_override = bool(
        epoch_changed
        and allow_field_scoped_epoch_rebase
        and field_dependency_results
        and not stale_field_rows
        and not conflicts
    )
    if epoch_changed and not field_scoped_epoch_override:
        errors.append("AUTHORITY_EPOCH_CHANGED")

    exact = base_sha == current_sha
    passed = not errors

    if passed and exact:
        status = "PASS__EXACT_CURRENT"
        integration_mode = "LAND_ATOMICALLY_ON_EXACT_CURRENT_BASE"
    elif passed and field_scoped_epoch_override:
        status = (
            "PASS__ZERO_CREDIT_FIELD_SCOPED_CURRENTNESS__"
            "GLOBAL_EPOCH_CHANGED_NONLOADBEARING"
        )
        integration_mode = (
            "REBIND_ZERO_CREDIT_CANDIDATE_ON_CURRENT_MAIN__"
            "PRESERVE_UNCHANGED_VERIFICATION__"
            "RECHECK_OUTER_EPOCH_BEFORE_ANY_AUTHORITY_BOUNDARY"
        )
    elif passed:
        status = "PASS__SEMANTICALLY_CURRENT__NONCONFLICTING_MAIN_ADVANCE"
        integration_mode = "REBIND_ON_CURRENT_MAIN__PRESERVE_UNCHANGED_VERIFICATION"
    else:
        status = "FAIL_CLOSED__TRANSACTION_STALE_OR_CONFLICTING"
        integration_mode = "RECOMPUTE_ONLY_INVALIDATED_DELTA"

    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "base_sha": base_sha,
        "current_sha": current_sha,
        "main_advanced": not exact,
        "expected_authority_epoch": expected_authority_epoch,
        "base_authority_epoch": base_authority_epoch,
        "current_authority_epoch": current_authority_epoch,
        "authority_epoch_changed": epoch_changed,
        "field_scoped_epoch_override_used": field_scoped_epoch_override,
        "declared_paths": list(declared),
        "intervening_paths": list(changed),
        "conflicting_paths": list(conflicts),
        "field_dependency_results": [dict(x) for x in field_dependency_results],
        "integration_mode": integration_mode,
        "verification_reuse_allowed": bool(passed and not exact),
        "zero_credit_preparation_only": bool(field_scoped_epoch_override),
        "outer_epoch_recheck_required_before_authority_boundary": True,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "errors": errors,
        "rule": (
            "UNRELATED_MAIN_OR_AUTHORITY_CHURN_DOES_NOT_INVALIDATE_VERIFIED_"
            "ZERO_CREDIT_WORK__DECLARED_PATH_OR_FIELD_DEPENDENCY_CHANGES_DO__"
            "OUTER_EPOCH_STILL_REQUIRED_FOR_CONSEQUENTIAL_AUTHORITY"
        ),
    }


def evaluate_transaction(
    *,
    root: Path,
    base_ref: str,
    current_ref: str,
    expected_authority_epoch: str,
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
    field_dependencies: Sequence[str] = (),
    allow_field_scoped_epoch_rebase: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    base_sha = _ref_sha(root, base_ref)
    current_sha = _ref_sha(root, current_ref)
    if not _is_ancestor(root, base_ref, current_ref):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__BASE_NOT_ANCESTOR_OF_CURRENT",
            "base_sha": base_sha,
            "current_sha": current_sha,
            "integration_mode": "REBASE_OR_REBUILD_FROM_CURRENT_MAIN",
            "verification_reuse_allowed": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
            "errors": ["BASE_NOT_ANCESTOR_OF_CURRENT"],
        }

    manifests = _field_manifests(root, base_ref, field_dependencies)
    field_results = _field_results(root, current_ref, manifests)
    base_epoch = epoch_for_ref(base_ref)["epoch_sha256"]
    current_epoch = epoch_for_ref(current_ref)["epoch_sha256"]

    return classify_snapshot_v2(
        base_sha=base_sha,
        current_sha=current_sha,
        expected_authority_epoch=expected_authority_epoch,
        base_authority_epoch=base_epoch,
        current_authority_epoch=current_epoch,
        intervening_paths=_changed_paths(root, base_ref, current_ref),
        mutation_paths=mutation_paths,
        dependency_paths=dependency_paths,
        field_dependency_results=field_results,
        allow_field_scoped_epoch_rebase=allow_field_scoped_epoch_rebase,
    )


def start_transaction(
    *,
    root: Path,
    base_ref: str,
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
    field_dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    root = root.resolve()
    epoch = epoch_for_ref(base_ref)
    manifests = _field_manifests(root, base_ref, field_dependencies)
    return {
        "schema": "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_START_V2",
        "status": "BOUND",
        "base_ref": base_ref,
        "base_sha": _ref_sha(root, base_ref),
        "authority_epoch_sha256": epoch["epoch_sha256"],
        "authority_epoch_components": epoch["components"],
        "mutation_paths": sorted(
            {_normalize_path(p) for p in mutation_paths if _normalize_path(p)}
        ),
        "dependency_paths": sorted(
            {_normalize_path(p) for p in dependency_paths if _normalize_path(p)}
        ),
        "field_dependency_manifests": manifests,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "RECHECK_DECLARED_PATHS_AND_FIELD_SCOPED_DEPENDENCIES_IMMEDIATELY_"
            "BEFORE_INTEGRATION__OUTER_EPOCH_REQUIRED_AT_AUTHORITY_BOUNDARY"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--mode", choices=("start", "finalize"), required=True)
    ap.add_argument("--base-ref", required=True)
    ap.add_argument("--current-ref", default="HEAD")
    ap.add_argument("--expected-authority-epoch")
    ap.add_argument("--mutation-path", action="append", default=[])
    ap.add_argument("--dependency-path", action="append", default=[])
    ap.add_argument(
        "--field-dependency",
        action="append",
        default=[],
        help="Repeat as repository/path.json#/rfc6901/pointer",
    )
    ap.add_argument(
        "--allow-field-scoped-epoch-rebase",
        action="store_true",
        help="Zero-credit preparation only; never grants promotion/execution authority.",
    )
    ns = ap.parse_args()

    try:
        if ns.mode == "start":
            out = start_transaction(
                root=ns.root,
                base_ref=ns.base_ref,
                mutation_paths=ns.mutation_path,
                dependency_paths=ns.dependency_path,
                field_dependencies=ns.field_dependency,
            )
        else:
            if not ns.expected_authority_epoch:
                raise AtomicFrontierTransactionV2Error(
                    "EXPECTED_AUTHORITY_EPOCH_REQUIRED_FOR_FINALIZE"
                )
            out = evaluate_transaction(
                root=ns.root,
                base_ref=ns.base_ref,
                current_ref=ns.current_ref,
                expected_authority_epoch=ns.expected_authority_epoch,
                mutation_paths=ns.mutation_path,
                dependency_paths=ns.dependency_path,
                field_dependencies=ns.field_dependency,
                allow_field_scoped_epoch_rebase=ns.allow_field_scoped_epoch_rebase,
            )
    except (AtomicFrontierTransactionV2Error, GateError, Exception) as exc:
        out = {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__TRANSACTION_GUARD_ERROR",
            "error": type(exc).__name__ + ":" + str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass", ns.mode == "start") else 42


if __name__ == "__main__":
    raise SystemExit(main())
