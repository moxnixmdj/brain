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
REGISTRY_BLOB = "ecf17421bbd1ad5fc0624a8403a7a6f73a64bfbb"
VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_VERIFY_20261010_V10.json"
VERIFY_BLOB = "f8ca5391876acd164af3a238958bca959f4fc026"


def test_current_professional_quality_projects_latest_truth_without_overclaim():
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
    assert scoped["admitted_scope_count"] == 10
    assert len(scoped["admitted_roots"]) == 10
    assert scoped["global_leaf_closure"] is False
    assert scoped["global_root_closure"] is False

    assert current["profile_execution_authority"] is True
    assert current["router_v3_independent_replay"] is False
    assert current["independent_replay"] is False
    assert current["live_default"] is False
    assert current["promotion_authority"] is False
    assert current["quality_authority"] is False
    assert current["terminal_authority"] is False
    assert "NO_ROUTER_V3_INDEPENDENT_REPLAY_YET" in current["hard_nonclaims"]

    legacy = current["legacy_router_verification"]
    assert legacy["scope"] == "ROUTER_V1_ONLY__DOES_NOT_VERIFY_ROUTER_V3"
