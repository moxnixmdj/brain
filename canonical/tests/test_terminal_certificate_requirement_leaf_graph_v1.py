import json
from pathlib import Path

from canonical.runtime.terminal_proof_leaf_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_REQUIREMENT_LEAF_GRAPH_V1.json"


def test_live_terminal_requirement_graph_is_fail_closed_on_unknown_reality_costs():
    doc = json.loads(GRAPH.read_text(encoding="utf-8"))
    out = evaluate(doc)

    assert out["status"] == "LOWER_BOUND_ONLY_UNKNOWN_COSTS_REMAIN", out
    assert out["lower_bound_reality_units"] == 0, out
    assert out["upper_bound_reality_units"] is None, out
    assert out["optimality_certificate"]["optimality_proved"] is False, out
    assert out["selected_unknown_cost_leaf_ids"], out
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0

    selected = set(out["selected_leaf_ids"])
    # The two future exact-target branches are impossible and must never survive.
    assert "TOOL_SCOPE::EXACT_FUTURE_TARGET_UNIVERSE" not in selected
    assert "DELEGATION_SCOPE::EXACT_FUTURE_TARGET_UNIVERSE" not in selected
    # Existing scoped component receipts must not be re-paid as leaves.
    assert "COMPOSITION_SCOPE::tool discovery" not in selected
    assert "COMPOSITION_SCOPE::delegation" not in selected
    # Actual unresolved load-bearing work must remain visible.
    assert "TB4::ZERO_COST_CARRIER_BOUND" in selected
    assert "COMPOSITION_SCOPE::recovery" in selected
    assert any(x.startswith("TOOL_SCOPE::") for x in selected)
    assert any(x.startswith("DELEGATION_SCOPE::") for x in selected)


def test_unknown_cost_is_never_reported_as_exact_zero_reality():
    doc = json.loads(GRAPH.read_text(encoding="utf-8"))
    out = evaluate(doc)
    assert not (
        out["optimality_certificate"]["optimality_proved"]
        and out["upper_bound_reality_units"] == 0
        and out["selected_unknown_cost_leaf_ids"]
    )
