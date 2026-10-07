from __future__ import annotations

import pytest

from canonical.runtime.certificate_gated_selected_route_router_v1 import RouterFailClosed
from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v1 import (
    context_digest,
    dispatch,
    preflight,
)


CANARY_CONTEXT = {"kind": "ROUTER_DEPLOYMENT_CANARY_V1"}


def test_deployed_registry_preflight_is_content_addressed_and_fail_closed():
    out = preflight()
    assert out["pass"] is True, out
    assert out["route_count"] == 1
    assert out["selected_cover_complete"] is False
    assert out["terminal_credit_delta"] == 0


def test_exact_canary_context_executes_only_through_certified_route():
    payload = {"probe": 7, "text": "deterministic"}
    out = dispatch(CANARY_CONTEXT, payload)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED"
    assert out["actual_context_digest"] == context_digest(CANARY_CONTEXT)
    assert out["selected_cell_id"] == "ROUTER_DEPLOYMENT_CANARY_ONLY"
    assert out["selected_route_id"] == "router-deployment-canary"
    assert out["creditable"] is False
    assert out["selected_cover_complete"] is False
    assert out["result"]["status"] == "PASS__DETERMINISTIC_CANARY_EXECUTED"
    assert out["result"]["terminal_result"] is False
    assert out["terminal_credit_delta"] == 0


def test_uncovered_context_cannot_execute_any_route():
    with pytest.raises(RouterFailClosed, match="NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
        dispatch({"kind": "UNREGISTERED_REAL_CONTEXT"}, {"probe": 1})


def test_context_digest_is_order_invariant_and_nan_rejected():
    assert context_digest({"b": 2, "a": 1}) == context_digest({"a": 1, "b": 2})
    with pytest.raises(Exception, match="CONTEXT_NOT_CANONICAL_JSON"):
        context_digest({"x": float("nan")})
