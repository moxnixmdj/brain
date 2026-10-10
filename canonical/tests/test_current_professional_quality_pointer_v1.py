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
REGISTRY_BLOB = "f862131430822dfa0b76fe6093f31701b6dca7fe"
OVERLAY = "canonical/runtime/professional_quality_scoped_evidence_overlay_v1.py"
OVERLAY_BLOB = "17f5472868aafcb45e75c72b744bcd8ad45a7049"
OVERLAY_TESTS_BLOB = "f434254ad7dd659537f2deab34d9cc70c7391584"
R3_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_20261010_V1.json"
R3_VERIFY_BLOB = "3c9a6f03c9dfb7597cdb7c5ca01e9eaf66a596e0"
ROUTER_V3_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V3_INDEPENDENT_VERIFY_20261010_V1.json"
ROUTER_V3_VERIFY_BLOB = "1e793db5919be8a75e1599ba974bd06afaae6e91"
ROUTER_V3_TESTS_BLOB = "7fd496e9200d1408d561cadcf40b8f4bf536c898"

EXPECTED_SEMANTIC_LEAVES = {
    "PQ::R1_TARGET_SPECIFICATION::SEMANTIC",
    "PQ::R2_CANDIDATE_SEARCH::SEMANTIC",
    "PQ::R3_REALIZATION_OBSERVATION::SEMANTIC",
    "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::SEMANTIC",
    "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
    "PQ::R8_POPULATION_CONTEXT_OPERATOR::SEMANTIC",
    "PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC",
    "PQ::R10_ANALYSIS_DECISION::SEMANTIC",
    "PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::SEMANTIC",
    "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC",
}


def test_current_professional_quality_projects_r3_scoped_truth_without_overclaim():
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
    assert scoped["tests_git_blob_sha"] == OVERLAY_TESTS_BLOB
    assert scoped["verification_path"] == R3_VERIFY
    assert scoped["verification_git_blob_sha"] == R3_VERIFY_BLOB
    assert scoped["admitted_scope_count"] == 19
    assert "R3_REALIZATION_OBSERVATION" in scoped["admitted_roots"]
    assert set(scoped["bounded_semantic_leaf_ids"]) == EXPECTED_SEMANTIC_LEAVES
    assert scoped["global_leaf_closure"] is False
    assert scoped["global_root_closure"] is False
    assert scoped["domain_semantic_closure"] is False
    assert scoped["domain_execution_closure"] is False

    assert current["profile_execution_authority"] is True
    router_verify = current["router_v3_independent_verification"]
    assert router_verify["path"] == ROUTER_V3_VERIFY
    assert router_verify["git_blob_sha"] == ROUTER_V3_VERIFY_BLOB
    assert router_verify["exact_router_git_blob_sha"] == ROUTER_BLOB
    assert router_verify["exact_tests_git_blob_sha"] == ROUTER_V3_TESTS_BLOB
    assert router_verify["actual_clean_and_hard_defect_docx_integration"] is True
    assert router_verify["quality_authority"] is False
    assert current["router_v3_independent_replay"] is True
    assert current["independent_replay"] is True
    assert current["live_default"] is False
    assert current["promotion_authority"] is False
    assert current["quality_authority"] is False
    assert current["terminal_authority"] is False

    leaf = current["leaf_coverage_projection"]
    assert leaf["partial_coverage_leaf_count"] == 22
    assert leaf["semantic_partial_coverage_leaf_count"] == 10
    assert leaf["execution_partial_coverage_leaf_count"] == 12
    assert leaf["no_scoped_evidence_leaf_count"] == 2
    assert leaf["no_scoped_evidence_leaf_ids"] == [
        "PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC",
        "PQ::R5_EVALUATOR_REFERENCE::SEMANTIC",
    ]
    assert leaf["verified_global_leaf_count"] == 0
    assert leaf["open_global_leaf_count"] == 24
    assert leaf["global_leaf_closure"] is False

    r3 = current["r3_realization_semantic"]
    assert r3["verification_path"] == R3_VERIFY
    assert r3["verification_git_blob_sha"] == R3_VERIFY_BLOB
    assert r3["bounded_semantic_evidence"] is True
    assert r3["global_r3_semantic_leaf_closed"] is False
    assert r3["arbitrary_semantic_target_correctness_proved"] is False
    assert r3["whole_open_ended_native_artifact_contract_scope_equivalence_proved"] is False
    assert r3["terminal_credit_delta"] == 0

    same = current["same_subject_composition"]
    assert same["structural_gate_verified"] is True
    assert same["real_all_root_subject_bound"] is False
    assert "NO_REAL_ARTIFACT_OR_SYSTEM_BOUND_TO_ALL_TWELVE_ROOTS_YET" in current["hard_nonclaims"]
    assert current["next"].startswith("ADD_BOUNDED_SEMANTIC_EVIDENCE_FOR_R4_OR_R5")
