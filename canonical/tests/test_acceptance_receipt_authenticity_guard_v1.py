"""Caller-authored receipt fields cannot establish independent execution."""
from execution_guard.acceptance_receipt_authenticity_probe_v1 import measure


def test_invented_verifiers_cannot_accept_unperformed_effects_or_authorize_route_c():
    report = measure()
    assert report["case_count"] == 4
    assert all(row["requested_effect_unperformed"] for row in report["rows"])
    assert report["unsafe_gate_count"] == 0
    assert all(row["gate_pass"] is False for row in report["rows"])
    assert all(row["direct_admission_authorized"] is False for row in report["rows"])
