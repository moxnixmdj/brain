"""Fail-closed default-live integration gate for current R2 direct routes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_route_registry_v1 as dispatcher

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_LIVE_INTEGRATION_CLOSURE_V4"
ROOT = Path(__file__).resolve().parents[2]
DISPATCHER = "canonical/runtime/r2_direct_route_registry_v1.py"
FIXED_POINT = "canonical/runtime/general_adequate_decision_fixed_point_v2.py"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("JSON_NOT_OBJECT:" + str(path))
    return dict(value)


def evaluate(*, repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    current = _json(root / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
    direct = current.get("direct_adequacy")
    if not isinstance(direct, Mapping):
        raise ValueError("CURRENT_R2_DIRECT_ADEQUACY_MISSING")

    state = dispatcher.effective_state(repo_root=root)
    baseline = set(state["baseline_activation_route_ids"])
    dynamic = set(state["dynamic_admission_route_ids"])
    effective = set(state["deployable_route_ids"])
    expected = baseline | dynamic

    dispatcher_path = root / DISPATCHER
    fixed_path = root / FIXED_POINT
    source = fixed_path.read_text(encoding="utf-8")

    runtime_binding_ok = (
        direct.get("direct_runtime_path") == DISPATCHER
        and direct.get("direct_runtime_git_blob_sha") == _blob(dispatcher_path)
    )
    fixed_binding_ok = (
        direct.get("fixed_point_controller_git_blob_sha") == _blob(fixed_path)
        and current.get("controller", {}).get("fixed_point_git_blob_sha") == _blob(fixed_path)
    )
    stable_import = (
        "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy"
        in source
    )
    legacy_import = "r2_direct_end_to_end_adequacy_v13 as direct_adequacy" in source

    counts_ok = (
        direct.get("current_route_count") == len(baseline)
        and direct.get("baseline_activation_route_count") == len(baseline)
        and direct.get("dynamic_admission_route_count") == len(dynamic)
        and direct.get("default_live_route_count") == len(effective)
    )
    ordered_current_complete = (
        state["activation_auto_admitted_route_count"] == 0
        and state["stale_selection_metadata_route_ids"] == []
        and state["legacy_selection_metadata_count"] == len(baseline)
    )

    equality = expected == effective
    missing = sorted(expected - effective)
    unauthorized = sorted(effective - expected)

    passed = (
        equality
        and not missing
        and not unauthorized
        and runtime_binding_ok
        and fixed_binding_ok
        and stable_import
        and not legacy_import
        and counts_ok
        and ordered_current_complete
        and direct.get("future_route_source_edit_required") is False
        and direct.get("future_route_registry_edit_required") is False
        and direct.get("legacy_v1_to_v13_runtime_chain_load_bearing") is False
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__VERIFIED_DEPLOYABLE_EQUALS_DEFAULT_EXECUTABLE__V13_ORDERED_CURRENT_COMPLETE"
            if passed else
            "FAIL_CLOSED__DEFAULT_RUNTIME_INTEGRATION_OPEN"
        ),
        "pass": passed,
        "baseline_activation_route_count": len(baseline),
        "dynamic_admission_route_count": len(dynamic),
        "expected_default_live_route_count": len(expected),
        "effective_default_live_route_count": len(effective),
        "verified_deployable_equals_default_executable": equality,
        "missing_execution": missing,
        "unauthorized_execution": unauthorized,
        "runtime_binding_ok": runtime_binding_ok,
        "fixed_point_binding_ok": fixed_binding_ok,
        "stable_dispatcher_import_live": stable_import,
        "legacy_v13_import_live": legacy_import,
        "count_reconciliation_ok": counts_ok,
        "ordered_current_route_metadata_complete": ordered_current_complete,
        "activation_auto_admitted_route_count": state["activation_auto_admitted_route_count"],
        "stale_selection_metadata_route_ids": state["stale_selection_metadata_route_ids"],
        "future_route_source_edit_required": direct.get("future_route_source_edit_required"),
        "future_route_registry_edit_required": direct.get("future_route_registry_edit_required"),
        "legacy_version_chain_load_bearing": direct.get("legacy_v1_to_v13_runtime_chain_load_bearing"),
        "open_world_semantic_coverage_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
