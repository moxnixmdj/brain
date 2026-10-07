from __future__ import annotations

import pytest

from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2 import (
    RuntimeBindingFailClosed,
    _verify_payload_attestation,
    context_digest,
    dispatch,
    payload_digest,
    preflight,
)

CANARY_CONTEXT={"kind":"ROUTER_DEPLOYMENT_CANARY_V1"}
CANARY_PAYLOAD={"probe":7,"text":"deterministic"}

def test_v1_canary_registry_remains_compatible():
    out=preflight()
    assert out["pass"] is True,out
    assert out["route_count"]==1
    assert out["selected_cover_complete"] is False

def test_noncreditable_canary_dispatch_still_executes_without_payload_validator():
    out=dispatch(CANARY_CONTEXT,CANARY_PAYLOAD)
    assert out["status"]=="PASS__CERTIFICATE_GATED_ROUTE_EXECUTED"
    assert out["creditable"] is False
    assert out["payload_sha256"] is None
    assert out["result"]["status"]=="PASS__DETERMINISTIC_CANARY_EXECUTED"

def _attestation():
    return {
      "admitted":True,
      "cell_id":"CELL",
      "context_digest_sha256":context_digest({"cell":"CELL"}),
      "payload_sha256":payload_digest({"x":1}),
    }

def test_exact_payload_attestation_passes():
    _verify_payload_attestation(
      _attestation(),
      cell_id="CELL",
      actual_context_digest=context_digest({"cell":"CELL"}),
      actual_payload_digest=payload_digest({"x":1}),
    )

def test_wrong_payload_digest_fails_closed():
    a=_attestation(); a["payload_sha256"]="0"*64
    with pytest.raises(RuntimeBindingFailClosed,match="PAYLOAD_ATTESTATION_DIGEST_MISMATCH"):
      _verify_payload_attestation(
        a,cell_id="CELL",
        actual_context_digest=context_digest({"cell":"CELL"}),
        actual_payload_digest=payload_digest({"x":1}),
      )

def test_wrong_context_digest_fails_closed():
    a=_attestation(); a["context_digest_sha256"]="0"*64
    with pytest.raises(RuntimeBindingFailClosed,match="PAYLOAD_ATTESTATION_CONTEXT_MISMATCH"):
      _verify_payload_attestation(
        a,cell_id="CELL",
        actual_context_digest=context_digest({"cell":"CELL"}),
        actual_payload_digest=payload_digest({"x":1}),
      )

def test_wrong_cell_fails_closed():
    a=_attestation(); a["cell_id"]="OTHER"
    with pytest.raises(RuntimeBindingFailClosed,match="PAYLOAD_ATTESTATION_CELL_MISMATCH"):
      _verify_payload_attestation(
        a,cell_id="CELL",
        actual_context_digest=context_digest({"cell":"CELL"}),
        actual_payload_digest=payload_digest({"x":1}),
      )

def test_not_admitted_fails_closed():
    a=_attestation(); a["admitted"]=False
    with pytest.raises(RuntimeBindingFailClosed,match="PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL"):
      _verify_payload_attestation(
        a,cell_id="CELL",
        actual_context_digest=context_digest({"cell":"CELL"}),
        actual_payload_digest=payload_digest({"x":1}),
      )

def test_payload_digest_order_invariant_and_nan_rejected():
    assert payload_digest({"b":2,"a":1})==payload_digest({"a":1,"b":2})
    with pytest.raises(Exception,match="PAYLOAD_NOT_CANONICAL_JSON"):
      payload_digest({"x":float("nan")})
