"""Dynamic exact-byte projection for the current one-shot closure frontier.

The one-shot runtime and its inner V1 closure are stable load-bearing code and
remain content-addressed in governance. R2 and terminal authority are moving
pointers, however. Treating their last observed blob hashes as permanently
"current" creates an avoidable race.

This module resolves those moving authorities from repository state at call time,
returns their exact Git blob identities, and makes snapshot drift observable
without turning ordinary concurrent progress into a false closure failure.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURRENT_ONE_SHOT_DYNAMIC_PROJECTION_V1"

PATHS = {
    "pointer": "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json",
    "v1": "canonical/runtime/one_shot_verified_closure_v1.py",
    "v2": "canonical/runtime/one_shot_reality_closure_v2.py",
    "r2": "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "terminal": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "default_runtime": "canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json",
    "live_wrapper": "canonical/runtime/r2_direct_live_admission_v1.py",
    "fixed_point": "canonical/runtime/general_adequate_decision_fixed_point_v2.py",
    "v19": "canonical/runtime/r2_direct_end_to_end_adequacy_v19.py",
    "v21": "canonical/runtime/r2_direct_end_to_end_adequacy_v21.py",
    "dynamic_admissions_pointer": "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",
    "dynamic_admissions_manifest": "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json",
    "self": "canonical/runtime/current_one_shot_projection_v1.py",
}

_VERSION = re.compile(r"(?:^|__)V(\d+)(?:__|$)")

_FINANCE_COMMON_POLICY_WAKE = (
    "NEW_COMMON_POLICY_ADEQUACY_CERTIFICATE_ROBUST_TO_THE_SURVIVING_COUNTERMODEL"
)
_FINANCE_DIRECT_ADEQUACY_WAKE = "NEW_DIRECT_END_TO_END_FINANCE_ADEQUACY_CERTIFICATE"
_FINANCE_DISCRIMINATOR_WAKES = frozenset(
    {
        "NEW_AUTHENTIC_POLICY_CHANGING_SOURCE_OR_CONTEXT_FACT",
        "NEW_SCOPE_COMPLETE_SOUND_FINANCE_INTERPRETATION_OR_CONSTRAINT_BOUND",
        "NEW_CONTENT_ADDRESSED_COMPLETE_FINANCE_SOURCE_OR_CONVENTION_SCOPE_BOUND_OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE",
        "NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_COMPANYCONCEPT_AND_SEC_INLINE_XBRL_STANDARD_FASB_SCOPES",
        "NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_COMPANYCONCEPT_SEC_INLINE_XBRL_STANDARD_FASB_AND_SAME_FILING_ISSUER_EXTENSION_DOCUMENTATION_SCOPES",
        "NEW_AUTHENTICATED_COMPLETE_BOUNDED_DENOTATION_EXTENSION_OR_SET_RELATION_EVIDENCE_OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE",
        "NEW_TASK_SPECIFIC_OEWN_TERMINAL_SIGNATURE_OR_DISCRIMINATOR_BINDING_FOR_SURVIVING_RELEASE_RELATIVE_SENSES",
        "NEW_AUTHENTICATED_CONTEXT_OR_RELATION_EVIDENCE_THAT_DISCRIMINATES_SURVIVING_SENSES",
        "NEW_AUTHENTICATED_OEWN_DECISION_MANIFEST_BINDING_COMPLETE_TERMINAL_SIGNATURES_TO_ALL_RELEASE_RELATIVE_SENSES",
        "NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT",
    }
)
_FINANCE_EFFECT_ORDER = (
    "COMMON_POLICY_ADEQUACY_BYPASS",
    "DIRECT_END_TO_END_ADEQUACY_BYPASS",
    "AUTHENTICATED_WORLD_DISCRIMINATOR_OR_CONSTRAINT",
)


def _finance_wake_effect_projection(r2: dict[str, Any]) -> dict[str, Any]:
    cells = r2.get("current_cell_classifications")
    cells = cells if isinstance(cells, dict) else {}
    cell = cells.get("FINANCE_SEMANTIC_ADEQUACY_TAIL")
    cell = cell if isinstance(cell, dict) else {}
    raw_wakes = cell.get("wake_on")
    if not isinstance(raw_wakes, list):
        return {
            "status": "NOT_APPLICABLE__NO_FINANCE_WAKE_LIST",
            "concrete_wake_condition_count": 0,
            "decision_effect_class_count": 0,
            "all_wakes_classified": False,
            "dedupe_by_effect_class_authorized": False,
            "effect_groups": {},
            "unclassified_wakes": [],
            "preserve_concrete_wake_routes_for_provenance": True,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    groups: dict[str, list[str]] = {}
    unclassified: list[str] = []
    for raw in raw_wakes:
        wake = str(raw)
        if wake == _FINANCE_COMMON_POLICY_WAKE:
            effect = "COMMON_POLICY_ADEQUACY_BYPASS"
        elif wake == _FINANCE_DIRECT_ADEQUACY_WAKE:
            effect = "DIRECT_END_TO_END_ADEQUACY_BYPASS"
        elif wake in _FINANCE_DISCRIMINATOR_WAKES:
            effect = "AUTHENTICATED_WORLD_DISCRIMINATOR_OR_CONSTRAINT"
        else:
            digest = hashlib.sha256(wake.encode("utf-8")).hexdigest()[:16]
            effect = "UNCLASSIFIED_WAKE::" + digest
            unclassified.append(wake)
        groups.setdefault(effect, []).append(wake)

    ordered = [effect for effect in _FINANCE_EFFECT_ORDER if effect in groups]
    ordered.extend(sorted(effect for effect in groups if effect not in _FINANCE_EFFECT_ORDER))
    all_classified = not unclassified
    return {
        "status": (
            "PASS__FINANCE_WAKE_EFFECT_QUOTIENT"
            if all_classified
            else "FAIL_CLOSED__UNCLASSIFIED_FINANCE_WAKE_PRESERVED_SEPARATELY"
        ),
        "concrete_wake_condition_count": len(raw_wakes),
        "decision_effect_class_count": len(groups),
        "all_wakes_classified": all_classified,
        "dedupe_by_effect_class_authorized": all_classified,
        "preferred_effect_search_order": ordered,
        "effect_groups": {effect: groups[effect] for effect in ordered},
        "unclassified_wakes": unclassified,
        "preserve_concrete_wake_routes_for_provenance": True,
        "finance_cell_state": cell.get("state"),
        "information_theoretic_externality_proved": (
            cell.get("information_theoretic_externality_proved") is True
        ),
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }




def _resolve_dynamic_admissions_manifest(
    root: Path,
    admissions_pointer: dict[str, Any],
) -> tuple[str, Path]:
    target = admissions_pointer.get("target")
    target = target if isinstance(target, dict) else {}
    rel = str(target.get("path") or "")
    if not rel:
        raise ValueError("DYNAMIC_ADMISSIONS_TARGET_PATH_MISSING")
    if not rel.startswith("canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_"):
        raise ValueError("DYNAMIC_ADMISSIONS_TARGET_PATH_OUTSIDE_ALLOWED_NAMESPACE")
    if not rel.endswith(".json"):
        raise ValueError("DYNAMIC_ADMISSIONS_TARGET_PATH_NOT_JSON")
    if target.get("schema") != "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1":
        raise ValueError("DYNAMIC_ADMISSIONS_TARGET_SCHEMA_INVALID")

    resolved = (root / rel).resolve(strict=True)
    resolved.relative_to(root)
    return rel, resolved


def _default_runtime_projection(
    pointer: dict[str, Any],
    default_runtime: dict[str, Any],
    admissions_pointer: dict[str, Any],
    admissions_manifest: dict[str, Any],
    actual: dict[str, str],
    dynamic_manifest_path: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    dynamic_manifest_path = (
        dynamic_manifest_path or PATHS["dynamic_admissions_manifest"]
    )

    if default_runtime.get("binding_semantics") != (
        "MUTABLE_CURRENT_PATH_IDENTITY__IMMUTABLE_LOAD_BEARING_DESCENDANTS_GIT_BLOB_BOUND"
    ):
        errors.append("DEFAULT_RUNTIME_BINDING_SEMANTICS_INVALID")

    pointer_binding = pointer.get("default_runtime_integration")
    pointer_binding = pointer_binding if isinstance(pointer_binding, dict) else {}
    if pointer_binding.get("path") != PATHS["default_runtime"]:
        errors.append("DEFAULT_RUNTIME_POINTER_PATH_MISMATCH")
    if pointer_binding.get("pointer_semantics") != "MUTABLE_CURRENT_PATH_IDENTITY_AUTHORITATIVE":
        errors.append("DEFAULT_RUNTIME_POINTER_SEMANTICS_INVALID")

    runtime = default_runtime.get("r2_default_route_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    wrapper = runtime.get("stable_wrapper_path")
    if wrapper != PATHS["live_wrapper"]:
        errors.append("DEFAULT_RUNTIME_WRAPPER_PATH_MISMATCH")
    if runtime.get("stable_wrapper_git_blob_sha") != actual["live_wrapper"]:
        errors.append("DEFAULT_RUNTIME_WRAPPER_BLOB_MISMATCH")

    fixed = runtime.get("fixed_point_controller_path")
    if fixed != PATHS["fixed_point"]:
        errors.append("DEFAULT_RUNTIME_FIXED_POINT_PATH_MISMATCH")
    if runtime.get("fixed_point_controller_git_blob_sha") != actual["fixed_point"]:
        errors.append("DEFAULT_RUNTIME_FIXED_POINT_BLOB_MISMATCH")

    baseline = runtime.get("current_r2_activation_baseline")
    baseline = baseline if isinstance(baseline, dict) else {}
    if baseline.get("authority_pointer_path") != PATHS["r2"]:
        errors.append("DEFAULT_RUNTIME_BASELINE_POINTER_PATH_MISMATCH")
    if baseline.get("pointer_path_identity_authoritative") is not True:
        errors.append("DEFAULT_RUNTIME_BASELINE_POINTER_SEMANTICS_INVALID")
    if baseline.get("runtime_path") != PATHS["v19"]:
        errors.append("DEFAULT_RUNTIME_BASELINE_RUNTIME_PATH_MISMATCH")
    if baseline.get("runtime_git_blob_sha") != actual["v19"]:
        errors.append("DEFAULT_RUNTIME_BASELINE_RUNTIME_BLOB_MISMATCH")
    if baseline.get("role") != (
        "CURRENT_R2_SCHEDULER_AND_ACTIVATION_SNAPSHOT__NOT_DEFAULT_RUNTIME_SOURCE_SELECTOR"
    ):
        errors.append("DEFAULT_RUNTIME_BASELINE_ROLE_INVALID")

    backend = runtime.get("verified_static_backend")
    backend = backend if isinstance(backend, dict) else {}
    if backend.get("runtime_path") != PATHS["v21"]:
        errors.append("DEFAULT_RUNTIME_V21_PATH_MISMATCH")
    if backend.get("runtime_git_blob_sha") != actual["v21"]:
        errors.append("DEFAULT_RUNTIME_V21_BLOB_MISMATCH")
    static_count = backend.get("static_default_route_count_before_dynamic")
    if isinstance(static_count, bool) or not isinstance(static_count, int) or static_count < 0:
        errors.append("DEFAULT_RUNTIME_STATIC_ROUTE_COUNT_INVALID")
        static_count = None

    dynamic = runtime.get("dynamic_admission")
    dynamic = dynamic if isinstance(dynamic, dict) else {}
    if dynamic.get("current_pointer_path") != PATHS["dynamic_admissions_pointer"]:
        errors.append("DEFAULT_RUNTIME_DYNAMIC_POINTER_PATH_MISMATCH")
    if dynamic.get("pointer_path_identity_authoritative") is not True:
        errors.append("DEFAULT_RUNTIME_DYNAMIC_POINTER_SEMANTICS_INVALID")

    if admissions_pointer.get("binding_semantics") != (
        "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
    ):
        errors.append("DYNAMIC_ADMISSIONS_POINTER_BINDING_SEMANTICS_INVALID")

    target = admissions_pointer.get("target")
    target = target if isinstance(target, dict) else {}
    if target.get("path") != dynamic_manifest_path:
        errors.append("DYNAMIC_ADMISSIONS_TARGET_PATH_MISMATCH")
    if target.get("git_blob_sha") != actual["dynamic_admissions_manifest"]:
        errors.append("DYNAMIC_ADMISSIONS_TARGET_BLOB_MISMATCH")

    snapshot_drift = {
        "pointer_blob_differs_from_current": (
            bool(dynamic.get("current_pointer_git_blob_sha"))
            and dynamic.get("current_pointer_git_blob_sha")
            != actual["dynamic_admissions_pointer"]
        ),
        "manifest_path_differs_from_current": (
            bool(dynamic.get("current_manifest_path"))
            and dynamic.get("current_manifest_path") != dynamic_manifest_path
        ),
        "manifest_blob_differs_from_current": (
            bool(dynamic.get("current_manifest_git_blob_sha"))
            and dynamic.get("current_manifest_git_blob_sha")
            != actual["dynamic_admissions_manifest"]
        ),
        "snapshot_is_authoritative": False,
    }

    manifest_count = admissions_manifest.get("admission_count")
    admissions = admissions_manifest.get("admissions")
    if (
        isinstance(manifest_count, bool)
        or not isinstance(manifest_count, int)
        or manifest_count < 0
        or not isinstance(admissions, list)
        or manifest_count != len(admissions)
    ):
        errors.append("DYNAMIC_ADMISSIONS_COUNT_INVALID")
        manifest_count = None
    snapshot_drift["route_count_differs_from_current"] = (
        isinstance(manifest_count, int)
        and dynamic.get("current_dynamic_route_count") != manifest_count
    )
    if admissions_manifest.get("terminal_authority") is not False:
        errors.append("DYNAMIC_ADMISSIONS_MANIFEST_TERMINAL_AUTHORITY_INVALID")
    if admissions_manifest.get("terminal_credit_delta") != 0:
        errors.append("DYNAMIC_ADMISSIONS_MANIFEST_TERMINAL_CREDIT_INVALID")

    if default_runtime.get("terminal_authority") is not False:
        errors.append("DEFAULT_RUNTIME_TERMINAL_AUTHORITY_INVALID")
    default_accounting = default_runtime.get("accounting")
    default_accounting = (
        default_accounting if isinstance(default_accounting, dict) else {}
    )
    if default_accounting.get("terminal_credit_delta") != 0:
        errors.append("DEFAULT_RUNTIME_TERMINAL_CREDIT_INVALID")

    effective_count = (
        static_count + manifest_count
        if isinstance(static_count, int) and isinstance(manifest_count, int)
        else None
    )
    return {
        "path": PATHS["default_runtime"],
        "git_blob_sha": actual["default_runtime"],
        "status": default_runtime.get("status"),
        "scheduler_baseline": {
            "runtime_path": baseline.get("runtime_path"),
            "runtime_git_blob_sha": baseline.get("runtime_git_blob_sha"),
            "activation_route_count": baseline.get("activation_route_count"),
            "is_default_runtime_source_selector": False,
        },
        "stable_wrapper": {
            "path": PATHS["live_wrapper"],
            "git_blob_sha": actual["live_wrapper"],
        },
        "fixed_point_controller": {
            "path": PATHS["fixed_point"],
            "git_blob_sha": actual["fixed_point"],
        },
        "effective_static_backend": {
            "runtime_path": PATHS["v21"],
            "runtime_git_blob_sha": actual["v21"],
            "lineage": list(backend.get("lineage") or []),
            "static_route_count": static_count,
        },
        "dynamic_admission": {
            "pointer_path": PATHS["dynamic_admissions_pointer"],
            "pointer_git_blob_sha": actual["dynamic_admissions_pointer"],
            "manifest_path": dynamic_manifest_path,
            "manifest_git_blob_sha": actual["dynamic_admissions_manifest"],
            "dynamic_route_count": manifest_count,
            "future_verified_route_requires_new_vN_source": dynamic.get(
                "future_verified_route_requires_new_vN_source"
            ),
            "snapshot_drift": snapshot_drift,
        },
        "effective_known_direct_route_count": effective_count,
        "scheduler_snapshot_is_default_runtime_source_selector": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }, errors


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def _version_from_status(status: Any) -> int | None:
    match = _VERSION.search(str(status or ""))
    return int(match.group(1)) if match else None


def evaluate(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    targets = {
        name: (root / rel).resolve(strict=True)
        for name, rel in PATHS.items()
        if name != "dynamic_admissions_manifest"
    }
    for path in targets.values():
        path.relative_to(root)

    pointer = _load(targets["pointer"])
    r2 = _load(targets["r2"])
    terminal = _load(targets["terminal"])
    default_runtime = _load(targets["default_runtime"])
    admissions_pointer = _load(targets["dynamic_admissions_pointer"])
    dynamic_manifest_path, dynamic_manifest_target = (
        _resolve_dynamic_admissions_manifest(root, admissions_pointer)
    )
    targets["dynamic_admissions_manifest"] = dynamic_manifest_target
    admissions_manifest = _load(dynamic_manifest_target)

    actual = {name: _blob(path) for name, path in targets.items()}
    errors: list[str] = []

    runtime = pointer.get("runtime") if isinstance(pointer.get("runtime"), dict) else {}
    predecessor = (
        pointer.get("predecessor")
        if isinstance(pointer.get("predecessor"), dict)
        else {}
    )
    authority = (
        pointer.get("authority")
        if isinstance(pointer.get("authority"), dict)
        else {}
    )
    dynamic = (
        authority.get("dynamic_current_projection")
        if isinstance(authority.get("dynamic_current_projection"), dict)
        else {}
    )

    if runtime.get("path") != PATHS["v2"]:
        errors.append("POINTER_V2_PATH_MISMATCH")
    if runtime.get("git_blob_sha") != actual["v2"]:
        errors.append("POINTER_V2_BLOB_MISMATCH")
    if predecessor.get("path") != PATHS["v1"]:
        errors.append("POINTER_V1_PATH_MISMATCH")
    if predecessor.get("git_blob_sha") != actual["v1"]:
        errors.append("POINTER_V1_BLOB_MISMATCH")
    if dynamic.get("path") != PATHS["self"]:
        errors.append("DYNAMIC_PROJECTION_PATH_MISMATCH")
    if dynamic.get("git_blob_sha") != actual["self"]:
        errors.append("DYNAMIC_PROJECTION_BLOB_MISMATCH")
    if dynamic.get("authoritative_for_moving_r2_and_terminal") is not True:
        errors.append("DYNAMIC_PROJECTION_NOT_AUTHORITATIVE_FOR_MOVING_POINTERS")
    if authority.get("static_projection_snapshots_authoritative") is not False:
        errors.append("STATIC_SNAPSHOTS_MUST_BE_NONAUTHORITATIVE")

    default_runtime_projection, default_runtime_errors = _default_runtime_projection(
        pointer,
        default_runtime,
        admissions_pointer,
        admissions_manifest,
        actual,
        dynamic_manifest_path,
    )
    errors.extend(default_runtime_errors)

    snapshot = pointer.get("current_projection_refresh_20261009")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    terminal_snapshot_sha = str(
        snapshot.get("current_terminal_authority_git_blob_sha") or ""
    )
    r2_snapshot_sha = str(snapshot.get("current_r2_pointer_git_blob_sha") or "")

    result = {
        "schema": SCHEMA,
        "status": "PASS__DYNAMIC_CURRENT_PROJECTION"
        if not errors
        else "FAIL_CLOSED__DYNAMIC_CURRENT_PROJECTION",
        "pass": not errors,
        "errors": errors,
        "stable_load_bearing": {
            "one_shot_v1": {
                "path": PATHS["v1"],
                "git_blob_sha": actual["v1"],
            },
            "one_shot_v2": {
                "path": PATHS["v2"],
                "git_blob_sha": actual["v2"],
            },
        },
        "current_r2": {
            "path": PATHS["r2"],
            "git_blob_sha": actual["r2"],
            "status": r2.get("status"),
            "version": _version_from_status(r2.get("status")),
            "role": "SCHEDULER_AND_ACTIVATION_BASELINE__NOT_DEFAULT_RUNTIME_SOURCE_SELECTOR",
            "finance_wake_effect_projection": _finance_wake_effect_projection(r2),
        },
        "default_runtime_integration": default_runtime_projection,
        "current_terminal_authority": {
            "path": PATHS["terminal"],
            "git_blob_sha": actual["terminal"],
            "status": terminal.get("status"),
            "pointer_revision": terminal.get("pointer_revision"),
        },
        "snapshot_drift": {
            "r2_snapshot_differs_from_current": bool(r2_snapshot_sha)
            and r2_snapshot_sha != actual["r2"],
            "terminal_snapshot_differs_from_current": bool(terminal_snapshot_sha)
            and terminal_snapshot_sha != actual["terminal"],
            "snapshot_is_authoritative": False,
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(), sort_keys=True))
