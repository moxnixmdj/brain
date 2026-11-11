import json
from pathlib import Path

from canonical.runtime.terminal_proof_leaf_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_REQUIREMENT_LEAF_GRAPH_V3.json"
FRONTIER = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json"


def test_live_v3_graph_binds_exact_current_frontier_and_fails_closed_on_unknown_costs():
    doc = json.loads(GRAPH.read_text(encoding="utf-8"))
    frontier = json.loads(FRONTIER.read_text(encoding="utf-8"))
    out = evaluate(doc)

    assert doc["source_frontier"]["git_blob_sha"] == "106139ff69616670993dbc6af324d8686747e8b1", doc
    assert len(frontier["unresolved_predicates"]) == 31
    assert len(frontier["certificates"]) == 15

    assert out["status"] == "LOWER_BOUND_ONLY_UNKNOWN_COSTS_REMAIN", out
    assert out["nondominated_proof_set_count"] == 8, out
    assert len(out["selected_leaf_ids"]) == 32, out
    assert len(out["selected_unknown_cost_leaf_ids"]) == 32, out
    assert out["lower_bound_reality_units"] == 0, out
    assert out["upper_bound_reality_units"] is None, out
    assert out["optimality_certificate"]["optimality_proved"] is False, out
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False


def test_v3_compiles_existing_receipts_without_overclaiming_them():
    doc = json.loads(GRAPH.read_text(encoding="utf-8"))
    out = evaluate(doc)
    selected = set(out["selected_leaf_ids"])

    # Existing independently verified facts are not repaid.
    assert "COMPOSITION_SCOPE::tool discovery" not in selected
    assert "COMPOSITION_SCOPE::delegation" not in selected
    assert "DELEGATION_SCOPE::DOMAIN_AND_INFORMATION_COVERAGE" not in selected
    assert "TB4::MINIMUM_8_TASK_SCORE_ARITHMETIC" not in selected
    assert "TB4::RESOURCE_METADATA_INDEPENDENT_REPRODUCTION" not in selected

    # Impossible routes are deleted.
    assert "TOOL_SCOPE::EXACT_FUTURE_TARGET_UNIVERSE" not in selected
    assert "DELEGATION_SCOPE::EXACT_FUTURE_TARGET_UNIVERSE" not in selected
    assert "TB4_CARRIER::PR958_GITHUB_HOSTED_4CPU_DECLARED_LIMITS" not in selected

    # Still-real obligations remain explicit.
    assert "TB4::TASK_IDENTITY_BINDING" in selected
    assert "TB4::PROTOCOL_EQUIVALENCE_BOUND" in selected
    assert "TB4::ATTAINABILITY_RECOMPILED" in selected
    assert any(x.startswith("TB4_CARRIER::") for x in selected)
    assert any(x.startswith("TOOL_SCOPE::") for x in selected)
    assert (
        "DELEGATION_SCOPE::EXHAUSTIVE_FINITE_SUPERSET" in selected
        or "DELEGATION_SCOPE::UNIVERSAL_PERFORMANCE_BOUND" in selected
    )


def test_v3_never_treats_certificate_zero_cost_as_terminal_zero_cost():
    out = evaluate(json.loads(GRAPH.read_text(encoding="utf-8")))
    assert out["selected_unknown_cost_leaf_ids"], out
    assert not (
        out["optimality_certificate"]["optimality_proved"]
        and out["upper_bound_reality_units"] == 0
    ), out
    assert out["new_reality_units_consumed"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
