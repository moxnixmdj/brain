from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"


def test_current_terminal_truth_keeps_executable_refinement_open():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    truth = terminal["live_truth"]
    assert truth["executable_refinement_framework_bound"] is True
    assert truth["router_canary_structural_refinement_binding_bound"] is True
    assert truth["router_canary_refinement_verified"] is False
    assert truth["brain_owned_semantic_edge_structural_refinement_binding_bound"] is True
    assert truth["brain_owned_semantic_edge_bounded_refinement_verified"] is False
    assert truth["repository_wide_executable_refinement_closed"] is False
    assert truth["all_creditable_live_routes_refinement_verified"] is False
    assert truth["terminal_executable_refinement_gap_closed"] is False
    assert truth["executable_refinement_missing_is_external_impossibility"] is False
    assert truth["declarative_refinement_boolean_is_promotion_authority"] is False


def test_refinement_framework_source_bindings_are_exactly_projected():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    src = terminal["authoritative_sources"]["executable_refinement_framework_20261009_v1"]
    assert src["verifier"]["git_blob_sha"] == "13618667e6f87b29b1e56ceeb8947c51d64de683"
    assert src["creditable_route_gate"]["git_blob_sha"] == "58602558b3a6ef81e9c6dcaf28cbc61eb0b1d70d"
    assert src["dependency_graph_guard"]["git_blob_sha"] == "7ee3988dc393965f83994fba70cd1903e7e2aa7c"
    assert src["dependency_graph"]["git_blob_sha"] == "b4fc9176f5e463e2352c437708dfe4dc75898368"
    assert src["gated_entrypoint"]["git_blob_sha"] == "c4f3ed3ea767a8930789f2426484fbce710d8f14"


def test_refinement_reconciliation_grants_zero_terminal_credit():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    rec = terminal["executable_refinement_reconciliation_20261009_v1"]
    assert rec["terminal_credit_delta"] == 0
    assert "MECHANICALLY_CHECKED_MODEL_TO_EXECUTABLE_REFINEMENT" in rec["highest_dominance_open_leaf"]
    assert any("NO_SUPPORTED_PROOF_CLASS" in item for item in rec["open"])
