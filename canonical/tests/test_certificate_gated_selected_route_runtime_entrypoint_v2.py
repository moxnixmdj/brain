from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v2 as entrypoint
from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2 import (
    RuntimeBindingFailClosed,
    _verify_payload_attestation,
    context_digest,
    dispatch,
    payload_digest,
    preflight,
)

CANARY_CONTEXT = {"kind": "ROUTER_DEPLOYMENT_CANARY_V1"}
CANARY_PAYLOAD = {"probe": 7, "text": "deterministic"}


def test_v1_canary_registry_remains_compatible():
    out = preflight()
    assert out["pass"] is True, out
    assert out["route_count"] == 1
    assert out["selected_cover_complete"] is False


def test_noncreditable_canary_dispatch_still_executes_without_payload_validator():
    out = dispatch(CANARY_CONTEXT, CANARY_PAYLOAD)
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED"
    assert out["creditable"] is False
    assert out["payload_sha256"] is None
    assert out["result"]["status"] == "PASS__DETERMINISTIC_CANARY_EXECUTED"


def _attestation():
    return {
        "admitted": True,
        "cell_id": "CELL",
        "context_digest_sha256": context_digest({"cell": "CELL"}),
        "payload_sha256": payload_digest({"x": 1}),
    }


def test_exact_payload_attestation_passes():
    _verify_payload_attestation(
        _attestation(),
        cell_id="CELL",
        actual_context_digest=context_digest({"cell": "CELL"}),
        actual_payload_digest=payload_digest({"x": 1}),
    )


def test_wrong_payload_digest_fails_closed():
    a = _attestation()
    a["payload_sha256"] = "0" * 64
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="PAYLOAD_ATTESTATION_DIGEST_MISMATCH",
    ):
        _verify_payload_attestation(
            a,
            cell_id="CELL",
            actual_context_digest=context_digest({"cell": "CELL"}),
            actual_payload_digest=payload_digest({"x": 1}),
        )


def test_wrong_context_digest_fails_closed():
    a = _attestation()
    a["context_digest_sha256"] = "0" * 64
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="PAYLOAD_ATTESTATION_CONTEXT_MISMATCH",
    ):
        _verify_payload_attestation(
            a,
            cell_id="CELL",
            actual_context_digest=context_digest({"cell": "CELL"}),
            actual_payload_digest=payload_digest({"x": 1}),
        )


def test_wrong_cell_fails_closed():
    a = _attestation()
    a["cell_id"] = "OTHER"
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="PAYLOAD_ATTESTATION_CELL_MISMATCH",
    ):
        _verify_payload_attestation(
            a,
            cell_id="CELL",
            actual_context_digest=context_digest({"cell": "CELL"}),
            actual_payload_digest=payload_digest({"x": 1}),
        )


def test_not_admitted_fails_closed():
    a = _attestation()
    a["admitted"] = False
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL",
    ):
        _verify_payload_attestation(
            a,
            cell_id="CELL",
            actual_context_digest=context_digest({"cell": "CELL"}),
            actual_payload_digest=payload_digest({"x": 1}),
        )


def test_payload_digest_order_invariant_and_nan_rejected():
    assert payload_digest({"b": 2, "a": 1}) == payload_digest({"a": 1, "b": 2})
    with pytest.raises(Exception, match="PAYLOAD_NOT_CANONICAL_JSON"):
        payload_digest({"x": float("nan")})


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _creditable_registry(
    tmp_path: Path,
    *,
    receipt_verified: bool = True,
    receipt_subject: str = "route",
    route_binding: str | None = None,
):
    route = _write(
        tmp_path,
        "canonical/runtime/route.py",
        "def invoke(payload):\n    return {'pass': True}\n",
    )
    validator = _write(
        tmp_path,
        "canonical/runtime/validator.py",
        "def validate(context, payload):\n    return {}\n",
    )
    route_blob = entrypoint.git_blob_sha(route)
    validator_blob = entrypoint.git_blob_sha(validator)

    adequacy = _write(
        tmp_path,
        "canonical/verification/adequacy.json",
        json.dumps(
            {
                "cell_id": "CELL",
                "route_id": "route",
                "creditable": True,
            }
        )
        + "\n",
    )
    admission_obj = {
        "cell_id": "CELL",
        "route_id": "route",
        "context_digest_sha256": "ctx",
        "admitted": True,
        "creditable": True,
        "payload_validator_path": "canonical/runtime/validator.py",
        "payload_validator_blob_sha": validator_blob,
        "payload_validator_callable": "validate",
    }
    admission = _write(
        tmp_path,
        "canonical/verification/admission.json",
        json.dumps(admission_obj) + "\n",
    )
    refinement_certificate = _write(
        tmp_path,
        "canonical/governance/refinement.json",
        json.dumps({"subject_id": "route"}) + "\n",
    )
    cert_blob = entrypoint.git_blob_sha(refinement_certificate)
    refinement_receipt = _write(
        tmp_path,
        "canonical/verification/refinement-receipt.json",
        json.dumps(
            {
                "subject_id": receipt_subject,
                "refinement_verified": receipt_verified,
                "certificate_git_blob_sha": cert_blob,
                "concrete_route_git_blob_sha": route_binding or route_blob,
                "terminal_credit_delta": 0,
            }
        )
        + "\n",
    )

    row = {
        "context_digest": "ctx",
        "cell_id": "CELL",
        "route_id": "route",
        "route_path": "canonical/runtime/route.py",
        "route_blob_sha": route_blob,
        "callable": "invoke",
        "adequacy_certificate_path": "canonical/verification/adequacy.json",
        "adequacy_certificate_blob_sha": entrypoint.git_blob_sha(adequacy),
        "admission_certificate_path": "canonical/verification/admission.json",
        "admission_certificate_blob_sha": entrypoint.git_blob_sha(admission),
        "admitted": True,
        "creditable": True,
        "payload_validator_path": "canonical/runtime/validator.py",
        "payload_validator_blob_sha": validator_blob,
        "payload_validator_callable": "validate",
        "refinement_certificate_path": "canonical/governance/refinement.json",
        "refinement_certificate_blob_sha": cert_blob,
        "refinement_receipt_path": "canonical/verification/refinement-receipt.json",
        "refinement_receipt_blob_sha": entrypoint.git_blob_sha(refinement_receipt),
    }
    return {
        "schema": entrypoint.REGISTRY_SCHEMA,
        "default": "FAIL_CLOSED",
        "selected_cover_complete": False,
        "router": {},
        "routes": [row],
    }, row, refinement_receipt


def test_creditable_route_missing_refinement_binding_fails_closed(tmp_path, monkeypatch):
    registry, row, _ = _creditable_registry(tmp_path)
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    for key in (
        "refinement_certificate_path",
        "refinement_certificate_blob_sha",
        "refinement_receipt_path",
        "refinement_receipt_blob_sha",
    ):
        row.pop(key)
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="CREDITABLE_REFINEMENT_BINDING_MISSING:0",
    ):
        entrypoint._verified_rows(registry)


def test_creditable_route_stale_refinement_receipt_fails_closed(tmp_path, monkeypatch):
    registry, row, _ = _creditable_registry(tmp_path)
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    row["refinement_receipt_blob_sha"] = "0" * 40
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="REFINEMENT_RECEIPT_BLOB_DRIFT:0",
    ):
        entrypoint._verified_rows(registry)


def test_creditable_route_unverified_refinement_receipt_fails_closed(
    tmp_path, monkeypatch
):
    registry, _, _ = _creditable_registry(tmp_path, receipt_verified=False)
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="REFINEMENT_RECEIPT_NOT_VERIFIED:0",
    ):
        entrypoint._verified_rows(registry)


def test_creditable_route_refinement_subject_mismatch_fails_closed(
    tmp_path, monkeypatch
):
    registry, _, _ = _creditable_registry(tmp_path, receipt_subject="other")
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="REFINEMENT_RECEIPT_SUBJECT_MISMATCH:0",
    ):
        entrypoint._verified_rows(registry)


def test_creditable_route_refinement_route_binding_mismatch_fails_closed(
    tmp_path, monkeypatch
):
    registry, _, _ = _creditable_registry(tmp_path, route_binding="0" * 40)
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    with pytest.raises(
        RuntimeBindingFailClosed,
        match="REFINEMENT_RECEIPT_ROUTE_BINDING_MISMATCH:0",
    ):
        entrypoint._verified_rows(registry)


def test_creditable_route_with_verified_refinement_binding_is_admitted(
    tmp_path, monkeypatch
):
    registry, _, _ = _creditable_registry(tmp_path)
    monkeypatch.setattr(entrypoint, "ROOT", tmp_path)
    receipts, rows = entrypoint._verified_rows(registry)
    assert len(receipts) == 1
    assert len(rows) == 1
    assert receipts[0].route_id == "route"
