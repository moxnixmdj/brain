from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v5 as v5

EXACT_CONTEXT = {"kind": "ROUTER_DEPLOYMENT_CANARY_V1"}
SYMBOLIC_CONTEXT = {"kind": "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"}
PAYLOAD = {"probe": 7, "text": "deterministic"}


def test_current_pointer_preflight_contains_exact_and_symbolic_rows():
    out = v5.preflight()
    assert out["pass"] is True, out
    assert out["route_row_count"] == 2
    assert out["route_id_count"] == 1
    assert out["exact_route_count"] == 1
    assert out["symbolic_route_count"] == 1
    assert out["creditable_route_count"] == 0
    assert out["selected_cover_complete"] is False


def test_exact_canary_dispatches_through_current_pointer():
    out = v5.dispatch(EXACT_CONTEXT, PAYLOAD)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED_UNIQUE_MATCH"
    assert out["match_mode"] == "EXACT_DIGEST"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["payload_sha256"] is None


def test_symbolic_canary_dispatches_through_same_current_pointer():
    out = v5.dispatch(SYMBOLIC_CONTEXT, PAYLOAD)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED_UNIQUE_MATCH"
    assert out["match_mode"] == "SYMBOLIC_PREDICATE"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["payload_sha256"] is None


def test_uncovered_context_fails_closed():
    with pytest.raises(v5.RuntimeBindingFailClosed, match="NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
        v5.select_route({"kind": "NOT_A_CANARY"})


def test_overlap_fails_closed_instead_of_sorting_first(monkeypatch):
    registry = v5.load_registry()
    rows = v5._verified_rows(registry)
    monkeypatch.setattr(v5, "_verified_rows", lambda _registry: rows)
    monkeypatch.setattr(v5, "_row_matches", lambda row, context, actual_digest: True)
    with pytest.raises(v5.RuntimeBindingFailClosed, match="AMBIGUOUS_CERTIFIED_ROUTE_MATCH"):
        v5.select_route({"kind": "ANY"}, registry=registry)


def test_pointer_hash_drift_fails_closed(tmp_path: Path):
    pointer = json.loads(
        Path(v5.CURRENT_REGISTRY_POINTER_PATH).read_text(encoding="utf-8")
    )
    pointer["target"]["git_blob_sha"] = "0" * 40
    bad = tmp_path / "pointer.json"
    bad.write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(v5.RuntimeBindingFailClosed, match="CURRENT_REGISTRY_TARGET_BLOB_DRIFT"):
        v5.load_registry(bad)


def test_creditable_row_without_payload_validator_fails_closed():
    row = {"creditable": True, "_admission": {}}
    with pytest.raises(
        v5.RuntimeBindingFailClosed,
        match="CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING",
    ):
        v5._verify_creditable_payload_binding(row, 0)


def test_verified_route_ids_deduplicate_same_route_across_admission_regions():
    assert v5.verified_route_ids() == ["router-deployment-canary"]
