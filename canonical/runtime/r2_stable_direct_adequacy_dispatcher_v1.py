"""Stable R2 direct-adequacy dispatcher over frozen legacy V15 plus dynamic admissions.

The current V15 router remains the exact legacy semantics. Future independently
verified routes are admitted through CURRENT_R2_DIRECT_ROUTE_ADMISSIONS and do
not require a V16/V17 source-chain edit.

Selection law:
- zero dynamic matches: delegate to V15 exactly;
- one dynamic match: legacy V15 must neither match nor expose semantic-open;
- more than one dynamic match: fail closed;
- any dynamic/legacy overlap: fail closed.

Preflight grants no execution or acceptance authority.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
import inspect
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v15 as legacy_v15
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admissions

SCHEMA = "PROJECT_BRAIN_R2_STABLE_DIRECT_ADEQUACY_DISPATCHER_V1"
ROOT = Path(__file__).resolve().parents[2]
LEGACY_RUNTIME_PATH = "canonical/runtime/r2_direct_end_to_end_adequacy_v15.py"
LEGACY_RUNTIME_GIT_BLOB_SHA = "7ef033b93b34dc65a6910cf393e7be3589fd03ea"


class StableDirectRouteError(ValueError):
    pass


def _base(status: str, *, matched: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "matched": matched,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _git_blob_sha(path: Path) -> str:
    return admissions.git_blob_sha(path)


def _legacy_binding(repo_root: str | Path) -> None:
    root = Path(repo_root).resolve()
    path = (root / LEGACY_RUNTIME_PATH).resolve()
    if not path.is_file():
        raise StableDirectRouteError("LEGACY_V15_RUNTIME_MISSING")
    if _git_blob_sha(path) != LEGACY_RUNTIME_GIT_BLOB_SHA:
        raise StableDirectRouteError("LEGACY_V15_RUNTIME_BLOB_MISMATCH")


def _module_name(runtime_path: str) -> str:
    if not runtime_path.startswith("canonical/runtime/") or not runtime_path.endswith(".py"):
        raise StableDirectRouteError("DYNAMIC_RUNTIME_PATH_INVALID")
    return runtime_path[:-3].replace("/", ".")


def _resolve(row: Mapping[str, Any], field: str):
    name = str(row.get(field) or "")
    if not name:
        raise StableDirectRouteError("DYNAMIC_CALLABLE_MISSING:" + field)
    try:
        current: Any = importlib.import_module(_module_name(str(row["runtime_path"])))
        for part in name.split("."):
            current = getattr(current, part)
    except Exception as exc:
        raise StableDirectRouteError(
            "DYNAMIC_CALLABLE_RESOLUTION_FAILED:"
            + str(row.get("route_id"))
            + ":"
            + field
            + ":"
            + type(exc).__name__
        ) from exc
    if not callable(current):
        raise StableDirectRouteError("DYNAMIC_CALLABLE_NOT_CALLABLE:" + field)
    return current


def _invoke(callable_obj, request: Mapping[str, Any], repo_root: str | Path):
    sig = inspect.signature(callable_obj)
    if "repo_root" in sig.parameters:
        return callable_obj(request, repo_root=repo_root)
    return callable_obj(request)


def _dynamic_preflights(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], dict[str, Any]]]]:
    current = admissions.load_current_admissions(repo_root=repo_root)
    rows = [deepcopy(dict(row)) for row in current["admissions"]]
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in rows:
        out = _invoke(_resolve(row, "preflight_callable"), request, repo_root)
        if not isinstance(out, Mapping):
            raise StableDirectRouteError(
                "DYNAMIC_PREFLIGHT_RESULT_NOT_OBJECT:" + str(row["route_id"])
            )
        result = dict(out)
        if result.get("matched") is True:
            observed = str(result.get("route_id") or "")
            if observed != str(row["route_id"]):
                raise StableDirectRouteError(
                    "DYNAMIC_PREFLIGHT_ROUTE_ID_MISMATCH:"
                    + str(row["route_id"])
                    + "!="
                    + observed
                )
            matches.append((row, result))
    return rows, matches


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    try:
        _legacy_binding(root)
        rows, dynamic_matches = _dynamic_preflights(request, repo_root=root)

        # Empty dynamic state is deliberately observationally equivalent to
        # current V15. This is the migration safety property.
        if not rows:
            return dict(legacy_v15.preflight(request, repo_root=root))

        if len(dynamic_matches) > 1:
            return {
                **_base("FAIL_CLOSED__DYNAMIC_ROUTE_COLLISION", matched=True),
                "reason": "MULTIPLE_DYNAMIC_ROUTES_MATCH",
                "matching_route_ids": sorted(
                    str(row["route_id"]) for row, _ in dynamic_matches
                ),
            }

        if len(dynamic_matches) == 1:
            dynamic_row, dynamic_out = dynamic_matches[0]
            legacy = legacy_v15.preflight(request, repo_root=root)
            if not isinstance(legacy, Mapping):
                raise StableDirectRouteError("LEGACY_PREFLIGHT_RESULT_NOT_OBJECT")
            if (
                legacy.get("matched") is True
                or legacy.get("direct_route_semantic_open") is True
            ):
                ids = [str(dynamic_row["route_id"])]
                if legacy.get("route_id"):
                    ids.append(str(legacy["route_id"]))
                return {
                    **_base("FAIL_CLOSED__DYNAMIC_LEGACY_ROUTE_COLLISION", matched=True),
                    "reason": (
                        "DYNAMIC_ROUTE_OVERLAPS_LEGACY_MATCH_OR_SEMANTIC_OPEN"
                    ),
                    "matching_route_ids": sorted(set(ids)),
                    "legacy_status": legacy.get("status"),
                    "legacy_direct_route_semantic_open": (
                        legacy.get("direct_route_semantic_open") is True
                    ),
                }
            return dict(dynamic_out)

        return dict(legacy_v15.preflight(request, repo_root=root))
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("status") in {
        "FAIL_CLOSED",
        "FAIL_CLOSED__DYNAMIC_ROUTE_COLLISION",
        "FAIL_CLOSED__DYNAMIC_LEGACY_ROUTE_COLLISION",
    }:
        return pf

    try:
        current = admissions.load_current_admissions(repo_root=root)
        by_id = {str(row["route_id"]): row for row in current["admissions"]}
        route_id = str(pf.get("route_id") or "")
        if route_id in by_id and pf.get("matched") is True:
            row = by_id[route_id]
            out = _invoke(_resolve(row, "run_callable"), request, root)
            if not isinstance(out, Mapping):
                raise StableDirectRouteError("DYNAMIC_RUN_RESULT_NOT_OBJECT")
            observed = str(out.get("route_id") or "")
            if observed and observed != route_id:
                raise StableDirectRouteError(
                    "DYNAMIC_RUN_ROUTE_ID_MISMATCH:" + route_id + "!=" + observed
                )
            return dict(out)

        # No dynamic route owns the request. Preserve V15 execution exactly.
        return dict(legacy_v15.run(request, repo_root=root))
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED", matched=pf.get("matched") is True),
            "route_id": pf.get("route_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def catalog(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        _legacy_binding(root)
        current = admissions.load_current_admissions(repo_root=root)
        ids = sorted(str(row["route_id"]) for row in current["admissions"])
        return {
            "schema": SCHEMA,
            "status": "PASS__LEGACY_V15_PLUS_DYNAMIC_ADMISSIONS_LIVE",
            "pass": True,
            "legacy_runtime_path": LEGACY_RUNTIME_PATH,
            "legacy_runtime_git_blob_sha": LEGACY_RUNTIME_GIT_BLOB_SHA,
            "legacy_current_route_count": len(legacy_v15.ROUTES),
            "dynamic_admission_count": len(ids),
            "dynamic_route_ids": ids,
            "future_route_source_edit_required": False,
            "collision_policy": "FAIL_CLOSED_ON_DYNAMIC_DYNAMIC_OR_DYNAMIC_LEGACY_OVERLAP",
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }


ROUTES = dict(legacy_v15.ROUTES)
