from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.brain_owned_semantic_relation_edge_authority_v1 import (
    PROOF_CLASS,
    SCHEMA,
    verify,
)
from canonical.runtime.executable_refinement_verifier_v1 import verify_certificate

ROOT = Path(__file__).resolve().parents[2]
ABSTRACT = ROOT / "canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_ABSTRACT_SPEC_20261009_V1.json"
CERT = ROOT / "canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_EXECUTABLE_REFINEMENT_20261009_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence(*, relation="ENTAILS", text="Reserve buffer means liquidity cushion."):
    return {
        "schema": SCHEMA,
        "proof_class": PROOF_CLASS,
        "scope_id": "scope",
        "source_id": "left",
        "target_id": "right",
        "source_surface": "reserve buffer",
        "target_surface": "liquidity cushion",
        "relation": relation,
        "explicit_definition_sources": [
            {
                "source_id": "doc",
                "scope_id": "scope",
                "source_text": text,
            }
        ],
    }


def test_structural_certificate_is_bound_but_does_not_self_verify_refinement():
    out = verify_certificate(load(CERT), repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["subject_id"] == "brain-owned-semantic-edge-authority"
    assert out["structural_binding_verified"] is True
    assert out["refinement_verified"] is False
    assert out["assurance_level"] == "STRUCTURAL_BINDING_ONLY"
    assert out["terminal_credit_delta"] == 0


@pytest.mark.parametrize(
    ("case_id", "raw", "reason"),
    [
        ("EVIDENCE_NOT_OBJECT", "not-object", "EVIDENCE_NOT_OBJECT"),
        (
            "EVIDENCE_FIELD_SET_INVALID",
            {**evidence(), "extra": True},
            "EVIDENCE_FIELD_SET_INVALID",
        ),
        (
            "EVIDENCE_SCHEMA_INVALID",
            {**evidence(), "schema": "WRONG"},
            "EVIDENCE_SCHEMA_INVALID",
        ),
        (
            "PROOF_CLASS_UNSUPPORTED",
            {**evidence(), "proof_class": "MODEL_JUDGMENT"},
            "PROOF_CLASS_UNSUPPORTED",
        ),
        ("SCOPE_ID_REQUIRED", {**evidence(), "scope_id": ""}, "SCOPE_ID_REQUIRED"),
        (
            "DISTINCT_SOURCE_TARGET_IDS_REQUIRED",
            {**evidence(), "target_id": "left"},
            "DISTINCT_SOURCE_TARGET_IDS_REQUIRED",
        ),
        (
            "SOURCE_TARGET_SURFACES_REQUIRED",
            {**evidence(), "source_surface": ""},
            "SOURCE_TARGET_SURFACES_REQUIRED",
        ),
        (
            "RELATION_UNSUPPORTED",
            {**evidence(), "relation": "SIMILAR"},
            "RELATION_UNSUPPORTED",
        ),
        (
            "EXPLICIT_DEFINITION_SOURCES_REQUIRED",
            {**evidence(), "explicit_definition_sources": []},
            "EXPLICIT_DEFINITION_SOURCES_REQUIRED",
        ),
        (
            "DEFINITION_SOURCE_NOT_OBJECT",
            {**evidence(), "explicit_definition_sources": ["bad"]},
            "DEFINITION_SOURCE_NOT_OBJECT",
        ),
        (
            "DEFINITION_SOURCE_FIELD_SET_INVALID",
            {
                **evidence(),
                "explicit_definition_sources": [
                    {
                        "source_id": "doc",
                        "scope_id": "scope",
                        "source_text": "A means B.",
                        "extra": 1,
                    }
                ],
            },
            "DEFINITION_SOURCE_FIELD_SET_INVALID",
        ),
        (
            "DEFINITION_SOURCE_BINDING_INVALID",
            {
                **evidence(),
                "explicit_definition_sources": [
                    {
                        "source_id": "doc",
                        "scope_id": "wrong",
                        "source_text": "A means B.",
                    }
                ],
            },
            "DEFINITION_SOURCE_BINDING_INVALID",
        ),
        (
            "SEMANTIC_IDENTITY_NOT_PROVED",
            evidence(text="Reserve buffer and liquidity cushion are reviewed."),
            "SEMANTIC_IDENTITY_NOT_PROVED",
        ),
        (
            "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF",
            evidence(relation="NOT_ENTAILS"),
            "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF",
        ),
    ],
)
def test_declared_fail_closed_branch_has_canonical_witness(case_id, raw, reason):
    spec = load(ABSTRACT)
    declared = {row["case_id"]: row for row in spec["transition_partition"]}
    assert case_id in declared
    out = verify(raw)
    assert out["pass"] is False
    assert out["reason"] == reason
    assert out["execution_authority"] is False
    assert out["terminal_authority"] is False


def test_entails_success_matches_declared_success_projection():
    spec = load(ABSTRACT)
    declared = {row["case_id"]: row for row in spec["transition_partition"]}
    assert declared["ENTAILS_SUCCESS"]["kind"] == "PASS"

    out = verify(evidence())
    expected = spec["success_projection"]
    assert out["pass"] is True, out
    for key, value in expected.items():
        assert out[key] == value
    assert len(out["evidence_sha256"]) == 64
    assert len(out["receipt_sha256"]) == 64


def test_declared_partition_and_certificate_case_sets_match_exactly():
    spec = load(ABSTRACT)
    cert = load(CERT)
    spec_cases = {row["case_id"] for row in spec["transition_partition"]}
    cert_cases = {
        row["case_id"] for row in cert["transition_refinement"]["classes"]
    }
    assert spec_cases == cert_cases


def test_witness_suite_does_not_promote_refinement_authority():
    out = verify_certificate(load(CERT), repo_root=ROOT)
    assert out["refinement_verified"] is False
    assert out["execution_authority"] is False
    assert out["terminal_authority"] is False
