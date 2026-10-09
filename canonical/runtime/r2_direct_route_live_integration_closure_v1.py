"""R2 direct-route default-runtime integration closure gate V1.

Current R2 activation defines the deployable direct-route universe. The stable
dispatcher must expose exactly that universe. Legacy registry metadata may cover
some or all routes only to preserve historical precedence; a newly activated route
may be auto-admitted under UNIQUE_MATCH_REQUIRED without a registry or source edit.

This gate does not claim open-world semantic coverage or terminal completion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_route_registry_v1 as dispatcher

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_LIVE_INTEGRATION_CLOSURE_V1"
ROOT = Path(__file__).resolve().parents[2]
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

    state = dispatcher.effective_state(repo_root=root)
    executable = set(state["deployable_route_ids"])
    metadata = set(state["legacy_selection_metadata_route_ids"])
    auto_admitted = set(state["auto_admitted_route_ids"])
    stale_metadata = set(state["stale_selection_metadata_route_ids"])

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

    missing_execution = sorted(deployable - executable)
    unauthorized_execution = sorted(executable - deployable)
    metadata_missing_for_deployable = sorted(deployable - metadata)

    equality = deployable == executable
    passed = (
        equality
        and runtime_binding_ok
        and fixed_point_blob_ok
        and stable_import
        and not legacy_import_live
        and direct.get("future_route_source_edit_required") is False
        and direct.get("future_route_registry_edit_required") is False
        and not stale_metadata
        and auto_admitted == set(metadata_missing_for_deployable)
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_R2_DEPLOYABLE_EQUALS_DEFAULT_EXECUTABLE_DIRECT_ROUTES"
            if passed
            else "FAIL_CLOSED__R2_DIRECT_ROUTE_DEFAULT_INTEGRATION_OPEN"
        ),
        "pass": passed,
        "verified_deployable_route_count": len(deployable),
        "executable_dispatch_route_count": len(executable),
        "legacy_selection_metadata_count": len(metadata),
        "auto_admitted_route_count": len(auto_admitted),
        "verified_deployable_equals_executable": equality,
        "missing_execution": missing_execution,
        "unauthorized_execution": unauthorized_execution,
        "deployable_without_legacy_metadata": metadata_missing_for_deployable,
        "auto_admitted_route_ids": sorted(auto_admitted),
        "stale_selection_metadata_route_ids": sorted(stale_metadata),
        "runtime_binding_ok": runtime_binding_ok,
        "fixed_point_blob_ok": fixed_point_blob_ok,
        "stable_dispatcher_import_live": stable_import,
        "legacy_version_chain_import_live": legacy_import_live,
        "future_route_source_edit_required": direct.get(
            "future_route_source_edit_required"
        ),
        "future_route_registry_edit_required": direct.get(
            "future_route_registry_edit_required"
        ),
        "new_activation_routes_auto_admitted_fail_closed": (
            direct.get("dynamic_activation_auto_admission") is True
        ),
        "open_world_semantic_coverage_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
