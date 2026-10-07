from __future__ import annotations

import pytest

import canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v4 as v4

CANARY_CONTEXT = {"kind": "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"}


def test_live_noncreditable_canary_remains_compatible():
    out = v4.preflight()
    assert out["pass"] is True, out
    assert out["route_count"] == 1
    assert out["creditable_route_count"] == 0
    assert out["selected_cover_complete"] is False

    routed = v4.dispatch(CANARY_CONTEXT, {"probe": 41})
    assert routed["creditable"] is False
    assert routed["payload_sha256"] is None
    assert routed["result"]["terminal_result"] is False


def test_creditable_row_without_payload_validator_fails_closed():
    row = {
        "creditable": True,
        "cell_id": "CELL",
        "route_id": "route",
    }
    with pytest.raises(
        v4.RuntimeBindingFailClosed,
        match="CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING",
    ):
        # Isolate the V4-specific post-V3 check. The inherited V3 validation
        # is independently covered by the V3 suite.
        original = v4._verified_rows_v3
        try:
            v4._verified_rows_v3 = lambda registry: [row]
            v4._verified_rows({"scope_id": "scope://opus55/observable-trace"})
        finally:
            v4._verified_rows_v3 = original


def test_creditable_dispatch_must_call_payload_validator(monkeypatch):
    row = {
        "match_mode": "SYMBOLIC_PREDICATE",
        "admitted": True,
        "creditable": True,
        "cell_id": "FINITE_CELL",
        "route_id": "finite-route",
        "admission_predicate_id": "finite-predicate",
        "admission_certificate_blob_sha": "a" * 40,
        "adequacy_certificate_blob_sha": "b" * 40,
        "route_blob_sha": "c" * 40,
        "_predicate_path": object(),
        "_route_path": object(),
    }
    monkeypatch.setattr(
        v4,
        "load_registry",
        lambda: {"scope_id": "scope://opus55/observable-trace"},
    )
    monkeypatch.setattr(v4, "_verified_rows", lambda registry: [row])
    monkeypatch.setattr(
        v4,
        "_load_callable",
        lambda path, name, module_prefix: (
            (lambda ctx: True)
            if "admission_predicate" in module_prefix
            else (lambda payload: {"pass": True})
        ),
    )
    monkeypatch.setattr(
        v4,
        "_selected_cover_state",
        lambda registry, rows: {"authorized": False, "gate_status": "OPEN"},
    )

    calls = []

    def reject_payload(*args, **kwargs):
        calls.append((args, kwargs))
        raise v4.RuntimeBindingFailClosed("PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL")

    monkeypatch.setattr(v4, "_validate_creditable_payload", reject_payload)

    with pytest.raises(
        v4.RuntimeBindingFailClosed,
        match="PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL",
    ):
        v4.dispatch({"certified": True}, {"different": "payload"})

    assert len(calls) == 1


def test_noncreditable_dispatch_does_not_require_payload_validator(monkeypatch):
    row = {
        "match_mode": "SYMBOLIC_PREDICATE",
        "admitted": True,
        "creditable": False,
        "cell_id": "CANARY",
        "route_id": "canary",
        "admission_predicate_id": "canary-predicate",
        "admission_certificate_blob_sha": "a" * 40,
        "adequacy_certificate_blob_sha": "b" * 40,
        "route_blob_sha": "c" * 40,
        "_predicate_path": object(),
        "_route_path": object(),
    }
    monkeypatch.setattr(
        v4,
        "load_registry",
        lambda: {"scope_id": "scope://opus55/observable-trace"},
    )
    monkeypatch.setattr(v4, "_verified_rows", lambda registry: [row])
    monkeypatch.setattr(
        v4,
        "_load_callable",
        lambda path, name, module_prefix: (
            (lambda ctx: True)
            if "admission_predicate" in module_prefix
            else (lambda payload: {"pass": True})
        ),
    )
    monkeypatch.setattr(
        v4,
        "_selected_cover_state",
        lambda registry, rows: {"authorized": False, "gate_status": "OPEN"},
    )
    monkeypatch.setattr(
        v4,
        "_validate_creditable_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("noncreditable route must not call payload validator")
        ),
    )

    out = v4.dispatch({"canary": True}, {"probe": 1})
    assert out["creditable"] is False
    assert out["payload_sha256"] is None
