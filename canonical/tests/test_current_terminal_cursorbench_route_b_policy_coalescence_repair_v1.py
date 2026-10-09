import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_route_b_policy_coalescence_truth_repair():
    a=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").read_text())
    r=json.loads((ROOT/"canonical/governance/CURSORBENCH_ROUTE_B_POLICY_COALESCENCE_DISJUNCTION_TRUTH_REPAIR_20261009_V1.json").read_text())
    assert r["current_global_route_b_frontier"]["benchmark_scope_completeness"]=="CLOSED"
    assert r["current_global_route_b_frontier"]["positive_policy_adequacy_cover"]=="OPEN"
    assert len(r["route_b_disjunction"])==3
    l=a["live_truth"]
    assert l["cursorbench_route_b_three_object_mincut_global_necessity"] is False
    assert l["cursorbench_route_b_three_object_mincut_scope"]=="B_TYPED_SPECIALIST_MEMBERSHIP_BRANCH_ONLY"
    assert l["cursorbench_route_b_global_mandatory_proof_object_count"]==1
    assert l["cursorbench_route_b_global_mandatory_proof_objects"]==["CODING_SPEC_SCOPE_COMPLETE_AUTHENTICATED_POLICY_ADEQUACY_COVER"]
    assert l["cursorbench_route_b_common_policy_can_bypass_full_semantic_mapping"] is True
    assert l["cursorbench_route_b_common_policy_can_bypass_full_failure_taxonomy"] is True
    rec=a["cursorbench_route_b_policy_coalescence_truth_repair_reconciliation_20261009_v1"]
    assert rec["atom_truth_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
