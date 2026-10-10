"""Complete refinement-obligation registry for current authority runtime paths.

This module closes only the coverage/quantifier question: every non-superseded
runtime binding in CURRENT_TERMINAL_AUTHORITY must appear in the returned
refinement-obligation set exactly once.

It does NOT prove behavioral refinement for any path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.current_authority_runtime_binding_census_v1 import run as binding_census

SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_REGISTRY_V1"
DEFAULT_AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
DEFAULT_SELECTED_REGISTRY = "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1.json"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "coverage_complete": False,
        "semantic_refinement_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _selected_route_paths(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise ValueError("SELECTED_ROUTE_REGISTRY_MISSING")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("SELECTED_ROUTE_REGISTRY_NOT_OBJECT")
    routes = raw.get("routes")
    if not isinstance(routes, list):
        raise ValueError("SELECTED_ROUTE_REGISTRY_ROUTES_INVALID")
    out: dict[str, dict[str, Any]] = {}
    for row in routes:
        if not isinstance(row, Mapping):
            raise ValueError("SELECTED_ROUTE_REGISTRY_ROW_INVALID")
        route_path = row.get("route_path")
        if not isinstance(route_path, str) or not route_path:
            raise ValueError("SELECTED_ROUTE_PATH_INVALID")
        if route_path in out:
            raise ValueError("SELECTED_ROUTE_PATH_DUPLICATE:" + route_path)
        out[route_path] = {
            "route_id": str(row.get("route_id") or ""),
            "admitted": row.get("admitted") is True,
            "creditable": row.get("creditable") is True,
        }
    return out


def run(
    repo_root: str | Path,
    *,
    authority_path: str = DEFAULT_AUTHORITY,
    selected_registry_path: str = DEFAULT_SELECTED_REGISTRY,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    census = binding_census(root, authority_path=authority_path)
    if census.get("pass") is not True:
        return _fail(
            "CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_OPEN",
            census_status=census.get("status"),
            census_errors=census.get("errors"),
        )

    try:
        selected = _selected_route_paths((root / selected_registry_path).resolve())
    except ValueError as exc:
        return _fail(str(exc))

    by_path: dict[str, dict[str, Any]] = {}
    for row in census.get("checked_current_bindings") or []:
        if not isinstance(row, Mapping):
            return _fail("CENSUS_CHECKED_BINDING_INVALID")
        path = str(row.get("path") or "")
        expected = str(row.get("expected_git_blob_sha") or "")
        actual = str(row.get("actual_git_blob_sha") or "")
        if not path or not expected or expected != actual:
            return _fail("CENSUS_CURRENT_BINDING_NOT_EXACT:" + path)
        prior = by_path.get(path)
        if prior is not None and prior["git_blob_sha"] != expected:
            return _fail("CURRENT_PATH_CONFLICT:" + path)
        by_path[path] = {"git_blob_sha": expected}

    expected_count = int(census.get("current_unique_runtime_path_count") or -1)
    if len(by_path) != expected_count:
        return _fail(
            "CURRENT_UNIQUE_PATH_COUNT_MISMATCH",
            expected=expected_count,
            actual=len(by_path),
        )

    obligations = []
    selected_current = 0
    non_selected_current = 0
    for path in sorted(by_path):
        route = selected.get(path)
        if route is None:
            non_selected_current += 1
            class_name = "NON_SELECTED_CURRENT_RUNTIME"
        else:
            selected_current += 1
            class_name = "SELECTED_ROUTE_RUNTIME"
        obligations.append(
            {
                "path": path,
                "git_blob_sha": by_path[path]["git_blob_sha"],
                "classification": class_name,
                "selected_route": route,
                "refinement_obligation_present": True,
                "semantic_refinement_status": "UNRESOLVED",
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_CURRENT_RUNTIME_PATHS_HAVE_REFINEMENT_OBLIGATIONS",
        "pass": True,
        "authority_path": authority_path,
        "selected_registry_path": selected_registry_path,
        "current_runtime_unique_path_count": expected_count,
        "obligation_count": len(obligations),
        "selected_current_runtime_count": selected_current,
        "non_selected_current_runtime_count": non_selected_current,
        "obligations": obligations,
        "coverage_complete": len(obligations) == expected_count,
        "semantic_refinement_proved": False,
        "repository_wide_refinement_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
