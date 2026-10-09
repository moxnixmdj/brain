from __future__ import annotations

import copy
import json
from pathlib import Path

from canonical.runtime.executable_refinement_verifier_v1 import verify_certificate

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_EXECUTABLE_REFINEMENT_20261009_V1.json"


def _cert():
    return json.loads(CERT.read_text(encoding="utf-8"))


def test_semantic_edge_binding_is_structurally_valid_but_not_refinement_verified():
    out = verify_certificate(_cert(), repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["refinement_verified"] is False
    assert out["assurance_level"] == "STRUCTURAL_BINDING_ONLY"
    assert out["terminal_credit_delta"] == 0


def test_semantic_edge_binding_covers_both_load_bearing_modules():
    out = verify_certificate(_cert(), repo_root=ROOT)
    paths = {row["path"] for row in out["concrete_implementation"]}
    assert paths == {
        "canonical/runtime/brain_owned_semantic_relation_edge_authority_v1.py",
        "canonical/runtime/semantic_relation_control_v1.py",
    }


def test_semantic_edge_declared_partition_keeps_not_entails_fail_closed():
    out = verify_certificate(_cert(), repo_root=ROOT)
    assert "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF" in out["transition_case_ids"]
    assert "ENTAILS_RECEIPT" in out["transition_case_ids"]


def test_semantic_edge_blob_drift_fails_closed():
    cert = copy.deepcopy(_cert())
    cert["concrete_implementation"][0]["git_blob_sha"] = "0" * 40
    out = verify_certificate(cert, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "CONCRETE_IMPLEMENTATION_BLOB_DRIFT"


def test_semantic_edge_binding_cannot_claim_terminal_credit():
    cert = copy.deepcopy(_cert())
    cert["terminal_credit_delta"] = 1
    out = verify_certificate(cert, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "NONZERO_TERMINAL_CREDIT_FORBIDDEN"
