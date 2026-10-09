"""Stable authority-backed R2 direct adequacy dispatcher V1.

Current R2 activation is the deployable route universe. The immutable direct-route
registry is only a legacy precedence overlay for routes whose historical ordered
selection semantics must be preserved exactly.

A route admitted by current R2 authority but absent from the legacy overlay becomes
live automatically as UNIQUE_MATCH_REQUIRED. It may execute only when exactly one
such dynamic route matches and no legacy route matches the same request. Any
collision fails closed until a future explicit equivalence or dominance authority
is installed.

Thus future verified/activated R2 route growth requires neither a new
r2_direct_end_to_end_adequacy_vN.py nor a registry edit.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import raw_goal_archive_acceptance_v1 as archive_acceptance
from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as literal_acceptance
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json_acceptance
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as dynamic_admission

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_DISPATCHER_V1"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_REGISTRY_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
CURRENT_R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"

LEGACY_SELECTION_CLASS = "LEGACY_ORDERED_MIGRATION"
DYNAMIC_SELECTION_CLASS = "UNIQUE_MATCH_REQUIRED"


class DirectRouteRegistryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _inside(root: Path, raw: Any) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise DirectRouteRegistryError("PATH_REQUIRED")
    p = (root / value).resolve()
    resolved = root.resolve()
    if p != resolved and resolved not in p.parents:
        raise DirectRouteRegistryError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_file():
        raise DirectRouteRegistryError("BOUND_FILE_MISSING:" + value)
    return p


def _load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DirectRouteRegistryError(
            "JSON_INVALID:" + str(path)
        ) from exc
    if not isinstance(obj, Mapping):
        raise DirectRouteRegistryError("JSON_NOT_OBJECT:" + str(path))
    return dict(obj)


def _verify_blob(root: Path, rel: Any, expected: Any, *, label: str) -> Path:
    value = str(rel or "").strip()
    sha = str(expected or "").strip()
    path = _inside(root, value)
    if _git_blob_sha(path) != sha:
        raise DirectRouteRegistryError(label + "_BLOB_MISMATCH:" + value)
    return path


def load_registry(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load immutable legacy precedence metadata through the mutable CURRENT path."""
    root = Path(repo_root).resolve()
    pointer = Path(pointer_path).resolve() if pointer_path is not None else (
        root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
    )
    doc = _load_json(pointer)
    if doc.get("schema") != POINTER_SCHEMA:
        raise DirectRouteRegistryError("CURRENT_POINTER_SCHEMA_INVALID")
    if doc.get("status") != "ACTIVE_CURRENT_R2_DIRECT_ROUTE_SELECTION_METADATA_POINTER":
        raise DirectRouteRegistryError("CURRENT_POINTER_NOT_ACTIVE")
    if doc.get("binding_semantics") != (
        "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
    ):
        raise DirectRouteRegistryError("CURRENT_POINTER_BINDING_SEMANTICS_INVALID")
    target = doc.get("target")
    if not isinstance(target, Mapping):
        raise DirectRouteRegistryError("CURRENT_POINTER_TARGET_INVALID")
    target_path = _verify_blob(
        root,
        target.get("path"),
        target.get("git_blob_sha"),
        label="CURRENT_REGISTRY_TARGET",
    )
    registry = _load_json(target_path)
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise DirectRouteRegistryError("REGISTRY_SCHEMA_INVALID")
    if not str(registry.get("status") or "").startswith("ACTIVE_"):
        raise DirectRouteRegistryError("REGISTRY_NOT_ACTIVE")
    if registry.get("selection_role") != (
        "LEGACY_PRECEDENCE_OVERLAY_ONLY__CURRENT_R2_ACTIVATION_IS_DEPLOYABLE_ROUTE_UNIVERSE"
    ):
        raise DirectRouteRegistryError("REGISTRY_SELECTION_ROLE_INVALID")
    rows = registry.get("routes")
    if not isinstance(rows, list) or not rows:
        raise DirectRouteRegistryError("REGISTRY_ROUTES_INVALID")
    if registry.get("route_count") != len(rows):
        raise DirectRouteRegistryError("REGISTRY_ROUTE_COUNT_MISMATCH")

    route_ids: list[str] = []
    priorities: list[int] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise DirectRouteRegistryError("ROUTE_NOT_OBJECT:" + str(index))
        route_id = str(raw.get("route_id") or "")
        if not route_id:
            raise DirectRouteRegistryError("ROUTE_ID_MISSING:" + str(index))
        if raw.get("active") is not True:
            raise DirectRouteRegistryError("INACTIVE_LEGACY_METADATA:" + route_id)
        if raw.get("selection_class") != LEGACY_SELECTION_CLASS:
            raise DirectRouteRegistryError("LEGACY_SELECTION_CLASS_INVALID:" + route_id)
        priority = raw.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise DirectRouteRegistryError("ROUTE_PRIORITY_INVALID:" + route_id)
        for field in ("runtime_path", "runtime_git_blob_sha", "preflight_callable", "run_callable"):
            if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
                raise DirectRouteRegistryError(
                    "LEGACY_METADATA_FIELD_INVALID:" + route_id + ":" + field
                )
        route_ids.append(route_id)
        priorities.append(priority)

    if len(route_ids) != len(set(route_ids)):
        raise DirectRouteRegistryError("DUPLICATE_ROUTE_ID")
    if len(priorities) != len(set(priorities)):
        raise DirectRouteRegistryError("DUPLICATE_ROUTE_PRIORITY")
    if sorted(priorities) != list(range(len(rows))):
        raise DirectRouteRegistryError("ROUTE_PRIORITIES_NOT_CONTIGUOUS")
    return registry


def load_current_activation(*, repo_root: str | Path = ROOT) -> dict[str, Any]:
    """Load the current deployable R2 direct-route universe from current authority."""
    root = Path(repo_root).resolve()
    current_path = root / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
    current = _load_json(current_path)
    direct = current.get("direct_adequacy")
    if not isinstance(direct, Mapping):
        raise DirectRouteRegistryError("CURRENT_R2_DIRECT_ADEQUACY_MISSING")
    activation_rel = str(direct.get("activation_path") or "")
    if not activation_rel.startswith("canonical/governance/"):
        raise DirectRouteRegistryError("CURRENT_R2_ACTIVATION_PATH_INVALID")
    activation_path = _verify_blob(
        root,
        activation_rel,
        direct.get("activation_git_blob_sha"),
        label="CURRENT_R2_ACTIVATION",
    )
    activation = _load_json(activation_path)
    routes = activation.get("current_routes")
    if not isinstance(routes, list) or not routes:
        raise DirectRouteRegistryError("CURRENT_R2_ACTIVATION_ROUTES_INVALID")
    if direct.get("current_route_count") != len(routes):
        raise DirectRouteRegistryError("CURRENT_R2_ROUTE_COUNT_MISMATCH")
    ids = [
        str(row.get("route_id") or "")
        for row in routes
        if isinstance(row, Mapping)
    ]
    if len(ids) != len(routes) or any(not x for x in ids):
        raise DirectRouteRegistryError("CURRENT_R2_ROUTE_ID_INVALID")
    if len(ids) != len(set(ids)):
        raise DirectRouteRegistryError("CURRENT_R2_ROUTE_ID_DUPLICATE")
    return {
        "current_r2": current,
        "direct_adequacy": dict(direct),
        "activation": activation,
        "activation_path": activation_rel,
        "activation_git_blob_sha": str(direct.get("activation_git_blob_sha") or ""),
        "routes": [deepcopy(dict(row)) for row in routes],
    }


def _validate_legacy_binding(
    metadata: Mapping[str, Any],
    activation: Mapping[str, Any],
    *,
    root: Path,
) -> dict[str, Any]:
    route_id = str(metadata.get("route_id") or "")
    runtime_rel = activation.get("runtime")
    if runtime_rel is not None:
        if metadata.get("runtime_path") != runtime_rel:
            raise DirectRouteRegistryError("LEGACY_RUNTIME_PATH_AUTHORITY_MISMATCH:" + route_id)
        if metadata.get("runtime_git_blob_sha") != activation.get("runtime_git_blob_sha"):
            raise DirectRouteRegistryError("LEGACY_RUNTIME_BLOB_AUTHORITY_MISMATCH:" + route_id)
    _verify_blob(
        root,
        metadata.get("runtime_path"),
        metadata.get("runtime_git_blob_sha"),
        label="LEGACY_RUNTIME_" + route_id,
    )

    verification = activation.get("verification")
    if isinstance(verification, Mapping):
        if metadata.get("verification_path") != verification.get("path"):
            raise DirectRouteRegistryError(
                "LEGACY_VERIFICATION_PATH_AUTHORITY_MISMATCH:" + route_id
            )
        if metadata.get("verification_git_blob_sha") != verification.get("git_blob_sha"):
            raise DirectRouteRegistryError(
                "LEGACY_VERIFICATION_BLOB_AUTHORITY_MISMATCH:" + route_id
            )
        _verify_blob(
            root,
            metadata.get("verification_path"),
            metadata.get("verification_git_blob_sha"),
            label="LEGACY_VERIFICATION_" + route_id,
        )
    out = deepcopy(dict(metadata))
    out["activation_authority"] = True
    return out


def _derive_dynamic_row(
    activation: Mapping[str, Any],
    *,
    activation_index: int,
    root: Path,
) -> dict[str, Any]:
    route_id = str(activation.get("route_id") or "")
    runtime_rel = str(activation.get("runtime") or "").strip()
    runtime_sha = str(activation.get("runtime_git_blob_sha") or "").strip()
    if not runtime_rel or not runtime_sha:
        raise DirectRouteRegistryError(
            "AUTO_ADMITTED_ROUTE_RUNTIME_BINDING_MISSING:" + route_id
        )
    if not runtime_rel.startswith("canonical/runtime/"):
        raise DirectRouteRegistryError(
            "AUTO_ADMITTED_ROUTE_RUNTIME_PATH_INVALID:" + route_id
        )
    _verify_blob(root, runtime_rel, runtime_sha, label="AUTO_ADMITTED_RUNTIME_" + route_id)

    verification = activation.get("verification")
    if not isinstance(verification, Mapping):
        raise DirectRouteRegistryError(
            "AUTO_ADMITTED_ROUTE_VERIFICATION_BINDING_MISSING:" + route_id
        )
    verification_rel = str(verification.get("path") or "").strip()
    verification_sha = str(verification.get("git_blob_sha") or "").strip()
    if not verification_rel or not verification_sha:
        raise DirectRouteRegistryError(
            "AUTO_ADMITTED_ROUTE_VERIFICATION_BINDING_INVALID:" + route_id
        )
    _verify_blob(
        root,
        verification_rel,
        verification_sha,
        label="AUTO_ADMITTED_VERIFICATION_" + route_id,
    )
    return {
        "route_id": route_id,
        "priority": None,
        "activation_index": activation_index,
        "active": True,
        "capability_id": activation.get("capability_id"),
        "runtime_path": runtime_rel,
        "runtime_git_blob_sha": runtime_sha,
        "preflight_callable": "preflight",
        "run_callable": "run",
        "verification_path": verification_rel,
        "verification_git_blob_sha": verification_sha,
        "selection_class": DYNAMIC_SELECTION_CLASS,
        "activation_authority": True,
        "scope": activation.get("scope"),
        "automatic_live_admission": True,
        "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
    }


def effective_state(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    """Join frozen baseline activation, dynamic admissions, and legacy precedence."""
    root = Path(repo_root).resolve()
    metadata = load_registry(repo_root=root, pointer_path=pointer_path)
    current = load_current_activation(repo_root=root)
    dynamic = dynamic_admission.load_current_admissions(repo_root=root)

    metadata_by_id = {
        str(row["route_id"]): deepcopy(dict(row))
        for row in metadata["routes"]
    }
    baseline_ids: list[str] = []
    rows: list[dict[str, Any]] = []
    activation_auto: list[str] = []

    for index, raw in enumerate(current["routes"]):
        route_id = str(raw.get("route_id") or "")
        baseline_ids.append(route_id)
        if route_id in metadata_by_id:
            row = _validate_legacy_binding(
                metadata_by_id[route_id],
                raw,
                root=root,
            )
            row["activation_index"] = index
        else:
            row = _derive_dynamic_row(raw, activation_index=index, root=root)
            activation_auto.append(route_id)
        rows.append(row)

    baseline_set = set(baseline_ids)
    dynamic_ids: list[str] = []
    dynamic_shadowed: list[str] = []
    by_baseline = {str(row["route_id"]): row for row in rows}
    for offset, admitted in enumerate(dynamic["admissions"]):
        route_id = str(admitted.get("route_id") or "")
        if route_id in baseline_set:
            baseline = by_baseline[route_id]
            same = (
                baseline.get("runtime_git_blob_sha")
                == admitted.get("runtime_git_blob_sha")
                and baseline.get("verification_git_blob_sha")
                == admitted.get("verification_git_blob_sha")
            )
            if not same:
                raise DirectRouteRegistryError(
                    "DYNAMIC_ADMISSION_CONFLICTS_WITH_BASELINE:" + route_id
                )
            dynamic_shadowed.append(route_id)
            continue
        row = deepcopy(dict(admitted))
        row["activation_index"] = len(current["routes"]) + offset
        row["selection_class"] = DYNAMIC_SELECTION_CLASS
        row["automatic_live_admission"] = True
        rows.append(row)
        dynamic_ids.append(route_id)

    deployable_set = baseline_set | set(dynamic_ids)
    if len(deployable_set) != len(rows):
        raise DirectRouteRegistryError("EFFECTIVE_ROUTE_ID_COLLISION")

    stale = sorted(set(metadata_by_id) - baseline_set)
    auto = sorted(set(activation_auto) | set(dynamic_ids))
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_R2_BASELINE_PLUS_DYNAMIC_ADMISSIONS_JOINED_WITH_SELECTION_METADATA",
        "rows": rows,
        "deployable_route_ids": sorted(deployable_set),
        "baseline_activation_route_ids": sorted(baseline_set),
        "legacy_selection_metadata_route_ids": sorted(metadata_by_id),
        "activation_auto_admitted_route_ids": sorted(activation_auto),
        "dynamic_admission_route_ids": sorted(dynamic_ids),
        "dynamic_shadowed_by_baseline_route_ids": sorted(dynamic_shadowed),
        "auto_admitted_route_ids": auto,
        "stale_selection_metadata_route_ids": stale,
        "deployable_route_count": len(rows),
        "baseline_activation_route_count": len(baseline_set),
        "legacy_selection_metadata_count": len(metadata_by_id),
        "activation_auto_admitted_route_count": len(activation_auto),
        "dynamic_admission_route_count": len(dynamic_ids),
        "auto_admitted_route_count": len(auto),
        "current_activation_path": current["activation_path"],
        "current_activation_git_blob_sha": current["activation_git_blob_sha"],
        "dynamic_admission_target_path": dynamic["target_path"],
        "dynamic_admission_target_git_blob_sha": dynamic["target_git_blob_sha"],
    }

def _base(status: str, *, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _inline_archive_preflight(
    request: Mapping[str, Any], *, repo_root: str | Path = ROOT
) -> dict[str, Any]:
    goal = str(request.get("goal") or "").strip()
    match = archive_acceptance.GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    return {
        **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
        "matched": True,
        "route_id": "DIRECT_ADEQUACY::ARCHIVE_MANIFEST_TAR_GZ_V1",
        "capability_id": "archive.tar_gz.create_from_manifest",
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "bound_inputs": {
            "manifest_path": match.group("manifest"),
            "output_path": match.group("output"),
        },
        "semantic_scope": "EXACT_ARCHIVE_MANIFEST_VERIFICATION_PATHS_GOAL_ONLY",
        "preflight_execution_authority": False,
    }


def _inline_literal_preflight(
    request: Mapping[str, Any], *, repo_root: str | Path = ROOT
) -> dict[str, Any]:
    goal = str(request.get("goal") or "").strip()
    literal = literal_acceptance.preflight(goal)
    if literal.get("matched") is not True:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    return {
        **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
        "matched": True,
        "route_id": "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
        "capability_id": None,
        "goal_sha256": literal["goal_sha256"],
        "literal_sha256": literal["literal_sha256"],
        "semantic_scope": "STRICT_REPLY_OR_RESPOND_WITH_EXACTLY_LITERAL_GOAL_ONLY",
        "preflight_execution_authority": False,
    }


def _inline_literal_json_preflight(
    request: Mapping[str, Any], *, repo_root: str | Path = ROOT
) -> dict[str, Any]:
    goal = str(request.get("goal") or "").strip()
    literal_json = literal_json_acceptance.preflight(goal)
    if literal_json.get("matched") is not True:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    return {
        **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
        "matched": True,
        "route_id": "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1",
        "capability_id": None,
        "goal_sha256": literal_json["goal_sha256"],
        "output_path": literal_json["output_path"],
        "records_sha256": literal_json["records_sha256"],
        "semantic_scope": "STRICT_LITERAL_JSON_RECORDS_TO_CANONICAL_REPOSITORY_PATH_ONLY",
        "preflight_execution_authority": False,
    }


def _inline_v1_run(
    request: Mapping[str, Any], *, repo_root: str | Path = ROOT
) -> dict[str, Any]:
    # Keep the stable route registry importable without dragging the entire
    # legacy execution graph into registry/closure verification.
    legacy_v1 = importlib.import_module(
        "canonical.runtime.r2_direct_end_to_end_adequacy_v1"
    )
    return legacy_v1.run(request)


_INLINE = {
    "_inline_archive_preflight": _inline_archive_preflight,
    "_inline_literal_preflight": _inline_literal_preflight,
    "_inline_literal_json_preflight": _inline_literal_json_preflight,
    "_inline_v1_run": _inline_v1_run,
}


def _module_name(runtime_path: str) -> str:
    if not runtime_path.startswith("canonical/runtime/") or not runtime_path.endswith(".py"):
        raise DirectRouteRegistryError("RUNTIME_MODULE_PATH_INVALID")
    return runtime_path[:-3].replace("/", ".")


def _resolve_callable(row: Mapping[str, Any], field: str):
    name = str(row.get(field) or "")
    if name in _INLINE:
        return _INLINE[name]
    try:
        module = importlib.import_module(_module_name(str(row["runtime_path"])))
        current: Any = module
        for part in name.split("."):
            current = getattr(current, part)
    except Exception as exc:
        raise DirectRouteRegistryError(
            "ROUTE_CALLABLE_RESOLUTION_FAILED:"
            + str(row.get("route_id"))
            + ":"
            + field
            + ":"
            + type(exc).__name__
        ) from exc
    if not callable(current):
        raise DirectRouteRegistryError(
            "ROUTE_CALLABLE_NOT_CALLABLE:" + str(row["route_id"]) + ":" + field
        )
    return current


def _invoke(callable_obj, request: Mapping[str, Any], repo_root: str | Path):
    signature = inspect.signature(callable_obj)
    if "repo_root" in signature.parameters:
        return callable_obj(request, repo_root=repo_root)
    return callable_obj(request)


def _legacy_rows(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            deepcopy(dict(row))
            for row in state["rows"]
            if row.get("selection_class") == LEGACY_SELECTION_CLASS
        ],
        key=lambda row: int(row["priority"]),
    )


def _dynamic_rows(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            deepcopy(dict(row))
            for row in state["rows"]
            if row.get("selection_class") == DYNAMIC_SELECTION_CLASS
        ],
        key=lambda row: (int(row["activation_index"]), str(row["route_id"])),
    )


def _preflight_row(
    row: Mapping[str, Any],
    request: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    out = _invoke(_resolve_callable(row, "preflight_callable"), request, repo_root)
    if not isinstance(out, Mapping):
        raise DirectRouteRegistryError(
            "PREFLIGHT_RESULT_NOT_OBJECT:" + str(row["route_id"])
        )
    result = dict(out)
    if result.get("matched") is True:
        observed = str(result.get("route_id") or "")
        if observed != row["route_id"]:
            raise DirectRouteRegistryError(
                "PREFLIGHT_ROUTE_ID_MISMATCH:"
                + str(row["route_id"])
                + "!="
                + observed
            )
    return result


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    try:
        state = effective_state(repo_root=repo_root, pointer_path=pointer_path)
        legacy = _legacy_rows(state)
        dynamic = _dynamic_rows(state)

        # Existing current runtime remains the fast path: exact legacy precedence,
        # no extra all-route scan while there are no newly activated routes.
        if not dynamic:
            for row in legacy:
                out = _preflight_row(row, request, repo_root)
                if out.get("direct_route_semantic_open") is True:
                    if row.get("semantic_open_stops_fallback") is not True:
                        return {
                            **_base("FAIL_CLOSED__UNAUTHORIZED_SEMANTIC_OPEN_BARRIER"),
                            "matched": False,
                            "route_id": row.get("route_id"),
                            "reason": "SEMANTIC_OPEN_REQUIRES_EXPLICIT_BARRIER_AUTHORITY",
                        }
                    return out
                if out.get("matched") is True:
                    return out
            return {**_base("NO_DIRECT_ADEQUACY_ROUTE"), "matched": False}

        dynamic_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        dynamic_open: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in dynamic:
            out = _preflight_row(row, request, repo_root)
            if out.get("direct_route_semantic_open") is True:
                dynamic_open.append((row, out))
            if out.get("matched") is True:
                dynamic_matches.append((row, out))

        if dynamic_open:
            implicated = sorted({
                str(row["route_id"]) for row, _ in dynamic_open + dynamic_matches
            })
            if len(dynamic_open) == 1 and not dynamic_matches:
                only_row, only_out = dynamic_open[0]
                if only_row.get("semantic_open_stops_fallback") is True:
                    return only_out
            return {
                **_base("FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY"),
                "matched": False,
                "reason": "DYNAMIC_SEMANTIC_OPEN_CANNOT_DEFINE_FALLBACK_ORDER",
                "matching_route_ids": implicated,
            }

        if len(dynamic_matches) > 1:
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                "matched": True,
                "reason": "MULTIPLE_AUTO_ADMITTED_ROUTES_MATCH",
                "matching_route_ids": sorted(
                    row["route_id"] for row, _ in dynamic_matches
                ),
            }

        if len(dynamic_matches) == 1:
            dynamic_row, dynamic_out = dynamic_matches[0]
            for row in legacy:
                legacy_out = _preflight_row(row, request, repo_root)
                if legacy_out.get("matched") is True:
                    return {
                        **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                        "matched": True,
                        "reason": "AUTO_ADMITTED_ROUTE_OVERLAPS_LEGACY_ROUTE",
                        "matching_route_ids": sorted(
                            [dynamic_row["route_id"], row["route_id"]]
                        ),
                    }
            return dynamic_out

        for row in legacy:
            out = _preflight_row(row, request, repo_root)
            if out.get("direct_route_semantic_open") is True:
                if row.get("semantic_open_stops_fallback") is not True:
                    return {
                        **_base("FAIL_CLOSED__UNAUTHORIZED_SEMANTIC_OPEN_BARRIER"),
                        "matched": False,
                        "route_id": row.get("route_id"),
                        "reason": "SEMANTIC_OPEN_REQUIRES_EXPLICIT_BARRIER_AUTHORITY",
                    }
                return out
            if out.get("matched") is True:
                return out
        return {**_base("NO_DIRECT_ADEQUACY_ROUTE"), "matched": False}
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": False,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root, pointer_path=pointer_path)
    if pf.get("matched") is not True:
        return pf
    route_id = str(pf.get("route_id") or "")
    if not route_id:
        return pf
    try:
        state = effective_state(repo_root=repo_root, pointer_path=pointer_path)
        by_id = {str(row["route_id"]): row for row in state["rows"]}
        row = by_id.get(route_id)
        if row is None:
            raise DirectRouteRegistryError("MATCHED_ROUTE_NOT_IN_CURRENT_DEPLOYABLE_UNIVERSE")
        out = _invoke(_resolve_callable(row, "run_callable"), request, repo_root)
        if not isinstance(out, Mapping):
            raise DirectRouteRegistryError("RUN_RESULT_NOT_OBJECT:" + route_id)
        observed = str(out.get("route_id") or "")
        if observed and observed != route_id:
            raise DirectRouteRegistryError(
                "RUN_ROUTE_ID_MISMATCH:" + route_id + "!=" + observed
            )
        return dict(out)
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": route_id,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def catalog(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    state = effective_state(repo_root=repo_root, pointer_path=pointer_path)
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_R2_DEPLOYABLE_ROUTE_UNIVERSE_LIVE",
        "pass": True,
        "route_count": state["deployable_route_count"],
        "route_ids": state["deployable_route_ids"],
        "baseline_activation_route_count": state["baseline_activation_route_count"],
        "legacy_selection_metadata_count": state["legacy_selection_metadata_count"],
        "activation_auto_admitted_route_count": state["activation_auto_admitted_route_count"],
        "dynamic_admission_route_count": state["dynamic_admission_route_count"],
        "auto_admitted_route_count": state["auto_admitted_route_count"],
        "auto_admitted_route_ids": state["auto_admitted_route_ids"],
        "stale_selection_metadata_route_ids": state["stale_selection_metadata_route_ids"],
        "current_pointer_path": "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json",
        "current_activation_path": state["current_activation_path"],
        "dynamic_admission_target_path": state["dynamic_admission_target_path"],
        "future_route_source_edit_required": False,
        "future_route_registry_edit_required": False,
        "future_route_current_r2_edit_required": False,
        "new_route_collision_policy": (
            "UNIQUE_MATCH_REQUIRED__COLLISION_FAILS_CLOSED_UNTIL_EXPLICIT_"
            "EQUIVALENCE_OR_DOMINANCE_AUTHORITY"
        ),
        "terminal_authority": False,
    }


# Compatibility snapshot only. Execution paths call effective_state() fresh, so a
# mutable CURRENT_R2 authority update does not require a process-source rewrite.
_IMPORT_STATE = effective_state()
ROUTES = {
    str(row["route_id"]): {
        "capability_id": row.get("capability_id"),
        "runtime_path": row.get("runtime_path"),
        "preflight": row.get("preflight_callable"),
        "executor": row.get("run_callable"),
        "selection_class": row.get("selection_class"),
        "priority": row.get("priority"),
    }
    for row in _IMPORT_STATE["rows"]
}
