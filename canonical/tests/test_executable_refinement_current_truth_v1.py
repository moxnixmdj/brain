from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.executable_refinement_verifier_v1 import git_blob_sha

ROOT = Path(__file__).resolve().parents[2]
TRUTH = ROOT / "canonical/governance/EXECUTABLE_REFINEMENT_CURRENT_TRUTH_20261009_V1.json"


def _truth():
    return json.loads(TRUTH.read_text(encoding="utf-8"))


def test_truth_fragment_binds_exact_feature_artifacts():
    truth = _truth()
    for binding in truth["source_bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file(), binding
        assert git_blob_sha(path) == binding["git_blob_sha"], binding


def test_truth_fragment_keeps_refinement_and_terminal_closure_open():
    truth = _truth()
    state = truth["truth"]
    assert state["executable_refinement_framework_bound"] is True
    assert state["creditable_route_gate_bound"] is True
    assert state["declarative_refinement_boolean_is_promotion_authority"] is False
    assert state["router_canary_refinement_verified"] is False
    assert state["brain_owned_semantic_edge_bounded_refinement_verified"] is False
    assert state["repository_wide_executable_refinement_closed"] is False
    assert state["all_creditable_live_routes_refinement_verified"] is False
    assert state["terminal_executable_refinement_gap_closed"] is False
    assert state["executable_refinement_missing_is_external_impossibility"] is False


def test_truth_fragment_defers_hot_terminal_pointer_projection():
    truth = _truth()
    promotion = truth["promotion"]
    assert promotion["current_terminal_authority_pointer_modified"] is False
    assert promotion["current_terminal_authority_projection_status"].startswith("DEFERRED_")
    assert truth["terminal_authority"] is False
    assert truth["accounting"]["terminal_credit_delta"] == 0


def test_truth_fragment_identifies_real_next_frontier():
    truth = _truth()
    frontier = truth["frontier"]
    assert frontier["highest_dominance_open_leaf"] == "terminal-live-paths-executable-refinement"
    assert frontier["supported_proof_class_emitting_refinement_verified_true"] is False
    assert frontier["open_world_closure"] is False
    assert frontier["generator_coverage_proved"] is False
