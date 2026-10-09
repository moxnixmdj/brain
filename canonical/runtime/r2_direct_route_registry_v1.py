"""Stable registry-backed R2 direct adequacy dispatcher V1.

This runtime replaces the source-version chain as the live selection surface.
Existing independently verified route implementations remain byte-identical.
The mutable CURRENT pointer is authoritative by path identity; its immutable
registry target and every load-bearing route/verification artifact are Git-blob
bound before use.

Migration V1 deliberately preserves the exact historical V8->...->V1 precedence.
New route admission is a separate authority operation and must prove explicit
disjointness, equivalence, or dominance before entering the current registry.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import raw_goal_archive_acceptance_v1 as archive_acceptance
from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as literal_acceptance
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json_acceptance
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as legacy_v1

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_DISPATCHER_V1"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_REGISTRY_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"


class DirectRouteRegistryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _inside(root: Path, raw: Any) -> Path:
    p = (root / str(raw)).resolve()
    resolved = root.resolve()
    if p != resolved and resolved not in p.parents:
        raise DirectRouteRegistryError("PATH_OUTSIDE_REPOSITORY")
    return p


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, Mapping):
        raise DirectRouteRegistryError("JSON_NOT_OBJECT:" + str(path))
    return dict(obj)


def load_registry(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    pointer = Path(pointer_path).resolve() if pointer_path is not None else (
        root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
    )
    doc = _load_json(pointer)
    if doc.get("schema") != POINTER_SCHEMA:
        raise DirectRouteRegistryError("CURRENT_POINTER_SCHEMA_INVALID")
    if doc.get("status") != "ACTIVE_CURRENT_R2_DIRECT_ROUTE_POINTER":
        raise DirectRouteRegistryError("CURRENT_POINTER_NOT_ACTIVE")
    if doc.get("binding_semantics") != (
        "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
    ):
        raise DirectRouteRegistryError("CURRENT_POINTER_BINDING_SEMANTICS_INVALID")

    target = doc.get("target")
    if not isinstance(target, Mapping):
        raise DirectRouteRegistryError("CURRENT_POINTER_TARGET_INVALID")
    target_path = _inside(root, target.get("path"))
    expected_sha = str(target.get("git_blob_sha") or "")
    if _git_blob_sha(target_path) != expected_sha:
        raise DirectRouteRegistryError("CURRENT_REGISTRY_TARGET_BLOB_MISMATCH")

    registry = _load_json(target_path)
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise DirectRouteRegistryError("REGISTRY_SCHEMA_INVALID")
    if not str(registry.get("status") or "").startswith("ACTIVE_"):
        raise DirectRouteRegistryError("REGISTRY_NOT_ACTIVE")
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
        if raw.get("active") is not True:
            raise DirectRouteRegistryError("INACTIVE_ROUTE_IN_ACTIVE_REGISTRY:" + str(index))
        route_id = str(raw.get("route_id") or "")
        if not route_id:
            raise DirectRouteRegistryError("ROUTE_ID_MISSING:" + str(index))
        priority = raw.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise DirectRouteRegistryError("ROUTE_PRIORITY_INVALID:" + route_id)
        runtime_rel = str(raw.get("runtime_path") or "")
        runtime_path = _inside(root, runtime_rel)
        if not runtime_rel.startswith("canonical/runtime/") or runtime_path.suffix != ".py":
            raise DirectRouteRegistryError("ROUTE_RUNTIME_PATH_INVALID:" + route_id)
        if _git_blob_sha(runtime_path) != str(raw.get("runtime_git_blob_sha") or ""):
            raise DirectRouteRegistryError("ROUTE_RUNTIME_BLOB_MISMATCH:" + route_id)
        for field in ("preflight_callable", "run_callable"):
            if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
                raise DirectRouteRegistryError(
                    "ROUTE_CALLABLE_INVALID:" + route_id + ":" + field
                )
        verification_rel = raw.get("verification_path")
        verification_sha = raw.get("verification_git_blob_sha")
        if verification_rel is not None or verification_sha is not None:
            if not isinstance(verification_rel, str) or not isinstance(verification_sha, str):
                raise DirectRouteRegistryError(
                    "ROUTE_VERIFICATION_BINDING_INCOMPLETE:" + route_id
                )
            verification_path = _inside(root, verification_rel)
            if _git_blob_sha(verification_path) != verification_sha:
                raise DirectRouteRegistryError(
                    "ROUTE_VERIFICATION_BLOB_MISMATCH:" + route_id
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
    module = importlib.import_module(_module_name(str(row["runtime_path"])))
    current: Any = module
    for part in name.split("."):
        current = getattr(current, part)
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


def _rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [dict(x) for x in registry["routes"]],
        key=lambda row: int(row["priority"]),
    )


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
        registry = load_registry(repo_root=repo_root, pointer_path=pointer_path)
        for row in _rows(registry):
            out = _invoke(
                _resolve_callable(row, "preflight_callable"),
                request,
                repo_root,
            )
            if not isinstance(out, Mapping):
                raise DirectRouteRegistryError(
                    "PREFLIGHT_RESULT_NOT_OBJECT:" + str(row["route_id"])
                )
            if out.get("matched") is not True:
                continue
            observed = str(out.get("route_id") or "")
            if observed != row["route_id"]:
                raise DirectRouteRegistryError(
                    "PREFLIGHT_ROUTE_ID_MISMATCH:"
                    + str(row["route_id"])
                    + "!="
                    + observed
                )
            return dict(out)
        return {**_base("NO_DIRECT_ADEQUACY_ROUTE"), "matched": False}
    except DirectRouteRegistryError as exc:
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
    try:
        registry = load_registry(repo_root=repo_root, pointer_path=pointer_path)
        by_id = {row["route_id"]: row for row in _rows(registry)}
        route_id = str(pf.get("route_id") or "")
        row = by_id.get(route_id)
        if row is None:
            raise DirectRouteRegistryError("MATCHED_ROUTE_NOT_IN_CURRENT_REGISTRY")
        out = _invoke(_resolve_callable(row, "run_callable"), request, repo_root)
        if not isinstance(out, Mapping):
            raise DirectRouteRegistryError("RUN_RESULT_NOT_OBJECT:" + route_id)
        observed = str(out.get("route_id") or "")
        if observed and observed != route_id:
            raise DirectRouteRegistryError(
                "RUN_ROUTE_ID_MISMATCH:" + route_id + "!=" + observed
            )
        return dict(out)
    except DirectRouteRegistryError as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": pf.get("route_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def catalog(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    registry = load_registry(repo_root=repo_root, pointer_path=pointer_path)
    rows = _rows(registry)
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_R2_DIRECT_ROUTE_REGISTRY_LOADED",
        "pass": True,
        "route_count": len(rows),
        "route_ids": [row["route_id"] for row in rows],
        "current_pointer_path": "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json",
        "future_route_source_edit_required": False,
        "terminal_authority": False,
    }


ROUTES = {
    row["route_id"]: {
        "capability_id": row.get("capability_id"),
        "runtime_path": row.get("runtime_path"),
        "preflight": row.get("preflight_callable"),
        "executor": row.get("run_callable"),
        "priority": row.get("priority"),
    }
    for row in _rows(load_registry())
}
