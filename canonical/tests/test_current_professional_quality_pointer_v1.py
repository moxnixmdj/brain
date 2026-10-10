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
REGISTRY_BLOB = "650b2d5c29b18f213d5effddae2e600bb14d37df"
VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_VERIFY_20261010_V12.json"
VERIFY_BLOB = "87a1c86ce805ef3d2c8c987199ef844b0dbc3a26"
ROUTER_V3_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V3_INDEPENDENT_VERIFY_20261010_V1.json"
ROUTER_V3_VERIFY_BLOB = "1e793db5919be8a75e1599ba974bd06afaae6e91"
ROUTER_V3_TESTS_BLOB = "7fd496e9200d1408d561cadcf40b8f4bf536c898"
LEAF_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_LEAF_COVERAGE_PROJECTION_VERIFY_20261010_V2.json"
LEAF_VERIFY_BLOB = "ff0adc4f3c3b7df83834437dd84c1912ee8a8787"


def test_current_professional_quality_projects_verified_scoped_truth_without_overclaim():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["profile_path"] == PROFILE
    assert current["profile_sha"] == PROFILE_BLOB
    assert current["router_path"] == ROUTER
    assert current["router_sha"] == ROUTER_BLOB

    scoped = current["scoped_evidence"]
    assert scoped["registry_path"] == REGISTRY
    assert scoped["registry_git_blob_sha"] == REGISTRY_BLOB
    assert scoped["verification_path"] == VERIFY
    assert scoped["verification_git_blob_sha"] == VERIFY_BLOB
    assert scoped["admitted_scope_count"] == 12
    assert len(scoped["admitted_roots"]) == 12
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

    legacy = current["legacy_router_verification"]
    assert legacy["scope"] == "ROUTER_V1_ONLY__DOES_NOT_VERIFY_ROUTER_V3"
    assert "NO_ROUTER_V3_INDEPENDENT_REPLAY_YET" not in current["hard_nonclaims"]
    assert current["next"].startswith(
        "BIND_REAL_SAME_SUBJECT_ROOT_RECEIPTS_FOR_ONE_EXACT_ARTIFACT_OR_SYSTEM"
    )
    leaf = current["leaf_coverage_projection"]
    assert leaf["path"] == LEAF_VERIFY
    assert leaf["git_blob_sha"] == LEAF_VERIFY_BLOB
    assert leaf["verified_global_leaf_count"] == 0
    assert leaf["open_global_leaf_count"] == 24
    assert leaf["partial_coverage_leaf_count"] == 14
    assert leaf["semantic_partial_coverage_leaf_count"] == 2
    assert leaf["no_scoped_evidence_leaf_count"] == 10
    same = current["same_subject_composition"]
    assert same["structural_gate_verified"] is True
    assert same["real_all_root_subject_bound"] is False
    assert "NO_REAL_ARTIFACT_OR_SYSTEM_BOUND_TO_ALL_TWELVE_ROOTS_YET" in current["hard_nonclaims"]
