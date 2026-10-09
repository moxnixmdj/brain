"""R2 direct-route live integration closure gate V1.

Proves, for the current bounded direct-route universe declared by current R2
authority, that independently verified deployable routes, active registry rows,
and executable stable-dispatcher routes are the same set.

This is an R2 default-runtime integration theorem only. It does not claim
open-world semantic coverage or terminal completion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_route_registry_v1 as dispatcher

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_LIVE_INTEGRATION_CLOSURE_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
EXPECTED_DISPATCHER = "canonical/runtime/r2_direct_route_registry_v1.py"


class R2DirectRouteClosureError(ValueError):
    pass


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise R2DirectRouteClosureError("JSON_NOT_OBJECT:" + str(path))
    return dict(value)


def evaluate(*, repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    current_path = root / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
    fixed_point_path = root / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
    current = _json(current_path)
    direct = current.get("direct_adequacy")
    if not isinstance(direct, Mapping):
        raise R2DirectRouteClosureError("CURRENT_R2_DIRECT_ADEQUACY_MISSING")

    activation_rel = str(direct.get("activation_path") or "")
    activation = root / activation_rel
    if _blob(activation) != str(direct.get("activation_git_blob_sha") or ""):
        raise R2DirectRouteClosureError("CURRENT_R2_ACTIVATION_BLOB_DRIFT")
    activation_doc = _json(activation)
    deployable = {
        str(row.get("route_id") or "")
        for row in activation_doc.get("current_routes", [])
        if isinstance(row, Mapping) and str(row.get("route_id") or "")
    }

    registry = dispatcher.load_registry(repo_root=root)
    active = {
        str(row.get("route_id") or "")
        for row in registry["routes"]
        if isinstance(row, Mapping) and row.get("active") is True
    }
    executable = set(dispatcher.ROUTES)

    direct_runtime_rel = str(direct.get("direct_runtime_path") or "")
    direct_runtime = root / direct_runtime_rel
    runtime_binding_ok = (
        direct_runtime_rel == EXPECTED_DISPATCHER
        and _blob(direct_runtime) == str(direct.get("direct_runtime_git_blob_sha") or "")
    )

    fixed_point_blob_ok = (
        _blob(fixed_point_path)
        == str(direct.get("fixed_point_controller_git_blob_sha") or "")
    )
    source = fixed_point_path.read_text(encoding="utf-8")
    stable_import = (
        "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy"
        in source
    )
    legacy_import_live = (
        "from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as direct_adequacy"
        in source
    )

    missing_activation = sorted(active - deployable)
    missing_promotion = sorted(deployable - active)
    missing_execution = sorted(active - executable)
    unauthorized_execution = sorted(executable - deployable)

    equality = deployable == active == executable
    passed = (
        equality
        and runtime_binding_ok
        and fixed_point_blob_ok
        and stable_import
        and not legacy_import_live
        and direct.get("future_route_source_edit_required") is False
        and direct.get("legacy_v1_to_v8_runtime_chain_load_bearing") is False
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__VERIFIED_DEPLOYABLE_EQUALS_ACTIVE_EQUALS_EXECUTABLE_DIRECT_ROUTES"
            if passed
            else "FAIL_CLOSED__R2_DIRECT_ROUTE_LIVE_INTEGRATION_OPEN"
        ),
        "pass": passed,
        "verified_deployable_route_count": len(deployable),
        "active_registry_route_count": len(active),
        "executable_dispatch_route_count": len(executable),
        "verified_deployable_equals_active_equals_executable": equality,
        "missing_promotion": missing_promotion,
        "registry_not_in_verified_universe": missing_activation,
        "missing_execution": missing_execution,
        "unauthorized_execution": unauthorized_execution,
        "runtime_binding_ok": runtime_binding_ok,
        "fixed_point_blob_ok": fixed_point_blob_ok,
        "stable_dispatcher_import_live": stable_import,
        "legacy_version_chain_import_live": legacy_import_live,
        "future_route_source_edit_required": direct.get(
            "future_route_source_edit_required"
        ),
        "legacy_version_chain_load_bearing": direct.get(
            "legacy_v1_to_v8_runtime_chain_load_bearing"
        ),
        "open_world_semantic_coverage_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
