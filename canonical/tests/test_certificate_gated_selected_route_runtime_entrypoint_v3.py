from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v3 as r

EXACT_CONTEXT = {"kind": "ROUTER_DEPLOYMENT_CANARY_V1"}
SYMBOLIC_CONTEXT = {"kind": "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"}
PAYLOAD = {"probe": 7, "text": "deterministic"}


def test_current_pointer_preflight_supports_both_match_modes():
    out = r.preflight()
    assert out["pass"] is True, out
    assert out["route_row_count"] == 2
    assert out["route_id_count"] == 1
    assert out["match_modes"] == ["EXACT_CONTEXT_DIGEST", "SYMBOLIC_PREDICATE_CALLABLE"]
    assert out["selected_cover_complete"] is False


def test_exact_context_canary_dispatches_through_current_pointer():
    out = r.dispatch(EXACT_CONTEXT, PAYLOAD)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED"
    assert out["selected_match_mode"] == "EXACT_CONTEXT_DIGEST"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["creditable"] is False
    assert out["result"]["status"] == "PASS__DETERMINISTIC_CANARY_EXECUTED"


def test_symbolic_callable_canary_dispatches_through_same_current_pointer():
    out = r.dispatch(SYMBOLIC_CONTEXT, PAYLOAD)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED"
    assert out["selected_match_mode"] == "SYMBOLIC_PREDICATE_CALLABLE"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["creditable"] is False
    assert out["result"]["status"] == "PASS__DETERMINISTIC_CANARY_EXECUTED"


def test_uncovered_context_fails_closed():
    with pytest.raises(r.RuntimeBindingFailClosed, match="NO_CERTIFIED_ROUTE_MATCH"):
        r.select_route({"kind": "NOT_A_CANARY"})


def test_overlap_fails_closed_instead_of_lexical_tie_break(monkeypatch):
    registry = r.load_registry()
    rows = r._verified_rows(registry)
    monkeypatch.setattr(r, "_verified_rows", lambda _registry: rows)
    monkeypatch.setattr(r, "_row_matches", lambda row, context, actual_digest: True)
    with pytest.raises(r.RuntimeBindingFailClosed, match="AMBIGUOUS_CERTIFIED_ROUTE_MATCH"):
        r.select_route({"kind": "ANY"}, registry=registry)


def test_pointer_hash_drift_fails_closed(tmp_path: Path):
    pointer = json.loads(
        Path(r.CURRENT_REGISTRY_POINTER_PATH).read_text(encoding="utf-8")
    )
    pointer["target"]["git_blob_sha"] = "0" * 40
    bad = tmp_path / "pointer.json"
    bad.write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(r.RuntimeBindingFailClosed, match="CURRENT_REGISTRY_TARGET_BLOB_DRIFT"):
        r.load_registry(bad)


def test_verified_route_ids_deduplicate_same_route_across_match_modes():
    assert r.verified_route_ids() == ["router-deployment-canary"]
