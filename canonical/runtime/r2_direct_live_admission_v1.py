"""Stable default-live R2 direct-route admission wrapper over current V20.

V20 remains the exact legacy precedence carrier for all currently admitted routes.
New independently verified routes may be admitted through the proof-carrying dynamic
admission manifest without creating V20. Dynamic preflights are required to be pure.

Selection law:
- no dynamic admissions -> delegate exactly to V20;
- one dynamic match and no legacy match/open state -> execute the dynamic route;
- multiple dynamic matches -> fail closed;
- dynamic match plus any legacy match/semantic-open state -> fail closed;
- dynamic semantic-open state -> fail closed until explicit precedence authority exists.

This wrapper grants no verification, semantic, acceptance, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
import inspect
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v20 as legacy
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_LIVE_ADMISSION_WRAPPER_V1"
ROOT = Path(__file__).resolve().parents[2]
LEGACY_RUNTIME = "canonical.runtime.r2_direct_end_to_end_adequacy_v20"
DYNAMIC_SELECTION_CLASS = admission.SELECTION_CLASS

# Compatibility snapshot only. Dynamic routes are current-state data, not source constants.
ROUTES = dict(legacy.ROUTES)


class DirectLiveAdmissionError(ValueError):
    pass


def _base(status: str, *, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "verification_authority_mutated": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _module_name(runtime_path: str) -> str:
    if not runtime_path.startswith("canonical/runtime/") or not runtime_path.endswith(".py"):
        raise DirectLiveAdmissionError("DYNAMIC_RUNTIME_PATH_INVALID")
    return runtime_path[:-3].replace("/", ".")


def _resolve_callable(row: Mapping[str, Any], field: str):
    name = str(row.get(field) or "").strip()
    if not name:
        raise DirectLiveAdmissionError("DYNAMIC_CALLABLE_NAME_MISSING:" + field)
    try:
        module = importlib.import_module(_module_name(str(row.get("runtime_path") or "")))
        current: Any = module
        for part in name.split("."):
            current = getattr(current, part)
    except Exception as exc:
        raise DirectLiveAdmissionError(
            "DYNAMIC_CALLABLE_RESOLUTION_FAILED:"
            + str(row.get("route_id") or "")
            + ":"
            + field
            + ":"
            + type(exc).__name__
        ) from exc
    if not callable(current):
        raise DirectLiveAdmissionError(
            "DYNAMIC_CALLABLE_NOT_CALLABLE:"
            + str(row.get("route_id") or "")
            + ":"
            + field
        )
    return current


def _invoke(callable_obj, request: Mapping[str, Any], repo_root: str | Path):
    signature = inspect.signature(callable_obj)
    if "repo_root" in signature.parameters:
        return callable_obj(request, repo_root=repo_root)
    return callable_obj(request)


def _dynamic_rows(repo_root: str | Path) -> list[dict[str, Any]]:
    current = admission.load_current_admissions(repo_root=repo_root)
    rows = [deepcopy(dict(row)) for row in current["admissions"]]
    rows.sort(key=lambda row: str(row.get("route_id") or ""))
    return rows


def _dynamic_preflight(
    row: Mapping[str, Any],
    request: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    out = _invoke(_resolve_callable(row, "preflight_callable"), request, repo_root)
    if not isinstance(out, Mapping):
        raise DirectLiveAdmissionError(
            "DYNAMIC_PREFLIGHT_RESULT_NOT_OBJECT:" + str(row.get("route_id") or "")
        )
    result = dict(out)
    if result.get("matched") is True:
        observed = str(result.get("route_id") or "")
        expected = str(row.get("route_id") or "")
        if observed != expected:
            raise DirectLiveAdmissionError(
                "DYNAMIC_PREFLIGHT_ROUTE_ID_MISMATCH:" + expected + "!=" + observed
            )
    return result


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "matched": False, "reason": "REQUEST_NOT_OBJECT"}
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        dynamic = _dynamic_rows(root)
        if not dynamic:
            return legacy.preflight(request, repo_root=root)

        matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        semantic_open: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in dynamic:
            out = _dynamic_preflight(row, request, root)
            if out.get("direct_route_semantic_open") is True:
                semantic_open.append((row, out))
            if out.get("matched") is True:
                matches.append((row, out))

        if semantic_open:
            return {
                **_base("FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY"),
                "matched": False,
                "reason": "DYNAMIC_SEMANTIC_OPEN_CANNOT_DEFINE_LEGACY_PRECEDENCE",
                "route_ids": sorted(str(row["route_id"]) for row, _ in semantic_open),
            }

        if len(matches) > 1:
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                "matched": True,
                "reason": "MULTIPLE_DYNAMIC_ROUTES_MATCH",
                "matching_route_ids": sorted(str(row["route_id"]) for row, _ in matches),
            }

        legacy_out = legacy.preflight(request, repo_root=root)
        legacy_engaged = (
            legacy_out.get("matched") is True
            or legacy_out.get("direct_route_semantic_open") is True
        )

        if len(matches) == 1:
            row, dynamic_out = matches[0]
            if legacy_engaged:
                legacy_id = str(legacy_out.get("route_id") or "LEGACY_V20")
                return {
                    **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                    "matched": True,
                    "reason": "DYNAMIC_ROUTE_OVERLAPS_LEGACY_V20",
                    "matching_route_ids": sorted(
                        [str(row["route_id"]), legacy_id]
                    ),
                }
            return dynamic_out

        return dict(legacy_out)
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": False,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    status = str(pf.get("status") or "")
    if status.startswith("FAIL_CLOSED"):
        return pf
    if pf.get("direct_route_semantic_open") is True:
        return pf

    route_id = str(pf.get("route_id") or "")
    try:
        dynamic = _dynamic_rows(root)
        by_id = {str(row["route_id"]): row for row in dynamic}
        row = by_id.get(route_id)
        if row is not None and pf.get("matched") is True:
            out = _invoke(_resolve_callable(row, "run_callable"), request, root)
            if not isinstance(out, Mapping):
                raise DirectLiveAdmissionError("DYNAMIC_RUN_RESULT_NOT_OBJECT:" + route_id)
            observed = str(out.get("route_id") or "")
            if observed and observed != route_id:
                raise DirectLiveAdmissionError(
                    "DYNAMIC_RUN_ROUTE_ID_MISMATCH:" + route_id + "!=" + observed
                )
            return dict(out)
        return legacy.run(request, repo_root=root)
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": bool(route_id),
            "route_id": route_id or None,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def catalog(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    dynamic = _dynamic_rows(root)
    return {
        "schema": SCHEMA,
        "status": "PASS__V20_LEGACY_CARRIER_PLUS_DYNAMIC_DEFAULT_LIVE_ADMISSION",
        "pass": True,
        "legacy_runtime": LEGACY_RUNTIME,
        "legacy_route_count": len(legacy.ROUTES),
        "dynamic_route_count": len(dynamic),
        "dynamic_route_ids": sorted(str(row["route_id"]) for row in dynamic),
        "future_verified_route_requires_new_vN_source": False,
        "legacy_precedence_reencoded": False,
        "dynamic_collision_policy": (
            "UNIQUE_DYNAMIC_MATCH_AND_NO_LEGACY_MATCH_OR_SEMANTIC_OPEN__ELSE_FAIL_CLOSED"
        ),
        "verification_authority_mutated": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
