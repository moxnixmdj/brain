from __future__ import annotations

import copy
from pathlib import Path

from canonical.runtime.executable_refinement_verifier_v1 import (
    RECEIPT_SCHEMA,
    SCHEMA,
    git_blob_sha,
    verify_certificate,
)


def _make_repo(tmp_path: Path):
    abstract = tmp_path / "canonical/governance/abstract.json"
    concrete = tmp_path / "canonical/runtime/concrete.py"
    proof = tmp_path / "canonical/verification/proof.json"
    abstract.parent.mkdir(parents=True)
    concrete.parent.mkdir(parents=True)
    proof.parent.mkdir(parents=True)
    abstract.write_text('{"schema":"ABSTRACT_V1"}\n', encoding="utf-8")
    concrete.write_text('def run(x):\n    return x\n', encoding="utf-8")
    proof.write_text('{"pass":true}\n', encoding="utf-8")
    cert = {
        "schema": SCHEMA,
        "proof_class": "DECLARATIVE_BOUNDING",
        "subject_id": "fixture",
        "abstract_spec": {
            "path": "canonical/governance/abstract.json",
            "git_blob_sha": git_blob_sha(abstract),
            "semantic_version": "ABSTRACT_V1",
        },
        "concrete_implementation": [
            {
                "path": "canonical/runtime/concrete.py",
                "git_blob_sha": git_blob_sha(concrete),
            }
        ],
        "state_mapping": {"proved": True, "mode": "IDENTITY"},
        "input_binding": {"proved": True, "mode": "DIRECT_TYPED_MAPPING"},
        "transition_refinement": {
            "coverage_mode": "DECLARED_FINITE_PARTITION",
            "unsupported_behavior": "FAIL_CLOSED",
            "classes": [
                {"case_id": "PASS", "kind": "PASS"},
                {"case_id": "FAIL", "kind": "FAIL_CLOSED"},
            ],
        },
        "observation_refinement": {
            "proved": True,
            "mode": "EXACT_GOAL_PROJECTION",
        },
        "nondeterminism_contract": {
            "proved": True,
            "mode": "DETERMINISTIC",
        },
        "safety_refinement": {"proved": True},
        "liveness_refinement": {"required": False, "proved": False},
        "proof_dependencies": [
            {
                "path": "canonical/verification/proof.json",
                "git_blob_sha": git_blob_sha(proof),
            }
        ],
        "terminal_credit_delta": 0,
    }
    return cert, abstract, concrete, proof


def test_unknown_schema_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["schema"] = "UNKNOWN"
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "CERTIFICATE_SCHEMA_INVALID"


def test_missing_required_field_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert.pop("input_binding")
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "CERTIFICATE_FIELD_SET_INVALID"


def test_unsupported_proof_class_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["proof_class"] = "SELF_ASSERTED_MAGIC"
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "PROOF_CLASS_UNSUPPORTED"


def test_abstract_blob_drift_fails_closed(tmp_path):
    cert, abstract, _, _ = _make_repo(tmp_path)
    abstract.write_text('{"schema":"ABSTRACT_V2"}\n', encoding="utf-8")
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ABSTRACT_SPEC_BLOB_DRIFT"


def test_concrete_blob_drift_fails_closed(tmp_path):
    cert, _, concrete, _ = _make_repo(tmp_path)
    concrete.write_text('def run(x):\n    return None\n', encoding="utf-8")
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "CONCRETE_IMPLEMENTATION_0_BLOB_DRIFT"


def test_proof_dependency_drift_fails_closed(tmp_path):
    cert, _, _, proof = _make_repo(tmp_path)
    proof.write_text('{"pass":false}\n', encoding="utf-8")
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "PROOF_DEPENDENCY_0_BLOB_DRIFT"


def test_unknown_transition_class_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["transition_refinement"]["classes"][0]["kind"] = "MAGIC"
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "TRANSITION_CLASS_KIND_UNSUPPORTED"


def test_unproved_input_binding_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["input_binding"]["proved"] = False
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "INPUT_BINDING_UNPROVED"


def test_safety_only_certificate_rejected_when_liveness_is_declared_required(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["liveness_refinement"] = {"required": True, "proved": False}
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "LIVENESS_REFINEMENT_REQUIRED_BUT_UNPROVED"


def test_nonzero_terminal_credit_fails_closed(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["terminal_credit_delta"] = 1
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "NONZERO_TERMINAL_CREDIT_FORBIDDEN"


def test_valid_declarative_certificate_emits_structural_only_receipt(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    out = verify_certificate(copy.deepcopy(cert), repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["schema"] == RECEIPT_SCHEMA
    assert out["subject_id"] == "fixture"
    assert out["structural_binding_verified"] is True
    assert out["refinement_verified"] is False
    assert out["assurance_level"] == "STRUCTURAL_BINDING_ONLY"
    assert out["execution_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
    assert len(out["certificate_sha256"]) == 64
    assert len(out["receipt_sha256"]) == 64


def test_declarations_do_not_self_certify_refinement(tmp_path):
    cert, _, _, _ = _make_repo(tmp_path)
    cert["safety_refinement"] = {"proved": True}
    cert["liveness_refinement"] = {"required": False, "proved": True}
    out = verify_certificate(cert, repo_root=tmp_path)
    assert out["pass"] is True
    assert out["refinement_verified"] is False
    assert out["execution_authority"] is False
