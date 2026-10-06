from __future__ import annotations

import copy
import json
from pathlib import Path

from canonical.runtime.honesty_target_semantic_bridge_verifier_v1 import (
    BRIDGE,
    COUNTEREXAMPLE,
    ROOT,
    SOURCE,
    evaluate,
)


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_current_bridge_passes_zero_credit():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["target_behavior_semantic_count"] == 4
    assert out["mapped_target_behavior_semantic_count"] == 4
    assert out["performance_metadata_count"] == 1
    assert out["honesty_parity_proved"] is False
    assert out["universal_mediation_proved"] is False
    assert out["ledger_completeness_proved"] is False


def test_performance_marker_cannot_be_promoted_to_behavior_semantic():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    row = next(
        x for x in b["target_observation_classification"]
        if x["source_fact"].startswith("ANTHROPIC_REPORTS_OPUS55")
    )
    row["class"] = "LOAD_BEARING_BEHAVIOR_SEMANTIC"
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert "PERFORMANCE_METADATA_SET_MISMATCH" in out["errors"]


def test_missing_behavior_mapping_fails_closed():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    b["mapping"] = b["mapping"][:-1]
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert "MAPPED_TARGET_SET_NOT_EXACT_BEHAVIOR_SET" in out["errors"]


def test_preexisting_answer_must_map_to_material_disclosure_leaf():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    row = next(
        x for x in b["mapping"]
        if x["target_semantic"] == "ANTHROPIC_EVALUATES_DISCLOSURE_OF_PREEXISTING_ANSWER_USE"
    )
    row["brain_leaves"] = ["PREFER_EXPLICIT_UNCERTAINTY_OR_DECLINE_OVER_UNSUPPORTED_FACTUAL_ASSERTION"]
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert any(x.startswith("REQUIRED_MAPPING_MISMATCH:") for x in out["errors"])


def test_hidden_change_must_map_to_material_disclosure_leaf():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    row = next(
        x for x in b["mapping"]
        if x["target_semantic"] == "ANTHROPIC_EVALUATES_DISCLOSURE_OF_HIDDEN_CHANGES"
    )
    row["brain_leaves"] = ["NO_FALSE_COMPLETION_CLAIM"]
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert any(x.startswith("REQUIRED_MAPPING_MISMATCH:") for x in out["errors"])


def test_pressure_semantic_must_map_to_registered_belief_leaf():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    row = next(
        x for x in b["mapping"]
        if x["target_semantic"] == "ANTHROPIC_EVALUATES_HONESTY_UNDER_PRESSURE"
    )
    row["brain_leaves"] = ["NO_FALSE_COMPLETION_CLAIM"]
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert any(x.startswith("REQUIRED_MAPPING_MISMATCH:") for x in out["errors"])


def test_materiality_cannot_exempt_target_verdict_relevant_event():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    b["materiality_projection"]["machine_contract"][
        "target_verdict_relevance_defines_materiality"
    ] = False
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert (
        "MATERIALITY_CONTRACT_FALSE:target_verdict_relevance_defines_materiality"
        in out["errors"]
    )


def test_ledger_completeness_remains_separate_open_root():
    b = load(BRIDGE)
    b = copy.deepcopy(b)
    b["root_accounting_effect"]["preserves_open"] = [
        "HONESTY_UNIVERSAL_EMISSION_MEDIATION_TOTALITY"
    ]
    out = evaluate(bridge=b)
    assert out["pass"] is False
    assert "OTHER_HONESTY_ROOTS_NOT_PRESERVED" in out["errors"]


def test_primary_source_fact_drift_fails_closed():
    s = load(SOURCE)
    s = copy.deepcopy(s)
    s["observed_semantic_facts"] = s["observed_semantic_facts"][:-1]
    out = evaluate(source=s)
    assert out["pass"] is False
    assert "PRIMARY_SOURCE_FACT_SET_DRIFT" in out["errors"]


def test_unknown_brain_leaf_fails_closed():
    c = load(COUNTEREXAMPLE)
    c = copy.deepcopy(c)
    c["witness"]["leaves"] = c["witness"]["leaves"][:-1]
    out = evaluate(counterexample=c)
    assert out["pass"] is False
    assert "BRAIN_HONESTY_LEAF_SET_NOT_5" in out["errors"]


if __name__ == "__main__":
    tests = [
        test_current_bridge_passes_zero_credit,
        test_performance_marker_cannot_be_promoted_to_behavior_semantic,
        test_missing_behavior_mapping_fails_closed,
        test_preexisting_answer_must_map_to_material_disclosure_leaf,
        test_hidden_change_must_map_to_material_disclosure_leaf,
        test_pressure_semantic_must_map_to_registered_belief_leaf,
        test_materiality_cannot_exempt_target_verdict_relevant_event,
        test_ledger_completeness_remains_separate_open_root,
        test_primary_source_fact_drift_fails_closed,
        test_unknown_brain_leaf_fails_closed,
    ]
    for test in tests:
        test()
    print(f"PASS {len(tests)}/{len(tests)}")
