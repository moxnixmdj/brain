from __future__ import annotations

import pytest

from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v3 import (
    RuntimeBindingFailClosed,
    dispatch,
    preflight,
)

CANARY_CONTEXT = {"kind": "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"}


def test_symbolic_registry_preflight_is_fail_closed_and_not_global_cover():
    out = preflight()
    assert out["pass"] is True, out
    assert out["route_count"] == 1
    assert out["symbolic_route_count"] == 1
    assert out["creditable_route_count"] == 0
    assert out["selected_cover_complete"] is False
    assert out["terminal_credit_delta"] == 0


def test_symbolic_canary_context_executes_through_predicate():
    out = dispatch(CANARY_CONTEXT, {"probe": 11})
    assert out["status"] == "PASS__CERTIFICATE_GATED_SYMBOLIC_ROUTE_EXECUTED"
    assert out["match_mode"] == "SYMBOLIC_PREDICATE"
    assert out["admission_predicate_id"] == "SYMBOLIC_CANARY_KIND_V1"
    assert out["selected_cell_id"] == "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_ONLY"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["creditable"] is False
    assert out["selected_cover_complete"] is False
    assert out["result"]["status"] == "PASS__DETERMINISTIC_CANARY_EXECUTED"
    assert out["result"]["terminal_result"] is False


def test_symbolic_predicate_rejects_uncovered_context():
    with pytest.raises(RuntimeBindingFailClosed, match="NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
        dispatch({"kind": "SOMETHING_ELSE"}, {"probe": 1})
