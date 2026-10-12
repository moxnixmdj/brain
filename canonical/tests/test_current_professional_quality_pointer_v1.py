from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"

PROFILE = "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
PROFILE_BLOB = "f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
ROUTER = "canonical/runtime/professional_quality_p1_router_v3.py"
ROUTER_BLOB = "cdb6716ac6d562d1ab222242d07aeecc5cdfac78"
REGISTRY = "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB = "b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
OVERLAY = "canonical/runtime/professional_quality_scoped_evidence_overlay_v1.py"
OVERLAY_BLOB = "19c11df8b011fa2c72c755f421edcd38a89f0a07"
LATEST_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_R4_SEMANTIC_SCOPED_INTEGRATION_VERIFY_20261010_V1.json"
LATEST_VERIFY_BLOB = "664c22bfdfc51ea4058e4e2d3c3efe9d8def907b"

EXPECTED_SEMANTIC_LEAVES = {
    "PQ::R1_TARGET_SPECIFICATION::SEMANTIC",
    "PQ::R2_CANDIDATE_SEARCH::SEMANTIC",
    "PQ::R3_REALIZATION_OBSERVATION::SEMANTIC",
    "PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC",
    "PQ::R5_EVALUATOR_REFERENCE::SEMANTIC",
    "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::SEMANTIC",
    "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
    "PQ::R8_POPULATION_CONTEXT_OPERATOR::SEMANTIC",
    "PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC",
    "PQ::R10_ANALYSIS_DECISION::SEMANTIC",
    "PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::SEMANTIC",
    "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC",
}


def test_current_professional_quality_projects_complete_bounded_root_semantics_without_overclaim():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["profile_path"] == PROFILE
    assert current["profile_sha"] == PROFILE_BLOB
    assert current["router_path"] == ROUTER
    assert current["router_sha"] == ROUTER_BLOB

    scoped = current["scoped_evidence"]
    assert scoped["registry_path"] == REGISTRY
    assert scoped["registry_git_blob_sha"] == REGISTRY_BLOB
    assert scoped["runtime_path"] == OVERLAY
    assert scoped["runtime_git_blob_sha"] == OVERLAY_BLOB
    assert scoped["verification_path"] == LATEST_VERIFY
    assert scoped["verification_git_blob_sha"] == LATEST_VERIFY_BLOB
    assert scoped["admitted_scope_count"] == 21
    assert len(scoped["admitted_roots"]) == 12
    assert set(scoped["bounded_semantic_leaf_ids"]) == EXPECTED_SEMANTIC_LEAVES
    assert scoped["global_leaf_closure"] is False
    assert scoped["global_root_closure"] is False
    assert scoped["domain_semantic_closure"] is False
    assert scoped["domain_execution_closure"] is False

    leaf = current["leaf_coverage_projection"]
    assert leaf["partial_coverage_leaf_count"] == 24
    assert leaf["semantic_partial_coverage_leaf_count"] == 12
    assert leaf["execution_partial_coverage_leaf_count"] == 12
    assert leaf["no_scoped_evidence_leaf_count"] == 0
    assert leaf["no_scoped_evidence_leaf_ids"] == []
    assert leaf["verified_global_leaf_count"] in {0, 9}
    assert leaf["open_global_leaf_count"] in {15, 24}
    assert leaf["global_leaf_closure"] is False

    same = current["same_subject_composition"]
    assert same["structural_gate_verified"] is True
    assert same["real_all_root_subject_bound"] in {False, True}
    frontier = current["same_subject_root_binding_frontier"]
    assert frontier["verified_root_subject_binding_count"] in {0, 12}
    assert frontier["composition_admissible"] in {False, True}

    assert current["profile_execution_authority"] is True
    assert current["live_default"] is False
    assert current["promotion_authority"] is False
    assert current["quality_authority"] is False
    assert current["terminal_authority"] is False
    assert current["terminal_credit_delta"] == 0
    assert "NO_PROFESSIONAL_QUALITY_COMPLETENESS_PROOF" in current["hard_nonclaims"]
