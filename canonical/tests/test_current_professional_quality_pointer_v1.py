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
REGISTRY_BLOB = "58083361e2f56c7b7312f07fb5d9670eb78dc121"
VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_VERIFY_20261010_V11.json"
VERIFY_BLOB = "6760cf07f928a9adcf70a0e2ec46e81b109f035a"
ROUTER_V3_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V3_INDEPENDENT_VERIFY_20261010_V1.json"
ROUTER_V3_VERIFY_BLOB = "1e793db5919be8a75e1599ba974bd06afaae6e91"
ROUTER_V3_TESTS_BLOB = "7fd496e9200d1408d561cadcf40b8f4bf536c898"

SAME_SUBJECT_RUNTIME = "canonical/runtime/professional_quality_same_subject_composition_gate_v1.py"
SAME_SUBJECT_RUNTIME_BLOB = "46ab1a5bdf91e3559bfca89ee6059d0be7e89937"
SAME_SUBJECT_TESTS = "canonical/tests/test_professional_quality_same_subject_composition_gate_v1.py"
SAME_SUBJECT_TESTS_BLOB = "9d265428c1ec3c3bfa6cea5d2c8c3b90b36edcd5"
SAME_SUBJECT_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_VERIFY_20261010_V1.json"
SAME_SUBJECT_VERIFY_BLOB = "56ab94e6f3cc68a34f1e73ebf9294d8639563522"
ASSURANCE = ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"


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

    same_subject = current["same_subject_composition_gate"]
    assert same_subject["runtime_path"] == SAME_SUBJECT_RUNTIME
    assert same_subject["runtime_git_blob_sha"] == SAME_SUBJECT_RUNTIME_BLOB
    assert same_subject["tests_path"] == SAME_SUBJECT_TESTS
    assert same_subject["tests_git_blob_sha"] == SAME_SUBJECT_TESTS_BLOB
    assert same_subject["verification_path"] == SAME_SUBJECT_VERIFY
    assert same_subject["verification_git_blob_sha"] == SAME_SUBJECT_VERIFY_BLOB
    assert same_subject["replay_result"] == "PYCOMPILE_PASS__9_OF_9_PASS"
    assert same_subject["required_root_count"] == 12
    assert same_subject["composition_admissibility_only"] is True
    assert same_subject["real_all_root_subject_binding_proved"] is False
    assert same_subject["professional_quality_closed"] is False
    assert same_subject["quality_authority"] is False
    assert same_subject["terminal_authority"] is False

    assert "NO_REAL_ALL_ROOT_SAME_SUBJECT_BINDING_YET" in current["hard_nonclaims"]
    assert current["next"].startswith(
        "BIND_REAL_CONTENT_ADDRESSED_ROOT_SUBJECT_RECEIPTS_FOR_ONE_EXACT_ARTIFACT_OR_DECLARED_SYSTEM"
    )


def test_current_assurance_requires_same_subject_binding_before_live_promotion():
    assurance = json.loads(ASSURANCE.read_text(encoding="utf-8"))
    same_subject = assurance["professional_quality_same_subject_composition_gate"]

    assert same_subject["runtime_path"] == SAME_SUBJECT_RUNTIME
    assert same_subject["runtime_git_blob_sha"] == SAME_SUBJECT_RUNTIME_BLOB
    assert same_subject["tests_path"] == SAME_SUBJECT_TESTS
    assert same_subject["tests_git_blob_sha"] == SAME_SUBJECT_TESTS_BLOB
    assert same_subject["verification_path"] == SAME_SUBJECT_VERIFY
    assert same_subject["verification_git_blob_sha"] == SAME_SUBJECT_VERIFY_BLOB
    assert same_subject["result"] == "PYCOMPILE_PASS__9_OF_9_PASS__COMPOSITION_ADMISSIBILITY_ONLY"
    assert same_subject["same_subject_normal_form_rule_enforced"] is True
    assert same_subject["real_all_root_subject_binding_proved"] is False
    assert same_subject["global_leaf_closure"] is False
    assert same_subject["domain_semantic_closure"] is False
    assert same_subject["domain_execution_closure"] is False
    assert same_subject["live_default_credit"] is False

    required = assurance["activation"]["required_before_promotion"]
    assert (
        "REAL_CONTENT_ADDRESSED_SAME_SUBJECT_BINDINGS_FOR_ALL_LOAD_BEARING_PROFESSIONAL_ROOTS"
        in required
    )
    assert assurance["live_default"] is False
    assert assurance["terminal_authority"] is False
