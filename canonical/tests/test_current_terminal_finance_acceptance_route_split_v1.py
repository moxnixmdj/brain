import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
SPLIT=ROOT/"canonical/governance/FINANCE_ACCEPTANCE_ROUTE_SPLIT_20261009_V1.json"

def test_finance_acceptance_routes_are_split_without_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    s=json.loads(SPLIT.read_text(encoding="utf-8"))
    live=a["live_truth"]
    assert live["finance_acceptance_predicates_share_one_mandatory_serial_semantic_tail"] is False
    assert live["finance_index_general_finance_semantic_tail_serial_prerequisite"] is False
    assert live["finance_index_separate_index_execution_required"] is False
    assert live["finance_index_fixed_bar_state"].startswith("OPEN_BLOCKED__")
    assert live["finance_index_current_component_count"]==6
    assert live["finance_index_reusable_checkpoint_dependency_count"]==4
    assert live["finance_index_owner_component_breakdown_publicly_available"] is False
    assert live["finance_index_inner_component_normalization_publicly_bound"] is False
    assert live["finance_agent_v2_state"]=="DORMANT_ON_CURRENT_PUBLIC_SCOPE_CUT"
    assert live["finance_agent_v2_public_contract_superset_route_admissible"] is False
    assert live["finance_agent_v2_private_scored_population_publicly_complete"] is False
    assert s["finance_index"]["general_finance_semantic_tail_required_as_serial_prerequisite"] is False
    assert s["finance_agent_v2"]["public_task_contract_superset_route"]=="FALSIFIED"
    assert a["finance_acceptance_route_split_reconciliation_20261009_v1"]["proved_predicate_count_delta"]==0
    assert a["finance_acceptance_route_split_reconciliation_20261009_v1"]["acceptance_credit_delta"]==0
    assert a["finance_acceptance_route_split_reconciliation_20261009_v1"]["terminal_credit_delta"]==0
    assert live["independent_open_acceptance_obligations"]==13

if __name__=="__main__":
    test_finance_acceptance_routes_are_split_without_credit()
    print("PASS 1/1")
