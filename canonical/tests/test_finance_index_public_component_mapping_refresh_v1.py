import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/FINANCE_INDEX_PUBLIC_COMPONENT_MAPPING_REFRESH_20261010_V1.json"

def test_finance_index_public_mapping_refresh_stays_fail_closed():
    j=json.loads(P.read_text(encoding="utf-8"))
    t=j["bound_truth"]
    c=j["consequence"]
    assert t["outer_weights_and_evaluation_membership_public"] is True
    assert t["inner_component_subscore_transform_public"] is False
    assert t["public_component_breakdown_values_available"] is False
    assert c["normalized_component_lower_bound_can_be_created_from_public_underlying_benchmark_score_alone"] is False
    assert c["default_component_floor_authorized"] is False
    assert c["cross_benchmark_score_transfer_without_exact_normalization_authorized"] is False
    assert c["row_state"].startswith("OPEN_BLOCKED")
    assert j["accounting"]["acceptance_credit_delta"]==0
    assert j["accounting"]["terminal_credit_delta"]==0
