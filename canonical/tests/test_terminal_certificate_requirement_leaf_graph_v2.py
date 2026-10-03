import json
from pathlib import Path

from canonical.runtime.terminal_proof_leaf_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_REQUIREMENT_LEAF_GRAPH_V2.json"


def test_live_v2_compiles_existing_tb4_receipts_and_shrinks_unknown_cut():
    doc = json.loads(GRAPH.read_text(encoding="utf-8"))
    out = evaluate(doc)

    assert out["status"] == "LOWER_BOUND_ONLY_UNKNOWN_COSTS_REMAIN", out
    assert out["nondominated_proof_set_count"] == 8, out
    assert len(out["selected_leaf_ids"]) == 32, out
    assert len(out["selected_unknown_cost_leaf_ids"]) == 32, out
    assert out["lower_bound_reality_units"] == 0, out
    assert out["upper_bound_reality_units"] is None, out
    assert out["optimality_certificate"]["optimality_proved"] is False, out

    selected = set(out["selected_leaf_ids"])
    assert "TB4::MINIMUM_8_TASK_SCORE_ARITHMETIC" not in selected
    assert "TB4::RESOURCE_METADATA_INDEPENDENT_REPRODUCTION" not in selected
    assert "TB4_CARRIER::STANDARD_HOSTED_RUNNER_DECLARED_LIMITS" not in selected
    assert "TB4::TASK_IDENTITY_BINDING" in selected
    assert "TB4::PROTOCOL_EQUIVALENCE_BOUND" in selected
    assert "TB4::ATTAINABILITY_RECOMPILED" in selected
    assert any(x.startswith("TB4_CARRIER::") for x in selected)


def test_v2_preserves_zero_credit_and_no_execution_authority():
    out = evaluate(json.loads(GRAPH.read_text(encoding="utf-8")))
    assert out["new_reality_units_consumed"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
