"""Fail-closed live-integration gate for the current R2 direct-route layer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import r2_direct_route_registry_v1 as dispatcher

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_LIVE_INTEGRATION_CLOSURE_V3"
ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DISPATCHER = "canonical/runtime/r2_direct_route_registry_v1.py"
VERSION_CHAIN_IMPORT = re.compile(
    r"from canonical\.runtime import r2_direct_end_to_end_adequacy_v\d+ as direct_adequacy"
)


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
    current_path = root / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
    fixed_path = root / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
    dispatcher_path = root / EXPECTED_DISPATCHER

    current = _json(current_path)
    direct = current.get("direct_adequacy")
    if not isinstance(direct, Mapping):
        raise ValueError("CURRENT_R2_DIRECT_ADEQUACY_MISSING")

    activation_path = root / str(direct.get("activation_path") or "")
    if _blob(activation_path) != str(direct.get("activation_git_blob_sha") or ""):
        raise ValueError("CURRENT_R2_ACTIVATION_BLOB_DRIFT")
    activation = _json(activation_path)
    baseline = {
        str(row.get("route_id") or "")
        for row in activation.get("current_routes", [])
        if isinstance(row, Mapping) and str(row.get("route_id") or "")
    }

    state = dispatcher.effective_state(repo_root=root)
    effective = set(state["deployable_route_ids"])
    dynamic = set(state["dynamic_admission_route_ids"])
    expected = baseline | dynamic

    runtime_binding_ok = (
        direct.get("direct_runtime_path") == EXPECTED_DISPATCHER
        and direct.get("direct_runtime_git_blob_sha") == _blob(dispatcher_path)
    )
    fixed_binding_ok = (
        direct.get("fixed_point_controller_git_blob_sha") == _blob(fixed_path)
    )
    source = fixed_path.read_text(encoding="utf-8")
    stable_import = (
        "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy"
        in source
    )
    version_chain_import = VERSION_CHAIN_IMPORT.search(source) is not None

    missing_execution = sorted(expected - effective)
    unauthorized_execution = sorted(effective - expected)
    equality = expected == effective
    declared_count_ok = (
        direct.get("current_route_count") == len(baseline)
        and activation.get("current_route_count") == len(baseline)
    )
    passed = (
        equality
        and declared_count_ok
        and runtime_binding_ok
        and fixed_binding_ok
        and stable_import
        and not version_chain_import
        and direct.get("future_route_source_edit_required") is False
        and direct.get("future_route_registry_edit_required") is False
        and direct.get("legacy_version_chain_load_bearing") is False
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_R2_VERIFIED_DEPLOYABLE_EQUALS_DEFAULT_EXECUTABLE"
            if passed else
            "FAIL_CLOSED__CURRENT_R2_DEFAULT_RUNTIME_INTEGRATION_OPEN"
        ),
        "pass": passed,
        "baseline_activation_route_count": len(baseline),
        "dynamic_admission_route_count": len(dynamic),
        "expected_deployable_route_count": len(expected),
        "effective_executable_route_count": len(effective),
        "declared_route_count_ok": declared_count_ok,
        "verified_deployable_equals_default_executable": equality,
        "missing_execution": missing_execution,
        "unauthorized_execution": unauthorized_execution,
        "runtime_binding_ok": runtime_binding_ok,
        "fixed_point_binding_ok": fixed_binding_ok,
        "stable_dispatcher_import_live": stable_import,
        "version_chain_import_live": version_chain_import,
        "future_route_source_edit_required": direct.get("future_route_source_edit_required"),
        "future_route_registry_edit_required": direct.get("future_route_registry_edit_required"),
        "legacy_version_chain_load_bearing": direct.get("legacy_version_chain_load_bearing"),
        "open_world_semantic_coverage_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
