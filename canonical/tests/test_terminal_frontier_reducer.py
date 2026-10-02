from __future__ import annotations

import copy
import json
from pathlib import Path

from canonical.runtime.terminal_closure_reducer import evaluate_frontier_state


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_live_frontier_reduces_to_prequalification_without_contradiction():
    out = evaluate_frontier_state(
        _load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"),
        _load("canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json"),
        _load("canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json"),
    )
    assert out["status"] == "PASS", out
    assert out["implementation_authority_count"] == 0
    assert out["fresh_terminal_evidence_allowed"] is False
    assert out["next_action"] == "COMPLETE_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION"


def test_stale_survivor_projection_fails_closed():
    active = {"atomic_preproof_frontier": {"implementation_authority_count": 0, "execute_now": False}}
    universe = {
        "atomic_preproof_frontier": {"implementation_authority_count": 5, "execute_now": False},
        "global_cut": {"atomic_preproof_survivor_count": 5},
        "execution_authority": {"fresh_terminal_evidence_allowed": False},
    }
    preq = {
        "execution_authority": False,
        "prequalification_progress": {"zero_preproof_implementation_residuals": True},
    }
    out = evaluate_frontier_state(active, universe, preq)
    assert out["status"] == "FAIL_CLOSED"
    assert out["next_action"] == "RECONCILE_RECEIPT_DERIVED_STATE"
    assert any("IMPLEMENTATION_AUTHORITY_COUNT_CONTRADICTION" in x for x in out["failed_invariants"])


def test_prequalification_pass_automatically_authorizes_parallel_terminal_wave():
    active = {"atomic_preproof_frontier": {"implementation_authority_count": 0, "execute_now": False}}
    universe = {
        "atomic_preproof_frontier": {"implementation_authority_count": 0, "execute_now": False},
        "global_cut": {"atomic_preproof_survivor_count": 0},
        "execution_authority": {"fresh_terminal_evidence_allowed": True},
    }
    preq = {
        "execution_authority": True,
        "prequalification_progress": {"zero_preproof_implementation_residuals": True},
    }
    out = evaluate_frontier_state(active, universe, preq)
    assert out["status"] == "PASS"
    assert out["execution_authority"] is True
    assert out["fresh_terminal_evidence_allowed"] is True
    assert out["next_action"] == "EXECUTE_T0_T1_T2_T3_IN_PARALLEL"
