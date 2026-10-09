from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from canonical.runtime.executable_refinement_verifier_v1 import verify_certificate
from canonical.runtime.router_deployment_canary_v1 import invoke

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "canonical/governance/ROUTER_DEPLOYMENT_CANARY_ABSTRACT_SPEC_20261009_V1.json"
CERT_PATH = ROOT / "canonical/governance/ROUTER_DEPLOYMENT_CANARY_EXECUTABLE_REFINEMENT_20261009_V1.json"


def _cert():
    return json.loads(CERT_PATH.read_text(encoding="utf-8"))


def test_canary_structural_binding_is_valid_but_not_refinement_verified():
    out = verify_certificate(_cert(), repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["refinement_verified"] is False
    assert out["assurance_level"] == "STRUCTURAL_BINDING_ONLY"
    assert out["terminal_credit_delta"] == 0


def test_canary_success_observation_matches_abstract_contract():
    payload = {"probe": 7, "text": "deterministic"}
    out = invoke(payload)
    expected = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert out == {
        "schema": "PROJECT_BRAIN_ROUTER_DEPLOYMENT_CANARY_V1",
        "status": "PASS__DETERMINISTIC_CANARY_EXECUTED",
        "payload_sha256": expected,
        "terminal_result": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def test_canary_non_mapping_is_type_error():
    with pytest.raises(TypeError, match="PAYLOAD_MAPPING_REQUIRED"):
        invoke([1, 2, 3])


def test_canary_binding_drift_fails_closed():
    cert = _cert()
    cert["concrete_implementation"][0]["git_blob_sha"] = "0" * 40
    out = verify_certificate(cert, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "CONCRETE_IMPLEMENTATION_BLOB_DRIFT"


def test_canary_cannot_claim_terminal_credit():
    cert = copy.deepcopy(_cert())
    cert["terminal_credit_delta"] = 1
    out = verify_certificate(cert, repo_root=ROOT)
    assert out["pass"] is False
    assert out["reason"] == "NONZERO_TERMINAL_CREDIT_FORBIDDEN"
