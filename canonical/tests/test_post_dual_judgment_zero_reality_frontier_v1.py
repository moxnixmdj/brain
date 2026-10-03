from __future__ import annotations

import copy
import json
from pathlib import Path

from canonical.runtime import post_dual_judgment_zero_reality_frontier_v1 as r

ROOT = Path(__file__).resolve().parents[2]


def test_current_post_dual_frontier_is_exact_17_requirement_cut():
    out = r.evaluate()
    assert out["pass"] is True, out
    assert out["live_world"]["proved_predicates"] == 11
    assert out["live_world"]["unresolved_predicates"] == 27
    assert out["zero_reality_frontier"]["unique_zero_reality_requirement_count"] == 17
    assert out["zero_reality_frontier"]["nondominated_certificate_count"] == 14
    assert out["zero_reality_frontier"]["covered_predicate_count"] == 25
    assert out["zero_reality_frontier"]["primitive_zero_reality_work_units"] == 31
    assert out["zero_reality_frontier"]["matched_priority_child_facts"] == 16
    assert set(out["transition"]["direct_reality_blocked_predicates"]) == {
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    }
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0


def test_source_admission_does_not_close_target_predicates():
    out = r.evaluate()
    assert out["pass"] is True, out
    assert out["live_world"]["unresolved_predicates"] == 27
    assert len(out["transition"]["discharged_zero_reality_requirements"]) == 2
    assert len(out["transition"]["direct_reality_blocked_predicates"]) == 2
    assert "SOURCE_ADMISSION_IS_NOT_ACCEPTANCE_PREDICATE_CLOSURE" in out["hard_rules"]


def test_global_fresh_reality_remains_false():
    out = r.evaluate()
    assert out["pass"] is True, out
    assert out["transition"]["direct_reality_state"].endswith(
        "GLOBAL_FRESH_REALITY_AUTHORITY_FALSE"
    )
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
