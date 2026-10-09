from __future__ import annotations

import json
from pathlib import Path

import pytest

import canonical.runtime.creditable_route_refinement_gate_v1 as gate
from canonical.runtime.creditable_route_refinement_gate_v1 import (
    RefinementGateFailClosed,
    git_blob_sha,
    verify_creditable_refinement_binding,
)
from canonical.runtime.executable_refinement_verifier_v1 import SCHEMA


def fixture(tmp_path: Path):
    route = tmp_path / "canonical/runtime/route.py"
    route.parent.mkdir(parents=True)
    route.write_text("def invoke(x): return x\n")
    abstract = tmp_path / "canonical/governance/spec.json"
    abstract.parent.mkdir(parents=True)
    abstract.write_text('{"schema":"SPEC"}\n')
    cert = tmp_path / "canonical/governance/cert.json"
    raw = {
        "schema": SCHEMA,
        "proof_class": "DECLARATIVE_BOUNDING",
        "subject_id": "r",
        "abstract_spec": {
            "path": "canonical/governance/spec.json",
            "git_blob_sha": git_blob_sha(abstract),
            "semantic_version": "SPEC",
        },
        "concrete_implementation": [
            {
                "path": "canonical/runtime/route.py",
                "git_blob_sha": git_blob_sha(route),
            }
        ],
        "state_mapping": {"proved": True, "mode": "STATELESS"},
        "input_binding": {"proved": True, "mode": "DIRECT_TYPED_MAPPING"},
        "transition_refinement": {
            "coverage_mode": "DECLARED_FINITE_PARTITION",
            "unsupported_behavior": "FAIL_CLOSED",
            "classes": [{"case_id": "PASS", "kind": "PASS"}],
        },
        "observation_refinement": {"proved": True, "mode": "EXACT_GOAL_PROJECTION"},
        "nondeterminism_contract": {"proved": True, "mode": "DETERMINISTIC"},
        "safety_refinement": {"proved": True},
        "liveness_refinement": {"required": False, "proved": False},
        "proof_dependencies": [],
        "terminal_credit_delta": 0,
    }
    cert.write_text(json.dumps(raw))
    row = {
        "route_path": "canonical/runtime/route.py",
        "route_blob_sha": git_blob_sha(route),
        "refinement_certificate_path": "canonical/governance/cert.json",
        "refinement_certificate_blob_sha": git_blob_sha(cert),
        "refinement_liveness_required": False,
    }
    return row


def test_missing_refinement_binding_fails_closed(tmp_path):
    with pytest.raises(
        RefinementGateFailClosed,
        match="CREDITABLE_REFINEMENT_BINDING_MISSING",
    ):
        verify_creditable_refinement_binding({"route_path": "x"}, repo_root=tmp_path)


def test_structural_only_certificate_cannot_admit_creditable_route(tmp_path):
    row = fixture(tmp_path)
    with pytest.raises(
        RefinementGateFailClosed,
        match="REFINEMENT_NOT_MECHANICALLY_VERIFIED",
    ):
        verify_creditable_refinement_binding(row, repo_root=tmp_path)


def test_certificate_blob_drift_fails_closed(tmp_path):
    row = fixture(tmp_path)
    row["refinement_certificate_blob_sha"] = "0" * 40
    with pytest.raises(
        RefinementGateFailClosed,
        match="REFINEMENT_CERTIFICATE_BLOB_DRIFT",
    ):
        verify_creditable_refinement_binding(row, repo_root=tmp_path)


def test_subject_route_mismatch_fails_closed_even_with_verified_receipt(tmp_path, monkeypatch):
    row = fixture(tmp_path)
    monkeypatch.setattr(
        gate,
        "verify_certificate",
        lambda cert, repo_root: {
            "pass": True,
            "refinement_verified": True,
            "concrete_implementation": [
                {"path": "canonical/runtime/other.py", "git_blob_sha": "0" * 40}
            ],
            "liveness_refinement_verified": True,
        },
    )
    with pytest.raises(
        RefinementGateFailClosed,
        match="REFINEMENT_SUBJECT_ROUTE_MISMATCH",
    ):
        verify_creditable_refinement_binding(row, repo_root=tmp_path)


def test_verified_matching_receipt_can_pass_gate_plumbing(tmp_path, monkeypatch):
    row = fixture(tmp_path)
    monkeypatch.setattr(
        gate,
        "verify_certificate",
        lambda cert, repo_root: {
            "pass": True,
            "refinement_verified": True,
            "concrete_implementation": [
                {"path": row["route_path"], "git_blob_sha": row["route_blob_sha"]}
            ],
            "liveness_refinement_verified": True,
        },
    )
    out = verify_creditable_refinement_binding(row, repo_root=tmp_path)
    assert out["refinement_verified"] is True
